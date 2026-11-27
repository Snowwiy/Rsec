"""Private workstation inventory and loopback-only inference checks."""

import argparse
import http.client
import json
import os
import stat
import struct
import time
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from rsec.utils import bounded_read, write_json


def regular(entry, directory=False):
    info = entry.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    return expected(info.st_mode) and not (
        stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def gguf_metadata(path):
    # Read scalar metadata preceding the tokenizer arrays. Cap bytes and fields on untrusted files.
    formats = {
        0: "B",
        1: "b",
        2: "H",
        3: "h",
        4: "I",
        5: "i",
        6: "f",
        7: "?",
        10: "Q",
        11: "q",
        12: "d",
    }
    keys = {
        "general.architecture",
        "general.name",
        "general.size_label",
        "general.file_type",
        "general.license",
        "general.parameter_count",
        "tokenizer.ggml.model",
    }
    result = {}
    with path.open("rb") as stream:

        def read(n):
            if n > 65536 or stream.tell() + n > 2**20:
                raise ValueError("Metadata limit")
            data = stream.read(n)
            if len(data) != n:
                raise ValueError("Truncated metadata")
            return data

        def number(fmt):
            return struct.unpack("<" + fmt, read(struct.calcsize("<" + fmt)))[0]

        def string():
            return read(number("Q")).decode("utf-8")

        try:
            if read(4) != b"GGUF" or number("I") not in (2, 3):
                return result
            number("Q")
            fields = number("Q")
            for _ in range(min(fields, 256)):
                key = string()
                kind = number("I")
                if kind == 8:
                    value = string()
                elif kind in formats:
                    value = number(formats[kind])
                else:
                    break
                if key in keys:
                    result[key] = value
        except (ValueError, UnicodeError):
            pass
    return result


def inventory(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Expected a model library directory")
    models = []
    skipped = 0

    def onerror(_):
        nonlocal skipped
        skipped += 1

    for directory, children, files in os.walk(root, onerror=onerror):
        parent = Path(directory)
        children[:] = sorted(name for name in children if regular(parent / name, directory=True))
        names = {name for name in files if regular(parent / name)}
        weights = sorted(name for name in names if name.lower().endswith(".safetensors"))
        tokenizer = sorted(names & {"tokenizer.json", "tokenizer.model", "vocab.json"})
        config = {}
        if "config.json" in names:
            try:
                config = json.loads(bounded_read(parent / "config.json", 2**20))
                if not isinstance(config, dict):
                    raise ValueError("Invalid model config")
            except (ValueError, RuntimeError, OSError):
                config = {}
                skipped += 1
        for name in sorted(names):
            if name.lower().endswith(".gguf"):
                file = parent / name
                with file.open("rb") as stream:
                    header = stream.read(8)
                models.append(
                    dict(
                        path=str(file),
                        name=name,
                        format="GGUF",
                        metadata=gguf_metadata(file),
                        header_recognized=header[:4] == b"GGUF"
                        and int.from_bytes(header[4:], "little") in (2, 3),
                        bytes=file.stat().st_size,
                        use="llama.cpp / Ollama inference candidate only",
                    )
                )
        if weights:
            adapter = "adapter_config.json" in names
            models.append(
                dict(
                    path=str(parent),
                    name=parent.name,
                    format="LoRA candidate" if adapter else "Safetensors",
                    bytes=sum((parent / name).stat().st_size for name in weights),
                    architecture=config.get("model_type"),
                    quantization=config.get("quantization_config"),
                    tokenizer=tokenizer,
                    weights=weights,
                    license_files=sorted(
                        n for n in names if n.lower().startswith(("license", "copying"))
                    ),
                    use="verify base revision"
                    if adapter
                    else "verify shards, tokenizer, license and architecture before loading",
                )
            )
    return {
        "models": models,
        "unreadable_or_invalid": skipped,
        "scope": "regular local GGUF and Safetensors; metadata only, rights and runtime compatibility require review",
    }


def goose_settings(path):
    """Read only documented routing fields into the private report."""
    cfg = yaml.safe_load(bounded_read(path, 256 * 1024))
    if not isinstance(cfg, dict):
        raise ValueError("Invalid Goose config")
    result = {
        key: cfg.get(key)
        for key in ("GOOSE_PROVIDER", "GOOSE_MODEL")
        if isinstance(cfg.get(key), str)
    }
    for key in ("OLLAMA_HOST", "OPENAI_HOST"):
        host = cfg.get(key)
        if isinstance(host, str):
            url = urlsplit(host if "://" in host else "http://" + host)
            result[key] = {
                "loopback": url.hostname in {"localhost", "127.0.0.1", "::1"},
                "port": url.port,
            }
    return result


def request(port, path, payload=None):
    if not 1 <= port <= 65535:
        raise ValueError("Invalid local port")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    try:
        conn.request(
            "GET" if payload is None else "POST",
            path,
            body=json.dumps(payload) if payload is not None else None,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        data = response.read(1024 * 1024 + 1)
        if response.status != 200 or len(data) > 1024 * 1024:
            raise ValueError(f"Local runtime rejected request (HTTP {response.status})")
        return json.loads(data)
    finally:
        conn.close()


def probe(port, model, *, ollama=False):
    if ollama:
        info = request(port, "/api/show", {"model": model})
        if (
            info.get("remote_model")
            or info.get("remote_host")
            or model.endswith("-cloud")
            or model.endswith(":cloud")
            or not info.get("details", {}).get("format")
        ):
            raise ValueError("Expected an installed Ollama model with local format metadata")
    ids = [row["id"] for row in request(port, "/v1/models")["data"]]
    if model not in ids:
        raise ValueError("Baseline is absent from local server inventory")
    start = time.monotonic()
    reply = request(
        port,
        "/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with one digit."}],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 8,
        },
    )
    elapsed = time.monotonic() - start
    if not (reply["choices"][0]["message"].get("content") or "").strip():
        raise ValueError("Empty completion")
    tokens = reply.get("usage", {}).get("completion_tokens")
    return {
        "status": "LOCAL_BASELINE_RESPONSE",
        "model": model,
        "elapsed_seconds": elapsed,
        "completion_tokens": tokens,
        "end_to_end_tokens_per_second": tokens / elapsed if tokens else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    inv = subs.add_parser("inventory")
    inv.add_argument("library", type=Path)
    inv.add_argument("--output", type=Path, required=True)
    check = subs.add_parser("probe")
    check.add_argument("--port", type=int, required=True)
    check.add_argument("--model", required=True)
    check.add_argument("--ollama", action="store_true")
    check.add_argument("--output", type=Path, required=True)
    goose = subs.add_parser("goose-config")
    goose.add_argument("config", type=Path)
    goose.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "inventory":
        value = inventory(args.library)
    elif args.action == "goose-config":
        value = goose_settings(args.config)
    else:
        value = probe(args.port, args.model, ollama=args.ollama)
    write_json(args.output, value)


if __name__ == "__main__":
    main()
