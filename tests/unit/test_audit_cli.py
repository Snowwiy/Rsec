import importlib
import json
import subprocess

import pytest

from rsec.cli import main
from rsec.errors import RsecError
from rsec.utils import read_json


def test_actual_cli_data_lifecycle_and_reports(tmp_path, capsys):
    out = tmp_path / "data"
    assert (
        main(["data", "prepare", "--input", "data/samples/defensive.jsonl", "--output", str(out)])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["accepted"] == 12
    assert main(["data", "validate", str(out)]) == 0
    assert main(["data", "download"]) == 0
    assert main(["experiments", "list", "--root", str(tmp_path / "runs")]) == 0
    assert main(["models", "--root", str(tmp_path / "registry"), "list"]) == 0
    report = tmp_path / "evaluation.json"
    assert (
        main(
            [
                "evaluate",
                "--benchmark",
                "benchmarks/suite.jsonl",
                "--predictions",
                "tests/fixtures/reference_predictions.jsonl",
                "--model-id",
                "reference-fixture",
                "--output",
                str(report),
            ]
        )
        == 0
    )
    assert read_json(report)["overall"]["accuracy"] == 1
    assert (
        main(
            [
                "data",
                "prepare",
                "--input",
                "data/samples/defensive.jsonl",
                "--output",
                str(tmp_path / "bad"),
                "--category-cap",
                "0",
            ]
        )
        == 2
    )
    assert main(["doctor", "--output", str(tmp_path / "doctor.json")]) == 0
    assert read_json(tmp_path / "doctor.json")["gpu_validation"] == "not_verified"
    doc = tmp_path / "doc.md"
    doc.write_text("Review defensive evidence and preserve source provenance in all reports.")
    assert (
        main(
            [
                "data",
                "ingest",
                "--input",
                str(doc),
                "--output",
                str(tmp_path / "knowledge.jsonl"),
                "--source",
                "owner",
                "--source-url",
                "https://example.org/doc",
                "--license",
                "MIT",
                "--version",
                "1",
                "--redistribution",
                "allowed",
                "--reviewed",
            ]
        )
        == 0
    )


def test_cli_runtime_wiring_and_safe_error_output(tmp_path, monkeypatch, capsys):
    trainer = importlib.import_module("rsec.train")

    def fake_train(config, *args):
        assert config.local_files_only is False and config.max_steps == 1
        return {"status": "contract-only"}

    monkeypatch.setattr(trainer, "train", fake_train)
    assert (
        main(["train", "--smoke", "--allow-network", "--max-steps", "1", "--output", str(tmp_path)])
        == 0
    )
    predictor = importlib.import_module("rsec.predict")
    monkeypatch.setattr(predictor, "predict", lambda *a: {"contract": "only"})
    assert main(["predict", "--model", "fixture", "--output", str(tmp_path / "predictions")]) == 0
    exporter = importlib.import_module("rsec.export")
    monkeypatch.setattr(exporter, "export", lambda *a: {"contract": "only"})
    assert main(["export", "--source", "fixture", "--output", "unused"]) == 0
    runtime = importlib.import_module("rsec.inference")
    monkeypatch.setattr(runtime, "infer", lambda **k: {"contract": k["model"]})
    assert main(["infer", "--model", "fixture", "--prompt", "text"]) == 0
    config = tmp_path / "config.yaml"
    config.write_text("local_files_only: false\n")
    assert main(["infer", "--config", str(config), "--model", "fixture", "--prompt", "text"]) == 2
    config.write_text("unexpected: true\n")
    assert main(["infer", "--config", str(config), "--model", "fixture", "--prompt", "text"]) == 2
    for error in [
        OSError("sensitive-input-marker"),
        RuntimeError("sensitive-input-marker"),
        subprocess.CalledProcessError(1, ["tool"]),
        ImportError(name="optional_runtime"),
    ]:

        def fail(_error=error, **kwargs):
            raise _error

        monkeypatch.setattr(runtime, "infer", fail)
        assert main(["infer", "--model", "fixture", "--prompt", "text"]) == 2
        assert "sensitive-input-marker" not in capsys.readouterr().err


def test_hf_cli_provenance_routing(tmp_path, monkeypatch):
    from rsec import download

    def fake_acquire(dataset, revision, output, license, reviewed, split):
        assert reviewed is True and revision == "0" * 40 and license == "MIT"
        return {"contract": "only"}

    monkeypatch.setattr(download, "acquire_hf", fake_acquire)
    assert (
        main(
            [
                "data",
                "download-hf",
                "fixture",
                "--revision",
                "0" * 40,
                "--license",
                "MIT",
                "--reviewed",
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )


def test_training_guards_before_any_cuda_load(monkeypatch):
    from rsec.config import load_training
    from rsec.train import train

    module = importlib.import_module("rsec.train")
    monkeypatch.setattr(module, "doctor", lambda: {"cuda": True, "gpus": [{"bf16": False}]})
    config = load_training()
    with pytest.raises(RsecError, match="experimental"):
        train(config.model_copy(update={"strategy": "ddp"}))
    with pytest.raises(RsecError, match="Accelerate"):
        train(config.model_copy(update={"strategy": "ddp"}), allow_experimental=True)
    monkeypatch.setenv("WORLD_SIZE", "2")
    with pytest.raises(RsecError, match="Single-GPU"):
        train(config)
    with pytest.raises(RsecError, match="FSDP profile"):
        train(config.model_copy(update={"strategy": "fsdp"}), allow_experimental=True)
    with pytest.raises(RsecError, match="visible"):
        train(config.model_copy(update={"strategy": "ddp"}), allow_experimental=True)
    monkeypatch.setenv("WORLD_SIZE", "1")
    with pytest.raises(RsecError, match="Smoke mode"):
        train(config.model_copy(update={"adapter": "unused"}), smoke=True)
    with pytest.raises(RsecError, match="BF16"):
        train(config.model_copy(update={"precision": "bf16"}))
    with pytest.raises(RsecError, match="BLOCKED"):
        train(config.model_copy(update={"backend": "unsloth"}))


@pytest.mark.parametrize(
    "change",
    [
        {"max_steps": 0},
        {"target_modules": []},
        {"target_modules": ["q_proj", "q_proj"]},
        {"target_modules": [" "]},
        {"early_stopping_patience": 1, "save_steps": 2, "eval_steps": 3},
    ],
)
def test_invalid_training_config_fails(change):
    from rsec.config import Training, load_training

    with pytest.raises(ValueError):
        Training.model_validate({**load_training().model_dump(), **change})


def test_malformed_configuration_has_safe_cli_error(tmp_path, capsys):
    from rsec.config import load_training

    path = tmp_path / "config.yaml"
    path.write_text("[]\n")
    assert main(["config", "--config", str(path)]) == 2
    assert main(["infer", "--config", str(path), "--model", "fixture", "--prompt", "text"]) == 2
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles/test.yaml").write_text("[]")
    path.write_text("revision: " + "0" * 40)
    with pytest.raises(RsecError, match="mapping"):
        load_training(path, profile="test")
    assert "Traceback" not in capsys.readouterr().err
