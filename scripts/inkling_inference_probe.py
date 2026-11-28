import argparse
import base64
import csv
import http.client
import json
import os
import re
import socket
import struct
import subprocess
import threading
import time
import zlib
from collections import defaultdict
from contextlib import closing, suppress
from pathlib import Path

from rsec.thermal import THERMAL_FLAGS, sample


def request(port, path, data=None, timeout=15):
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)) as conn:
        conn.request(
            "POST" if data is not None else "GET",
            path,
            json.dumps(data) if data is not None else None,
            {"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = response.read(4 * 1024**2)
        if response.status != 200:
            raise ValueError(f"{path}: HTTP {response.status}")
        return json.loads(body)


def solid_red():
    def chunk(name, data):
        return (
            struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
        )

    size = 96
    return base64.b64encode(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\0\0" * size) * size))
        + chunk(b"IEND", b"")
    ).decode()


def quality(port, with_vision):
    template = {
        "model": "inkling-2-mini",
        "temperature": 0,
        "max_tokens": 512,
        "seed": 3407,
        "chat_template_kwargs": {"reasoning_effort": "none"},
    }

    diagnostics = []

    def chat(content, **extra):
        result = request(
            port,
            "/v1/chat/completions",
            {**template, **extra, "messages": [{"role": "user", "content": content}]},
            timeout=60,
        )
        choice = result["choices"][0]
        message = choice["message"]
        diagnostics.append(
            {
                "finish_reason": choice.get("finish_reason"),
                "content_chars": len(message.get("content") or ""),
                "reasoning_chars": len(message.get("reasoning_content") or ""),
                "completion_tokens": result.get("usage", {}).get("completion_tokens"),
                "tool_calls": len(message.get("tool_calls") or []),
            }
        )
        return message

    results = {}

    def check(name, operation):
        try:
            results[name] = operation()
        except (KeyError, IndexError, TypeError, ValueError, OSError) as exc:
            results[name] = {"error": type(exc).__name__}

    def answer(text, expected):
        reply = chat(text)["content"]
        return bool(reply and re.search(rf"\b{expected}\b", reply))

    check("english", lambda: answer("What is eight plus nine? Reply only with the number.", "17"))
    check("spanish", lambda: answer("Responde sólo con la capital de Chile.", "Santiago"))
    check(
        "code_reasoning",
        lambda: answer(
            "In Python, what is the integer value of sum([2, 5, 7])? Reply with the number.", "14"
        ),
    )
    schema = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    check(
        "schema",
        lambda: (
            json.loads(
                chat(
                    "Return the integer 7 in the value property.",
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "number", "strict": True, "schema": schema},
                    },
                )["content"]
            )
            == {"value": 7}
        ),
    )

    def tool_call():
        tool = {
            "type": "function",
            "function": {
                "name": "return_number",
                "description": "Return a specified integer unchanged.",
                "parameters": schema,
            },
        }
        reply = chat(
            "Call return_number with integer value 7.", tools=[tool], tool_choice="required"
        )
        call = reply["tool_calls"][0]["function"]
        return call["name"] == "return_number" and json.loads(call["arguments"]) == {"value": 7}

    check("tool_call", tool_call)
    if with_vision:
        check(
            "vision",
            lambda: (
                "red"
                in str(
                    chat(
                        [
                            {
                                "type": "text",
                                "text": "Which single color fills this image? Reply in English.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": "data:image/png;base64," + solid_red()},
                            },
                        ]
                    )["content"]
                ).lower()
            ),
        )
    return results, diagnostics


