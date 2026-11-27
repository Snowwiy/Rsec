import copy
from pathlib import Path

import pytest
import yaml

from rsec.data import load_rows
from rsec.datasets.benchmark import check_contamination, evaluate_benchmark, validate
from rsec.datasets.knowledge import normalize_cve
from rsec.datasets.registry import acquire_registry
from rsec.datasets.schema import Candidate
from rsec.datasets.stats import distribution, statistics
from rsec.errors import RsecError
from rsec.utils import jsonl, read_json, sha256, write_json


def acquisition_fixture(tmp_path):
    root = tmp_path / "cache"
    root.mkdir()
    path = root / "small.json"
    write_json(
        path,
        {
            "cveMetadata": {
                "cveId": "CVE-2021-44228",
                "state": "PUBLISHED",
                "datePublished": "2021-12-10",
            }
        },
    )
    raw = read_json("data/manifests/source_registry.json")
    cve = next(s for s in raw["sources"] if s["id"] == "cve-program")
    cve["snapshots"] = {"small.json": sha256(path)}
    registry = tmp_path / "registry.json"
    write_json(registry, raw)
    entry = {
        "source_id": "cve-program",
        "revision": cve["version"],
        "filename": "small.json",
        "url": "https://raw.githubusercontent.com/fixture/small.json",
        "sha256": sha256(path),
    }
    settings = {"allowed_hosts": ["raw.githubusercontent.com"], "registered_sources": [entry]}
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(settings))
    return root, path, registry, config, settings


def test_pinned_cache_needs_no_network_or_dns(tmp_path, monkeypatch):
    root, path, registry, config, settings = acquisition_fixture(tmp_path)
    monkeypatch.setattr(
        "socket.getaddrinfo", lambda *a, **k: pytest.fail("No DNS allowed for a verified cache hit")
    )
    result = acquire_registry(config, root, registry)
    assert result["network_requests_needed"] == 0 and result["sources"][0]["status"] == "cached"
    assert read_json(str(path) + ".provenance.json")["sha256"] == sha256(path)
    normalized = tmp_path / "knowledge.jsonl"
    assert normalize_cve([path], normalized, registry)["sft_eligible"] == 0
    row = next(load_rows(normalized))
    assert row["trusted"] is False and row["sft_eligible"] is False
    assert "messages" not in row
    path.write_text("corrupted")
    with pytest.raises(RsecError, match="integrity"):
        acquire_registry(config, root, registry)
    with pytest.raises(RsecError, match="integrity"):
        normalize_cve([path], tmp_path / "bad", registry)


@pytest.mark.parametrize(
    "attack",
    [
        "wrong_revision",
        "wrong_hash",
        "wrong_host",
        "path_traversal",
        "no_rights",
        "unapproved",
        "unknown_source",
        "sensitive_url",
    ],
)
def test_acquisition_permissions_hash_and_path_fail_before_network(tmp_path, attack):
    root, path, registry, config, settings = acquisition_fixture(tmp_path)
    entry = settings["registered_sources"][0]
    if attack == "wrong_revision":
        entry["revision"] = "unverified"
    elif attack == "wrong_hash":
        entry["sha256"] = "0" * 64
    elif attack == "wrong_host":
        entry["url"] = "https://example.org/small.json"
    elif attack == "path_traversal":
        entry["filename"] = "../escape"
    elif attack == "unknown_source":
        entry["source_id"] = "missing"
    elif attack == "sensitive_url":
        entry["url"] += "?password=" + ("aB8x" * 6)
    else:
        raw = read_json(registry)
        cve = next(s for s in raw["sources"] if s["id"] == "cve-program")
        if attack == "no_rights":
            cve["download_allowed"] = False
        else:
            cve["status"] = "REVIEW REQUIRED"
        write_json(registry, raw, overwrite=True)
    config.write_text(yaml.safe_dump(settings))
    with pytest.raises((RsecError, ValueError)):
        acquire_registry(config, root, registry)


def test_registered_transport_delegates_bounded_downloader(tmp_path, monkeypatch):
    root, path, registry, config, settings = acquisition_fixture(tmp_path)
    payload = path.read_bytes()
    path.unlink()

    def fake(source, destination, hosts):
        assert source["sha256"] == settings["registered_sources"][0]["sha256"]
        assert hosts == ["raw.githubusercontent.com"] and source["reviewed"] is True
        Path(destination).write_bytes(payload)
        return {"status": "downloaded", "sha256": source["sha256"]}

    monkeypatch.setattr("rsec.datasets.registry.download_source", fake)
    assert acquire_registry(config, root, registry)["sources"][0]["status"] == "downloaded"


