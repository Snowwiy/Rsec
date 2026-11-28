import json
import subprocess
from types import SimpleNamespace

import pytest

from rsec import local, thermal


def test_inventory_paths_formats_and_external_links(tmp_path):
    library = tmp_path / "AI Local"
    base = library / "offline base"
    base.mkdir(parents=True)
    (base / "model.safetensors").write_bytes(b"fixture")
    (base / "config.json").write_text('{"model_type":"llama"}')
    (base / "tokenizer.json").touch()
    adapter = library / "adapter"
    adapter.mkdir()
    (adapter / "x.safetensors").touch()
    (adapter / "adapter_config.json").touch()
    (adapter / "config.json").write_text("[")
    (library / "test.gguf").write_bytes(b"GGUF\x03\0\0\0")
    (library / "bad.gguf").touch()
    (library / "loop").symlink_to(library, target_is_directory=True)
    rows = local.inventory(library)
    by_name = {r["name"]: r for r in rows["models"]}
    assert set(by_name) == {"offline base", "adapter", "test.gguf", "bad.gguf"}
    assert (
        by_name["test.gguf"]["header_recognized"] and not by_name["bad.gguf"]["header_recognized"]
    )
    assert by_name["adapter"]["format"] == "LoRA candidate"
    assert by_name["offline base"]["architecture"] == "llama"
    assert rows["unreadable_or_invalid"] == 1


def test_probe_only_generates_for_installed_baseline(monkeypatch):
    requests = []

    def request(port, path, payload=None):
        requests.append(payload)
        if payload is None:
            return {"data": [{"id": "fixture"}]}
        return {"choices": [{"message": {"content": "1"}}], "usage": {"completion_tokens": 1}}

    monkeypatch.setattr(local, "request", request)
    with pytest.raises(ValueError, match="absent"):
        local.probe(8081, "missing")
    assert requests == [None]
    assert local.probe(8081, "fixture", catalog_only=True) == {
        "status": "LOCAL_BASELINE_LISTED",
        "model": "fixture",
    }
    assert requests == [None, None]
    monkeypatch.setattr(local.time, "perf_counter", lambda: 123.0)
    result = local.probe(8081, "fixture")
    assert result["completion_tokens"] == 1
    assert result["end_to_end_tokens_per_second"] is None
    assert requests[-1]["max_tokens"] == 8


@pytest.mark.parametrize(
    "text", ["GPU-other,32,20,2,4,1", "GPU-one,N/A,20,2,4,1", "GPU-one,nan,20,2,4,1"]
)
def test_missing_temperature_fails_closed(monkeypatch, text):
    text += "," + ",".join(["[N/A]"] * (len(thermal.METRICS) - 6))
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=text))
    with pytest.raises(ValueError):
        thermal.sample(["GPU-one"])


def test_overheat_stops_before_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(thermal, "sample", lambda ids: {ids[0]: {"temperature.gpu": 85}})
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: pytest.fail("Unexpected workload"))
    out = tmp_path / "private"
    with pytest.raises(RuntimeError, match="limit"):
        thermal.supervise(["GPU-one"], out)
    report = json.loads((out / "thermal.json").read_text())
    assert report["status"] == "interrupted" and report["samples"][0]["warning"]


def test_duplicate_devices_cannot_launch_ddp(tmp_path):
    with pytest.raises(ValueError, match="distinct"):
        thermal.supervise(["GPU-one"] * 2, tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


def test_check_both_cards_and_stop_on_thermal_throttling(tmp_path, monkeypatch):
    def sensors(watched):
        assert watched == ["GPU-worker", "GPU-observed"]
        return {
            "GPU-worker": {"temperature.gpu": 55},
            "GPU-observed": {"temperature.gpu": 73, thermal.THERMAL_FLAGS[0]: "Active"},
        }

    monkeypatch.setattr(thermal, "sample", sensors)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: pytest.fail("Unexpected workload"))
    with pytest.raises(RuntimeError, match="throttling"):
        thermal.supervise(["GPU-worker"], tmp_path / "private", watch=["GPU-observed"])