def validate(args):
    contexts = sorted(set(args.prompt_context or [args.context]))
    if contexts[-1] > args.context:
        raise ValueError("Prompt test context exceeds server context")
    if not 0 <= args.reasoning_budget <= 999:
        raise ValueError("Reasoning budget must be between 0 and 999")
    dest = args.output
    dest.mkdir(parents=True, exist_ok=False)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    listing = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,uuid", "--format=csv,noheader"],
        text=True,
        timeout=5,
    )
    ids = {name: uuid for name, uuid in csv.reader(listing.splitlines(), skipinitialspace=True)}
    uuids = [ids[f"NVIDIA GeForce RTX {model}"] for model in ("4070", "3060")]
    started = time.perf_counter()
    samples = []
    stopped = threading.Event()
    failures = []
    children = []
    report = {
        "status": "interrupted",
        "context": args.context,
        "cache": args.cache,
        "split": args.split,
        "reasoning_budget": args.reasoning_budget,
    }

    def capture():
        data = sample(uuids)
        t = max(gpu["temperature.gpu"] for gpu in data.values())
        row = {"elapsed": time.perf_counter() - started, "gpus": data}
        if children:
            with suppress(OSError):
                status = Path(f"/proc/{children[0].pid}/status").read_text(encoding="utf-8")
                rss = re.search(r"^VmRSS:\s+(\d+) kB$", status, re.MULTILINE)
                if rss:
                    row["server_rss_bytes"] = int(rss[1]) * 1024
        samples.append(row)
        if t >= 85 or any(
            str(gpu.get(flag, "")).casefold() in {"active", "yes"}
            for gpu in data.values()
            for flag in THERMAL_FLAGS
        ):
            raise RuntimeError("Thermal limit or throttling")
        if t >= 80:
            print(f"Thermal warning: {t:.1f} °C", flush=True)
        if row["elapsed"] >= 780:
            raise TimeoutError("Inference deadline reached")

    def watch():
        while not stopped.wait(0.75):
            try:
                capture()
            except Exception as exc:
                failures.append(str(exc))
                for child in tuple(children):
                    with suppress(ProcessLookupError):
                        child.terminate()
                return

    capture()
    env = {
        **os.environ,
        "RSEC_LLAMA_PROFILE": "inference-dual",
        "RSEC_LLAMA_SPLIT": args.split,
        "RSEC_LLAMA_CONTEXT": str(args.context),
        "RSEC_LLAMA_PORT": str(port),
        "RSEC_LLAMA_ALIAS": "inkling-2-mini",
        "RSEC_LLAMA_KV_CACHE": args.cache,
        "RSEC_LLAMA_REASONING_BUDGET": str(args.reasoning_budget),
        "RSEC_LLAMA_MMAP": "0",
        "RSEC_LLAMA_VERBOSE": "1",
        "RSEC_LLAMA_MMPROJ": str(args.projector) if args.projector else "",
        "HIP_VISIBLE_DEVICES": "",
        "NO_PROXY": "127.0.0.1,localhost,::1",
    }
    log_path = dest / "llama.log"
    wrapper = Path.cwd() / "scripts/llama_wsl.sh"
    with log_path.open("wb") as log:
        server = subprocess.Popen(
            ["bash", str(wrapper), str(args.model), *uuids],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    children.append(server)
    monitor = threading.Thread(target=watch)
    monitor.start()
    try:
        while time.perf_counter() - started < 410:
            if server.poll() is not None or failures:
                raise RuntimeError(
                    failures[-1] if failures else "llama-server exited before readiness"
                )
            try:
                if request(port, "/health", timeout=1).get("status") == "ok":
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.25)
        else:
            raise RuntimeError("llama.cpp startup deadline")
        report["load_seconds"] = time.perf_counter() - started
        runtime_log = log_path.read_text(encoding="utf-8", errors="replace")
        gpu_buffers = {
            f"CUDA{gpu}": float(size)
            for gpu, size in re.findall(
                r"CUDA(\d+)\s+model buffer size\s*=\s*([\d.]+) MiB", runtime_log
            )
            if float(size) > 0
        }
        if set(gpu_buffers) != {"CUDA0", "CUDA1"}:
            raise RuntimeError("No positive model buffers on both selected CUDA devices")
        report["model_buffers_mib"] = gpu_buffers
        report["offloaded_layers"] = re.findall(r"offloaded (\d+)/(\d+) layers", runtime_log)
        report["kv_mib"] = kv_allocations(runtime_log)
        print(f"Inkling {args.context} {args.cache} loaded on both GPUs", flush=True)
        if args.quality:
            report["quality"], report["chat_diagnostics"] = quality(port, bool(args.projector))
        tokenization = request(
            port,
            "/tokenize",
            {
                "content": " A controlled sequence validates the context buffer.",
                "add_special": False,
            },
        )
        ids = tokenization["tokens"]
        report["requests"] = {}
        for context in contexts:
            count = context - 128
            prompt = (ids * (count // len(ids) + 1))[:count]
            start = time.perf_counter()
            response = request(
                port,
                "/completion",
                {
                    "prompt": prompt,
                    "n_predict": 12,
                    "temperature": 0,
                    "cache_prompt": False,
                    "ignore_eos": True,
                },
                timeout=290,
            )
            timings = {
                key: value
                for key, value in response["timings"].items()
                if isinstance(value, (float, int))
            }
            report["requests"][context] = {**timings, "wall_seconds": time.perf_counter() - start}
            if timings.get("prompt_n", 0) < count - 8 or timings.get("predicted_n") != 12:
                raise RuntimeError("The requested context and output length were not processed")
        if args.goose_driver:
            driver = subprocess.Popen(["bash", str(args.goose_driver), str(port), str(dest)])
            children.append(driver)
            try:
                report["goose_driver_exit"] = driver.wait(timeout=240)
            except subprocess.TimeoutExpired:
                report["goose_error"] = "Local integration driver deadline"
            evidence = dest / "goose-result.json"
            if evidence.is_file():
                report["goose"] = json.loads(evidence.read_text())
        if failures:
            raise RuntimeError(failures[-1])
        report["status"] = "completed"
    except (OSError, RuntimeError, KeyError, ValueError, subprocess.TimeoutExpired) as exc:
        report["error"] = str(exc)
    finally:
        stopped.set()
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        monitor.join(timeout=5)
        report["wall_seconds"] = time.perf_counter() - started
        report["peak_sampled_rss_bytes"] = max(
            (s.get("server_rss_bytes", 0) for s in samples), default=0
        )
        private = {"samples": samples}
        (dest / "thermal.json").write_text(json.dumps(private, indent=2), encoding="utf-8")
        report["gpu_summary"] = [
            {
                "name": label,
                "peak_c": max(s["gpus"][uuid]["temperature.gpu"] for s in samples),
                "peak_mib": max(float(s["gpus"][uuid]["memory.used"]) for s in samples),
                **power_summary([s["gpus"][uuid]["power.draw"] for s in samples]),
            }
            for uuid, label in zip(uuids, ("4070", "3060"), strict=True)
        ]
        (dest / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)
    return 0 if report["status"] == "completed" else 2


def power_summary(readings):
    watts = []
    for reading in readings:
        with suppress(ValueError):
            watts.append(float(reading))
    return {"peak_w": max(watts), "mean_w": sum(watts) / len(watts)} if watts else {}


def kv_allocations(runtime_log):
    allocations = defaultdict(float)
    for gpu, size in re.findall(r"CUDA(\d+)\s+KV buffer size\s*=\s*([\d.]+) MiB", runtime_log):
        allocations[f"CUDA{gpu}"] += float(size)
    return {device: round(size, 2) for device, size in allocations.items()}


def main():
    cli = argparse.ArgumentParser(description="Run a thermally supervised Inkling inference case")
    cli.add_argument("--model", required=True, type=Path)
    cli.add_argument("--projector", type=Path)
    cli.add_argument("--output", required=True, type=Path)
    cli.add_argument("--context", type=int, choices=(4096, 8192, 16384, 32768), required=True)
    cli.add_argument(
        "--prompt-context", type=int, choices=(4096, 8192, 16384, 32768), action="append"
    )
    cli.add_argument("--cache", choices=("f16", "q8_0"), default="f16")
    cli.add_argument("--split", default="1,1")
    cli.add_argument("--reasoning-budget", type=int, default=128, metavar="0-999")
    cli.add_argument("--quality", action="store_true")
    cli.add_argument("--goose-driver", type=Path, help="Explicit local integration driver")
    return validate(cli.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