def test_cve_state_duplicates_and_reference_permission(tmp_path):
    root, path, registry, config, settings = acquisition_fixture(tmp_path)
    with pytest.raises(RsecError, match="Duplicate"):
        normalize_cve([path, path], tmp_path / "dup", registry)
    raw = read_json(registry)
    cve = next(s for s in raw["sources"] if s["id"] == "cve-program")
    cve["status"] = "REVIEW REQUIRED"
    write_json(registry, raw, overwrite=True)
    with pytest.raises(RsecError, match="rights"):
        normalize_cve([path], tmp_path / "blocked", registry)
    cve["status"] = "APPROVED"
    write_json(
        path, {"cveMetadata": {"cveId": "CVE-2099-9999999", "state": "REJECTED"}}, overwrite=True
    )
    cve["snapshots"]["small.json"] = sha256(path)
    write_json(registry, raw, overwrite=True)
    with pytest.raises(RsecError, match="identifier/state"):
        normalize_cve([path], tmp_path / "bad", registry)


def test_development_benchmark_mechanical_metrics_are_not_expert_gold(tmp_path):
    report = validate()
    assert report["cases"] == 32 and report["families"] == 15
    assert report["labels"] == {"insufficient": 12, "benign": 10, "vulnerable": 10}
    assert report["human_gold_certified"] is False and report["expert_reviewed"] == 0
    raw = list(load_rows("benchmarks/rsec_cyberbench/development.jsonl"))
    predictions = tmp_path / "predictions.jsonl"
    jsonl(
        predictions,
        [
            {
                "id": r["id"],
                "label": r["expected_label"],
                "cwe": r["expected_cwe"],
                "references": [ref["id"] for ref in r["references"]],
                "answer": "controlled scorer fixture",
            }
            for r in raw
        ],
    )
    result = evaluate_benchmark(predictions, tmp_path / "report.json")
    assert result["mechanical_metrics"]["accuracy"] == 1
    assert result["semantic_hallucinations"] is None and result["category_rubric_scores"] is None
    assert not check_contamination(
        ["data/pilot/candidates.jsonl"],
        ["benchmarks/suite.jsonl", "benchmarks/rsec_cyberbench/development.jsonl"],
    )["contaminated_ids"]
    with pytest.raises(RsecError, match="reserved"):
        check_contamination(["data/pilot/candidates.jsonl"], [])
    duplicate = tmp_path / "dup.jsonl"
    jsonl(duplicate, [raw[0], raw[0]])
    with pytest.raises(RsecError, match="duplicate"):
        validate(duplicate)
    bad = copy.deepcopy(raw[0])
    bad["purpose"] = "sft"
    path = tmp_path / "bad.jsonl"
    jsonl(path, [bad])
    with pytest.raises(RsecError, match="Invalid"):
        validate(path)


def test_statistics_without_tokenizer_are_not_token_measurements(subset):
    rows = [Candidate.model_validate(r) for r in subset]
    result = statistics(rows)
    assert result["records"] == 8 and result["whitespace_units"]["sum"] > 0
    assert result["tokenizer_tokens"] is None and result["tokens_per_epoch_eligible_sft"] is None
    assert distribution([])["mean"] is None
    assert distribution([1, 2, 3, 4]) == {
        "count": 4,
        "mean": 2.5,
        "median": 2.5,
        "p90": 3.7,
        "p95": 3.8499999999999996,
        "p99": 3.9699999999999998,
        "max": 4,
        "sum": 10,
    }


@pytest.mark.ml
def test_actual_tokenizer_statistics_use_only_messages(tmp_path, subset):
    pytest.importorskip("torch")
    from rsec.train import tiny_model

    _, tokenizer = tiny_model()
    path = tmp_path / "tokenizer"
    tokenizer.save_pretrained(path)
    rows = [Candidate.model_validate(r) for r in subset]
    report = statistics(rows, path)
    expected = [
        len(
            tokenizer.apply_chat_template(
                [m.model_dump() for m in r.messages], tokenize=True, return_dict=False
            )
        )
        for r in rows
    ]
    assert report["tokenizer_tokens"]["sum"] == sum(expected)
    assert report["tokens_per_epoch_eligible_sft"] == 0
    altered = rows[0].model_copy(deep=True)
    altered.evidence += " metadata only"
    altered.difficulty = "expert"
    assert statistics([altered], path)["tokenizer_tokens"]["sum"] == expected[0]
    tokenizer.chat_template = None
    tokenizer.save_pretrained(path)
    (path / "chat_template.jinja").unlink(missing_ok=True)
    with pytest.raises(RsecError, match="template"):
        statistics(rows, path)