def test_single_mode_rejects_two_gpu_worker(tmp_path):
    with pytest.raises(ValueError, match="GPU count|NCCL"):
        thermal.supervise(["GPU-one", "GPU-two"], tmp_path / "absent", mode="single")
    assert not (tmp_path / "absent").exists()


def test_single_supervision_preserves_caller_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "original")
    monkeypatch.setattr(thermal.time, "sleep", lambda _: None)
    monkeypatch.setattr(thermal, "sample", lambda ids: {ids[0]: {"temperature.gpu": 60}})
    runs = []

    def launch(argv, **kw):
        runs.append((argv, kw))
        return SimpleNamespace(poll=lambda: 0, returncode=0)

    monkeypatch.setattr(subprocess, "Popen", launch)
    thermal.supervise(["GPU-one"], tmp_path / "private")
    assert runs[0][1]["env"]["CUDA_VISIBLE_DEVICES"] == "GPU-one"
    assert thermal.os.environ["CUDA_VISIBLE_DEVICES"] == "original"
    assert json.loads((tmp_path / "private/thermal.json").read_text())["status"] == "completed"


def test_goose_reports_routing_without_credentials(tmp_path):
    path = tmp_path / "chosen config.yaml"
    path.write_text(
        "GOOSE_PROVIDER: ollama\nGOOSE_MODEL: baseline\nOLLAMA_HOST: http://name:example@127.0.0.1:11434/path?private=example\nOTHER: example\n"
    )
    assert local.goose_settings(path) == {
        "GOOSE_PROVIDER": "ollama",
        "GOOSE_MODEL": "baseline",
        "OLLAMA_HOST": {"loopback": True, "port": 11434},
    }
    path.write_text(
        "active_provider: openai\nproviders:\n  openai:\n    model: local-baseline\n    api_key: example\n"
    )
    assert local.goose_settings(path) == {
        "GOOSE_PROVIDER": "openai",
        "GOOSE_MODEL": "local-baseline",
    }


@pytest.mark.skipif(thermal.os.name != "posix", reason="POSIX process groups")
def test_sensor_loss_stops_running_worker(tmp_path, monkeypatch):
    readings = iter([{"GPU-one": {"temperature.gpu": 65}}, None])

    def sensor(ids):
        row = next(readings)
        if row is None:
            raise ValueError("lost sensor")
        return row

    stopped = []
    monkeypatch.setattr(thermal, "sample", sensor)
    monkeypatch.setattr(thermal.time, "sleep", lambda _: None)
    monkeypatch.setattr(thermal.os, "killpg", lambda pid, sig: stopped.append(pid))
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *args, **kw: SimpleNamespace(pid=123, poll=lambda: None, wait=lambda: None),
    )
    with pytest.raises(ValueError, match="lost sensor"):
        thermal.supervise(["GPU-one"], tmp_path / "run")
    assert stopped == [123]
    assert json.loads((tmp_path / "run/thermal.json").read_text())["status"] == "interrupted"


def test_gguf_scalar_metadata_with_bounded_incomplete_tail(tmp_path):
    import struct

    def string(value):
        encoded = value.encode()
        return struct.pack("<Q", len(encoded)) + encoded

    path = tmp_path / "base.gguf"
    path.write_bytes(
        b"GGUF"
        + struct.pack("<IQQ", 3, 7, 3)
        + string("general.architecture")
        + struct.pack("<I", 8)
        + string("llama")
        + string("general.file_type")
        + struct.pack("<II", 4, 15)
        + struct.pack("<Q", 2**40)
    )
    assert local.gguf_metadata(path) == {"general.architecture": "llama", "general.file_type": 15}


def test_http_probe_cli_writes_private_metrics(tmp_path, monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"data":[{"id":"fixture"}]}')

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert payload["model"] == "fixture"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b'{"choices":[{"message":{"content":"private-text"}}],"usage":{"completion_tokens":2}}'
            )

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            path = tmp_path / "space here" / "result.json"
            monkeypatch.setattr(
                "sys.argv",
                [
                    "local",
                    "probe",
                    "--model",
                    "fixture",
                    "--port",
                    str(server.server_port),
                    "--output",
                    str(path),
                ],
            )
            local.main()
            assert json.loads(path.read_text())["completion_tokens"] == 2
            assert "private-text" not in path.read_text()
        finally:
            server.shutdown()
            thread.join()


