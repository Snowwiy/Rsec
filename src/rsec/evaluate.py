"""Deterministic task scoring, independent of any commercial LLM judge."""

import math
from collections import defaultdict
from pathlib import Path

from rsec.data import load_rows
from rsec.errors import RsecError
from rsec.utils import digest, now, read_json, write_json


def divide(numerator, denominator):
    return numerator / denominator if denominator else None


def score(cases, predictions, labels=("vulnerable", "benign", "insufficient")):
    if not cases:
        raise RsecError("Empty benchmark")
    ids = [p["id"] for p in predictions]
    case_ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)) or len(case_ids) != len(set(case_ids)):
        raise RsecError("Duplicate benchmark/prediction IDs")
    if set(ids) - set(case_ids):
        raise RsecError("Unknown prediction IDs")
    lookup = {p["id"]: p for p in predictions}
    labels = sorted(set(labels))
    if not labels or any(c["expected"]["label"] not in labels for c in cases):
        raise RsecError("Benchmark label is outside the evaluation schema")
    correct = schema = unsupported = refs = fp = fn = positives = negatives = cwe_correct = 0
    per_label = {label: {"tp": 0, "fp": 0, "fn": 0} for label in labels}
    for case in cases:
        pred = lookup.get(case["id"], {})
        expected = case["expected"]
        label = pred.get("label")
        correct += label == expected["label"]
        valid = (
            isinstance(pred.get("answer"), str)
            and isinstance(pred.get("references"), list)
            and all(isinstance(r, str) for r in pred["references"])
            and label in labels
            and isinstance(pred.get("cwe"), list)
            and all(isinstance(c, str) for c in pred["cwe"])
        )
        schema += valid
        cwe_correct += valid and sorted(pred["cwe"]) == sorted(expected.get("cwe", []))
        claimed = pred.get("references", []) if valid else []
        refs += len(claimed)
        unsupported += sum(r not in expected.get("references", []) for r in claimed)
        positives += expected["label"] == "vulnerable"
        negatives += expected["label"] == "benign"
        fp += expected["label"] == "benign" and label == "vulnerable"
        fn += expected["label"] == "vulnerable" and label != "vulnerable"
        for name, counts in per_label.items():
            counts["tp"] += expected["label"] == name and label == name
            counts["fp"] += expected["label"] != name and label == name
            counts["fn"] += expected["label"] == name and label != name
    detailed = {}
    for label, counts in per_label.items():
        tp, false_p, false_n = counts["tp"], counts["fp"], counts["fn"]
        detailed[label] = {
            "precision": divide(tp, tp + false_p),
            "recall": divide(tp, tp + false_n),
            "f1": divide(2 * tp, 2 * tp + false_p + false_n),
        }
    tp = sum(v["tp"] for v in per_label.values())
    false_p = sum(v["fp"] for v in per_label.values())
    false_n = sum(v["fn"] for v in per_label.values())
    return {
        "cases": len(cases),
        "missing_predictions": len(cases) - len(predictions),
        "accuracy": correct / len(cases),
        "exact_match_label": correct / len(cases),
        "cwe_exact_match": cwe_correct / len(cases),
        "schema_compliance": schema / len(cases),
        "macro_f1": sum(v["f1"] or 0 for v in detailed.values()) / len(labels),
        "micro_f1": divide(2 * tp, 2 * tp + false_p + false_n),
        "false_positive_rate": divide(fp, negatives),
        "false_negative_rate": divide(fn, positives),
        "unsupported_reference_rate": divide(unsupported, refs),
        "per_label": detailed,
    }


def evaluate(
    benchmark, predictions, output, model_id, baseline=None, config="configs/evaluation.yaml"
):
    import yaml

    from rsec.utils import bounded_read

    settings = yaml.safe_load(bounded_read(config))
    if settings.get("dynamic_execution") is not False:
        raise RsecError("Dynamic model-generated code execution is not supported")
    cases, rows = list(load_rows(benchmark)), list(load_rows(predictions))
    if any(case["expected"]["label"] not in settings["labels"] for case in cases):
        raise RsecError("Benchmark label is outside the configured evaluation schema")
    sidecar = Path(str(predictions) + ".meta.json")
    generation = read_json(sidecar) if sidecar.exists() else None
    if generation and (
        generation["prediction_hash"] != digest(rows)
        or generation["benchmark_hash"] != digest(cases)
    ):
        raise RsecError("Prediction generation metadata integrity mismatch")
    report = {
        "created_at": now(),
        "model_id": model_id,
        "benchmark_hash": digest(cases),
        "prediction_hash": digest(rows),
        "overall": score(cases, rows, settings["labels"]),
        "evaluation_contract": digest(settings),
        "generation_contract": generation["conditions"] if generation else None,
        "domains": {},
        "languages": {},
        "limitations": [
            "Unsupported references are a proxy, not a semantic hallucination rate",
            "No execution of generated code; remediation success requires isolated reviewed tests",
            "Synthetic fixtures are plumbing checks, not a representative cybersecurity benchmark",
        ],
    }
    for key, section in (("domain", "domains"), ("language", "languages")):
        grouped = defaultdict(list)
        for case in cases:
            grouped[case[key]].append(case)
        for name, subset in grouped.items():
            selected = {c["id"] for c in subset}
            report[section][name] = score(
                subset, [p for p in rows if p["id"] in selected], settings["labels"]
            )
    for key in ("latency_seconds", "tokens_per_second", "vram_bytes"):
        values = [
            r[key]
            for r in rows
            if isinstance(r.get(key), (float, int))
            and not isinstance(r[key], bool)
            and math.isfinite(r[key])
            and r[key] >= 0
        ]
        report[key + "_mean"] = sum(values) / len(values) if values else None
    if baseline:
        previous = read_json(baseline)
        if previous["benchmark_hash"] != report["benchmark_hash"]:
            raise RsecError("Baseline must use the identical benchmark")
        if (
            not report["generation_contract"]
            or not report["generation_contract"].get("chat_templates")
            or not report["generation_contract"].get("system_hashes")
            or previous.get("generation_contract") != report["generation_contract"]
            or previous.get("evaluation_contract") != report["evaluation_contract"]
        ):
            raise RsecError(
                "Baseline requires identical recorded generation and evaluation conditions"
            )
        report["baseline_model"] = previous["model_id"]
        report["accuracy_delta"] = report["overall"]["accuracy"] - previous["overall"]["accuracy"]
        report["regression_passed"] = (
            report["accuracy_delta"] >= settings["release_gate"]["accuracy_delta_min"]
            and report["overall"]["macro_f1"] - previous["overall"]["macro_f1"]
            >= settings["release_gate"]["macro_f1_delta_min"]
            and report["overall"]["schema_compliance"] == 1
            and report["overall"]["missing_predictions"] == 0
        )
    write_json(output, report)
    return report
