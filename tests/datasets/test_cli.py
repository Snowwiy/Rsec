import json
from pathlib import Path

import pytest

from rsec.cli import main
from rsec.utils import jsonl, read_json


def test_all_dataset_commands_run_without_torch(tmp_path, capsys):
    assert main(["data", "sources"]) == 0
    assert json.loads(capsys.readouterr().out)["sources"] == 22
    generated = tmp_path / "pilot.jsonl"
    bench = tmp_path / "bench.jsonl"
    assert main(["data", "pilot", "--output", str(generated)]) == 0
    assert main(["data", "pilot", "--output", str(bench), "--benchmark"]) == 0
    assert main(["data", "pilot", "--output", str(generated)]) == 2
    root = tmp_path / "curated"
    assert (
        main(
            [
                "data",
                "curate",
                "--input",
                str(generated),
                "--output",
                str(root),
                "--version",
                "pilot-cli-test",
            ]
        )
        == 0
    )
    assert main(["data", "validate", str(root)]) == 0
    for action in ["quality", "quarantine", "stats", "version"]:
        assert main(["data", action, str(root)]) == 0
    assert main(["data", "review", str(root), "--output", str(tmp_path / "review.json")]) == 0
    assert read_json(tmp_path / "review.json")["records"]
    assert main(["data", "split", str(root), "--output", str(tmp_path / "sft")]) == 2
    assert not (tmp_path / "sft").exists()
    stats = tmp_path / "stats.json"
    assert main(["data", "stats", str(root), "--output", str(stats)]) == 0
    assert read_json(stats)["tokenizer_tokens"] is None
    for action in ["list", "validate"]:
        assert main(["benchmark", action]) == 0
    assert main(["benchmark", "contamination-check", "--input", str(generated)]) == 0
    preds = tmp_path / "preds.jsonl"
    jsonl(preds, [])
    assert (
        main(
            [
                "benchmark",
                "evaluate",
                "--predictions",
                str(preds),
                "--output",
                str(tmp_path / "bench-report.json"),
            ]
        )
        == 0
    )
    assert (
        read_json(tmp_path / "bench-report.json")["mechanical_metrics"]["missing_predictions"] == 32
    )


def test_cli_expert_fixture_split_and_versioning(tmp_path, subset, decision_for):
    path = tmp_path / "input.jsonl"
    jsonl(path, subset)
    decisions = tmp_path / "decisions.jsonl"
    jsonl(decisions, [decision_for(r) for r in subset])
    root = tmp_path / "release"
    assert (
        main(
            [
                "data",
                "curate",
                "--input",
                str(path),
                "--output",
                str(root),
                "--version",
                "test-only-attestations",
                "--decisions",
                str(decisions),
            ]
        )
        == 0
    )
    assert main(["data", "split", str(root), "--output", str(tmp_path / "sft")]) == 0
    assert main(["data", "validate", str(tmp_path / "sft")]) == 0
    assert read_json(root / "release_status.json")["expert_approved_sft"] == 8


@pytest.mark.parametrize(
    "argv",
    [
        ["data", "curate"],
        ["data", "review"],
        ["benchmark", "unknown"],
        ["data", "curate", "--input", "x", "--output", "y"],
        ["data", "pilot"],
    ],
)
def test_missing_arguments_are_nonzero(argv):
    with pytest.raises(SystemExit) as error:
        main(argv)
    assert error.value.code == 2


@pytest.mark.parametrize(
    "benchmark,target",
    [
        (False, "data/pilot/candidates.jsonl"),
        (True, "benchmarks/rsec_cyberbench/development.jsonl"),
    ],
)
def test_generator_reproduces_frozen_fixture_bytes(tmp_path, benchmark, target):
    from rsec.datasets.pilot import generate
    from rsec.utils import sha256

    path = tmp_path / "generated.jsonl"
    result = generate(path, benchmark)
    assert path.read_bytes() == Path(target).read_bytes()
    assert result["sha256"] == read_json(target + ".manifest.json")["sha256"] == sha256(path)