@pytest.mark.skipif(thermal.os.name != "posix", reason="Bash workstation wrapper")
def test_wsl_paths_with_spaces_confined_to_project(tmp_path):
    import shutil
    import sys
    from pathlib import Path

    root = tmp_path / "project with spaces"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "workstation_wsl.sh"
    shutil.copy(Path(__file__).parents[2] / "scripts" / script.name, script)
    run = subprocess.run(
        ["bash", str(script), "-c", "import os; print(os.environ['HF_HOME'])"],
        env={**thermal.os.environ, "RSEC_CUDA_PYTHON": sys.executable},
        capture_output=True,
        text=True,
        check=True,
    )
    assert run.stdout.strip() == str(root / ".rsec-local/cache/huggingface")
    assert (root / ".rsec-local/tmp").is_dir()


@pytest.mark.skipif(thermal.os.name != "posix", reason="Bash workstation wrapper")
def test_llama_wsl_direct_load_uses_installed_cli_flag(tmp_path):
    from pathlib import Path
    from uuid import UUID

    fixture_id = f"GPU-{UUID(int=1)}"
    smi = tmp_path / "nvidia-smi"
    smi.write_text("#!/usr/bin/env bash\nprintf 'NVIDIA GeForce RTX 3060, 10000\\n'\n")
    smi.chmod(0o755)
    server = tmp_path / "mock-server"
    server.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$1" == --list-devices ]]; then\n'
        "  printf '  CUDA0: NVIDIA GeForce RTX 3060 (12288 MiB)\\n'\n"
        "else\n"
        '  printf "%s\\n" "$CUDA_VISIBLE_DEVICES" "$@"\n'
        "fi\n"
    )
    server.chmod(0o755)
    model = tmp_path / "fixture with spaces.gguf"
    model.touch()
    projector = tmp_path / "projector with spaces.gguf"
    projector.touch()
    script = Path(__file__).parents[2] / "scripts" / "llama_wsl.sh"
    run = subprocess.run(
        ["bash", str(script), str(model), fixture_id],
        env={
            "PATH": str(tmp_path) + ":" + thermal.os.environ["PATH"],
            "RSEC_LLAMA_SERVER": str(server),
            "RSEC_LLAMA_PROFILE": "gaming",
            "RSEC_LLAMA_MMAP": "0",
            "RSEC_LLAMA_ALIAS": "inkling-test",
            "RSEC_LLAMA_MMPROJ": str(projector),
            "RSEC_LLAMA_KV_CACHE": "q8_0",
            "RSEC_LLAMA_REASONING_BUDGET": "128",
        },
        capture_output=True,
        text=True,
        check=True,
    )
    arguments = run.stdout.splitlines()
    assert arguments[0] == fixture_id
    assert arguments[arguments.index("--load-mode") + 1] == "none"
    assert arguments[arguments.index("-m") + 1] == str(model)
    assert arguments[arguments.index("--mmproj") + 1] == str(projector)
    assert arguments[arguments.index("--alias") + 1] == "inkling-test"
    assert arguments[arguments.index("--cache-type-v") + 1] == "q8_0"
    assert arguments[arguments.index("--reasoning-budget") + 1] == "128"
    assert "--no-mmap" not in arguments


@pytest.mark.parametrize(
    "metadata", [{"remote_host": "example.invalid", "details": {"format": "gguf"}}, {"details": {}}]
)
def test_goose_rejects_unverified_local_model(monkeypatch, metadata):
    def request(port, path, payload):
        assert path == "/api/show"
        return metadata

    monkeypatch.setattr(local, "request", request)
    with pytest.raises(ValueError, match="installed Ollama"):
        local.probe(11434, "baseline", ollama=True)
