import json

import pytest

from rsec.data import load_rows
from rsec.errors import RsecError
from rsec.evaluate import evaluate, score
from rsec.predict import predict
from rsec.utils import jsonl, read_json, write_json


def test_fixed_labels_preserve_schema_across_subsets():
    cases = [{"id": "a", "expected": {"label": "vulnerable", "cwe": ["CWE-89"]}}]
    predictions = [
        {
            "id": "a",
            "label": "benign",
            "cwe": [],
            "references": [],
            "answer": "wrong but well formed",
        }
    ]
    result = score(cases, predictions)
    assert result["schema_compliance"] == 1
    assert result["per_label"]["benign"]["precision"] == 0
    assert result["per_label"]["vulnerable"]["recall"] == 0
    assert result["accuracy"] == 0
    assert result["unsupported_reference_rate"] is None


def test_metrics_hand_calculation():
    labels = ["vulnerable", "vulnerable", "benign", "benign", "insufficient"]
    answers = ["vulnerable", "benign", "vulnerable", "benign", "insufficient"]
    cases = [{"id": str(i), "expected": {"label": label}} for i, label in enumerate(labels)]
    rows = [
        {"id": str(i), "label": label, "cwe": [], "references": [], "answer": "fixture"}
        for i, label in enumerate(answers)
    ]
    result = score(cases, rows)
    assert result["accuracy"] == pytest.approx(3 / 5)
    assert result["micro_f1"] == pytest.approx(3 / 5)
    assert result["macro_f1"] == pytest.approx(2 / 3)
    assert result["false_positive_rate"] == result["false_negative_rate"] == 0.5
    assert result["per_label"]["vulnerable"] == dict(precision=0.5, recall=0.5, f1=0.5)
    assert score(cases, [])["missing_predictions"] == 5
    with pytest.raises(RsecError, match="Empty"):
        score([], [])


def test_prediction_ids_not_controlled_by_model_and_comparison_contract(tmp_path, monkeypatch):
    import importlib

    module = importlib.import_module("rsec.predict")
    refs = list(load_rows("tests/fixtures/reference_predictions.jsonl"))
    responses = iter(refs)

    def fake_infer(model, prompt, **kwargs):
        assert kwargs["temperature"] == 0
        return dict(
            answer=json.dumps({**next(responses), "id": "forged"}),
            latency_seconds=1,
            tokens_per_second=2,
            vram_bytes=None,
            chat_template_hash="template-fixture",
            system_hash="system-fixture",
        )

    monkeypatch.setattr(module, "infer", fake_infer)
    path = tmp_path / "predictions.jsonl"
    predict("benchmarks/suite.jsonl", "fixture", path)
    assert [r["id"] for r in load_rows(path)] == [r["id"] for r in refs]
    baseline = tmp_path / "base.json"
    evaluate("benchmarks/suite.jsonl", path, baseline, "base")
    report = evaluate("benchmarks/suite.jsonl", path, tmp_path / "new.json", "candidate", baseline)
    assert report["regression_passed"] is True
    meta = read_json(str(path) + ".meta.json")
    meta["conditions"]["max_tokens"] = 10
    write_json(str(path) + ".meta.json", meta, overwrite=True)
    with pytest.raises(RsecError, match="conditions"):
        evaluate("benchmarks/suite.jsonl", path, tmp_path / "bad.json", "candidate", baseline)
    meta["prediction_hash"] = "0" * 64
    write_json(str(path) + ".meta.json", meta, overwrite=True)
    with pytest.raises(RsecError, match="integrity"):
        evaluate("benchmarks/suite.jsonl", path, tmp_path / "bad.json", "candidate")


@pytest.mark.parametrize("answer", ["not json", "[]", "null"])
def test_malformed_predictions_are_schema_failures(tmp_path, monkeypatch, answer):
    import importlib

    module = importlib.import_module("rsec.predict")
    monkeypatch.setattr(
        module,
        "infer",
        lambda *a, **k: dict(
            answer=answer, latency_seconds=1, tokens_per_second=None, vram_bytes=None
        ),
    )
    path = tmp_path / "predictions.jsonl"
    predict("benchmarks/suite.jsonl", "fixture", path)
    report = evaluate("benchmarks/suite.jsonl", path, tmp_path / "report.json", "fixture")
    assert report["overall"]["schema_compliance"] == 0
    assert report["overall"]["accuracy"] == 0


def test_benchmark_mismatch_and_untrusted_execution_disabled(tmp_path):
    benchmark = tmp_path / "benchmark.jsonl"
    jsonl(
        benchmark,
        [{"id": "a", "domain": "x", "language": "en", "expected": {"label": "vulnerable"}}],
    )
    path = tmp_path / "pred.jsonl"
    jsonl(path, [])
    first = tmp_path / "first.json"
    evaluate(benchmark, path, first, "fixture")
    report = read_json(first)
    report["benchmark_hash"] = "0" * 64
    write_json(first, report, overwrite=True)
    with pytest.raises(RsecError, match="identical benchmark"):
        evaluate(benchmark, path, tmp_path / "new.json", "new", first)
    cfg = tmp_path / "config.yaml"
    cfg.write_text("dynamic_execution: true\n")
    with pytest.raises(RsecError, match="execution"):
        evaluate(benchmark, path, tmp_path / "new.json", "new", config=cfg)
    cfg.write_text("dynamic_execution: false\nlabels: [other]\n")
    with pytest.raises(RsecError, match="label"):
        evaluate(benchmark, path, tmp_path / "new.json", "new", config=cfg)
