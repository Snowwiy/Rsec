import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from rsec.cli import main
from rsec.config import load_training
from rsec.evaluate import evaluate, score
from rsec.tracking import Experiment, Registry
from rsec.utils import atomic_write, confined, read_json


def test_all_hardware_profiles_validate():
    for path in Path("configs/profiles").glob("*.yaml"):
        assert load_training(profile=path.stem).context >= 64


def test_invalid_revision_and_backend():
    config = load_training()
    for delta in (
        {"revision": "main"},
        {"backend": "unsloth", "strategy": "ddp"},
        {"context": 0},
        {"unexpected": True},
    ):
        with pytest.raises(ValidationError):
            type(config).model_validate({**config.model_dump(), **delta})


def test_atomic_no_overwrite_and_confined_path(tmp_path):
    path = tmp_path / "out"
    atomic_write(path, "first")
    with pytest.raises(FileExistsError):
        atomic_write(path, "second")
    assert path.read_text() == "first"
    with pytest.raises(ValueError):
        confined(tmp_path, "../outside")
    link = tmp_path / "link"
    link.symlink_to(tmp_path.parent)
    with pytest.raises(ValueError):
        confined(tmp_path, "link/file")


def test_metrics_with_errors_missing_and_unsupported_references():
    cases = [
        {"id": "a", "expected": {"label": "vulnerable", "cwe": [], "references": []}},
        {"id": "b", "expected": {"label": "benign", "cwe": [], "references": []}},
    ]
    rows = [
        {"id": "a", "label": "benign", "cwe": [], "references": ["invented"], "answer": "incorrect"}
    ]
    result = score(cases, rows)
    assert result["accuracy"] == 0
    assert result["missing_predictions"] == 1
    assert result["false_negative_rate"] == 1
    assert result["unsupported_reference_rate"] == 1
    with pytest.raises(ValueError, match="Duplicate"):
        score(cases, rows * 2)
    with pytest.raises(ValueError, match="Unknown"):
        score(cases, [{**rows[0], "id": "other"}])


def test_reference_fixture_scoring_and_regression_gate(tmp_path):
    first = tmp_path / "a.json"
    report = evaluate(
        "benchmarks/suite.jsonl",
        "tests/fixtures/reference_predictions.jsonl",
        first,
        "reference-fixture",
    )
    assert report["overall"]["accuracy"] == 1
    assert report["latency_seconds_mean"] is None
    with pytest.raises(ValueError, match="conditions"):
        evaluate(
            "benchmarks/suite.jsonl",
            "tests/fixtures/reference_predictions.jsonl",
            tmp_path / "b.json",
            "reference-fixture-copy",
            first,
        )


def test_experiment_record_and_collision(tmp_path):
    run = Experiment(tmp_path, {"seed": 42}, run_id="run-abc")
    run.log({"step": 1, "loss": 2.0})
    run.finish("completed")
    assert read_json(run.path / "run.json")["status"] == "completed"
    assert (run.path / "metrics.csv").exists()
    with pytest.raises(FileExistsError):
        Experiment(tmp_path, {}, run_id="run-abc")


def test_registry_refuses_nonexistent_models(tmp_path):
    registry = Registry(tmp_path)
    assert registry.list() == []
    with pytest.raises(ValueError, match="Missing"):
        registry.register({"id": "fake"})


def test_registry_register_activate_and_integrity(tmp_path):
    import struct

    weights = tmp_path / "fixture.safetensors"
    header = json.dumps({"weight": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}).encode()
    header += b" " * (-len(header) % 8)
    weights.write_bytes(struct.pack("<Q", len(header)) + header + struct.pack("<f", 1.0))
    metadata = {
        "id": "fixture-only",
        "rsec_version": "0.1.0a0",
        "base_model": "local-test-fixture",
        "revision": "0" * 40,
        "architecture": "test-fixture",
        "adapters": [],
        "config": {},
        "dataset_hash": "0" * 64,
        "trained_at": None,
        "hardware": {},
        "commit": "0" * 40,
        "metrics": {},
        "license": "MIT",
        "artifacts": [str(weights)],
        "validation": "TESTED",
        "compatibility": [],
        "limitations": ["Fixture, not trained cybersecurity weights"],
    }
    registry = Registry(tmp_path / "registry")
    registry.register(metadata)
    assert registry.activate("fixture-only")["active"] == "fixture-only"
    with pytest.raises(FileExistsError):
        registry.register(metadata)
    weights.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="integrity"):
        registry.activate("fixture-only")


@pytest.mark.parametrize(
    "argv",
    [
        ["--version"],
        ["--help"],
        ["train", "--help"],
        ["data", "prepare", "--help"],
        ["export", "--help"],
        ["infer", "--help"],
    ],
)
def test_cli_help(argv):
    with pytest.raises(SystemExit) as stopped:
        main(argv)
    assert stopped.value.code == 0


def test_cli_config_and_error(capsys):
    assert main(["config"]) == 0
    assert json.loads(capsys.readouterr().out)["rank"] == 16
    assert main(["data", "validate", "no-such-release"]) == 2
    assert "rsec:" in capsys.readouterr().err


def test_no_gpu_training_has_clear_preflight(monkeypatch):
    from rsec import train

    monkeypatch.setattr(train, "doctor", lambda: {"cuda": False})
    with pytest.raises(ValueError, match="CUDA"):
        train.train(load_training())