def test_exported_cases_use_existing_prediction_contract(tmp_path, capsys):
    from rsec.cli import main
    from rsec.datasets.benchmark import export_cases

    output = tmp_path / "cases.jsonl"
    assert export_cases(output)["cases"] == 32
    cases = list(load_rows(output))
    assert all({"id", "prompt", "domain", "language", "expected"}.issubset(r) for r in cases)
    assert any(r["expected"]["cwe"] == ["CWE-79"] for r in cases)
    assert "Provided references:" in cases[0]["prompt"]
    assert main(["benchmark", "export", "--output", str(tmp_path / "cli-cases.jsonl")]) == 0


def test_human_rubric_scores_bound_to_content_and_no_fake_gold(tmp_path):
    from rsec.cli import main
    from rsec.datasets.benchmark import score_rubrics
    from rsec.datasets.schema import content_hash
    from rsec.utils import digest

    row = Candidate.model_validate(next(load_rows("benchmarks/rsec_cyberbench/development.jsonl")))
    rubric = read_json("benchmarks/rsec_cyberbench/rubrics.json")
    raw = {
        "record_id": row.id,
        "record_hash": content_hash(row),
        "rubric_hash": digest(rubric),
        "reviewer_id": "test-only-reviewer",
        "human_attested": True,
        "scores": {key: 2 for key in rubric["domains"][row.domain]},
    }
    ratings = tmp_path / "ratings.jsonl"
    jsonl(ratings, [raw])
    result = score_rubrics(ratings, tmp_path / "score.json")
    assert result["results"][0]["normalized_score"] == 1
    assert result["coverage"] == 1 / 32 and result["expert_gold_certified"] is False
    assert (
        main(
            [
                "benchmark",
                "rubric-score",
                "--ratings",
                str(ratings),
                "--output",
                str(tmp_path / "cli-score.json"),
            ]
        )
        == 0
    )
    for attack in [
        {"human_attested": False},
        {"rubric_hash": "0" * 64},
        {"record_hash": "0" * 64},
        {"scores": {}},
        {"scores": {k: True for k in raw["scores"]}},
        {"record_id": "foreign"},
    ]:
        ratings.unlink()
        jsonl(ratings, [{**raw, **attack}])
        with pytest.raises(RsecError):
            score_rubrics(ratings, tmp_path / "bad.json")
    ratings.unlink()
    jsonl(ratings, [raw, raw])
    with pytest.raises(RsecError, match="Duplicate"):
        score_rubrics(ratings, tmp_path / "bad.json")


@pytest.mark.ml
def test_phase2_sft_bridge_real_trl_targets(tmp_path, subset, decision_for):
    pytest.importorskip("torch")
    pytest.importorskip("trl")
    from trl import SFTConfig, SFTTrainer

    from rsec.config import load_training
    from rsec.datasets.release import curate
    from rsec.train import supervised_dataset, tiny_model

    path = tmp_path / "input.jsonl"
    jsonl(path, subset)
    decisions = tmp_path / "reviews.jsonl"
    jsonl(decisions, [decision_for(r) for r in subset])
    curate([path], tmp_path / "curated", "test-fixture-only", decisions_path=decisions)
    rows = list(load_rows(tmp_path / "curated/sft/train.jsonl"))
    model, tokenizer = tiny_model()
    config = load_training()
    data = supervised_dataset(rows, tokenizer, config)
    assert set(data.column_names) == {"prompt", "completion"}
    assert all(
        set(m) == {"role", "content"} for row in data for m in row["prompt"] + row["completion"]
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=data,
        args=SFTConfig(
            output_dir=str(tmp_path / "tiny"), use_cpu=True, report_to=[], completion_only_loss=True
        ),
    )
    batch = trainer.data_collator([trainer.train_dataset[0]])
    assert (batch["labels"] == -100).any() and (batch["labels"] != -100).any()
    assert model(**batch).loss.isfinite()
