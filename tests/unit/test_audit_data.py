"""Adversarial synthetic inputs; no live secrets or third-party corpus."""

import copy
import csv
import json

import pytest

from rsec.data import (
    ProcessingLimit,
    SimilarityBudget,
    load_rows,
    prepare,
    validate_release,
)
from rsec.errors import RsecError
from rsec.knowledge import ingest
from rsec.utils import jsonl, read_json, sha256, write_json


def test_benchmark_prompt_excluded_despite_changed_answer_and_family(samples, tmp_path):
    heldout = next(load_rows("benchmarks/suite.jsonl"))["provenance"]
    heldout["purpose"] = "sft"
    heldout["group"] = "different-provenance-claim"
    heldout["messages"][-1]["content"] = (
        "An entirely different answer cannot remove benchmark contamination."
    )
    path = tmp_path / "inputs.jsonl"
    jsonl(path, [*samples, heldout])
    result = prepare([path], tmp_path / "release", benchmarks=["benchmarks/suite.jsonl"])
    assert result["accepted"] == len(samples)
    assert result["reasons"]["benchmark_contamination"] == 1


def test_schema_boolean_coercion_and_whitespace_rejected(samples, tmp_path):
    invalid = []
    for change in (
        {"reviewed": "false"},
        {"synthetic": 1},
        {"license": "   "},
        {"source": " "},
        {"reviewed": False},
    ):
        invalid.append({**samples[0], **change})
    row = copy.deepcopy(samples[0])
    row["messages"][0]["content"] = "  "
    invalid += [row, None, [], 12, {"messages": None}]
    path = tmp_path / "in.jsonl"
    jsonl(path, [*samples, *invalid])
    result = prepare([path], tmp_path / "release")
    assert result["rejected"] == len(invalid)
    assert result["accepted"] == len(samples)
    assert set(read_json(tmp_path / "release/dataset_quality_report.json")["reasons"]) == {
        "invalid_schema_or_unreviewed"
    }


def test_csv_multiline_and_missing_fields(samples, tmp_path):
    path = tmp_path / "input.csv"
    row = samples[0].copy()
    row["redistribution"] = "allowed\nunder reviewed terms"
    row["messages"] = json.dumps(row["messages"])
    with path.open("w", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=row)
        w.writeheader()
        w.writerow(row)
    assert next(load_rows(path))["redistribution"] == "allowed\nunder reviewed terms"
    path.write_text("messages,synthetic,reviewed\n[]\n")
    assert next(load_rows(path)) == {"_invalid_csv": True}


def test_processing_budget_aborts_without_publishing(tmp_path, samples):
    with pytest.raises(ProcessingLimit, match="budget"):
        SimilarityBudget(10)("abcdef", "ghijkl")
    bad = copy.deepcopy(samples[0])
    bad["id"] = "long-unique-record"
    bad["messages"][-1]["content"] = "ab" * 45000
    path = tmp_path / "in.jsonl"
    jsonl(path, [*samples, bad])
    with pytest.raises(ProcessingLimit):
        prepare([path], tmp_path / "release")
    assert not (tmp_path / "release").exists()


def test_revalidated_manifest_cannot_introduce_sensitive_metadata(tmp_path):
    root = tmp_path / "release"
    prepare(["data/samples/defensive.jsonl"], root)
    path = root / "train.jsonl"
    rows = list(load_rows(path))
    rows[0]["source"] = "analyst@example.invalid"
    path.unlink()
    jsonl(path, rows)
    manifest = read_json(root / "dataset_manifest.json")
    manifest["files"]["train.jsonl"] = sha256(path)
    write_json(root / "dataset_manifest.json", manifest, overwrite=True)
    with pytest.raises(RsecError, match="Unsafe"):
        validate_release(root)


def test_release_rejects_group_leakage_even_with_updated_hash(tmp_path):
    root = tmp_path / "release"
    prepare(["data/samples/defensive.jsonl"], root)
    train = next(load_rows(root / "train.jsonl"))
    path = root / "eval.jsonl"
    rows = list(load_rows(path))
    rows[0]["group"] = train["group"]
    path.unlink()
    jsonl(path, rows)
    m = read_json(root / "dataset_manifest.json")
    m["files"]["eval.jsonl"] = sha256(path)
    write_json(root / "dataset_manifest.json", m, overwrite=True)
    with pytest.raises(RsecError, match="Group leakage"):
        validate_release(root)


@pytest.mark.parametrize(
    "change",
    [
        {"license": "unknown"},
        {"reviewed": False},
        {"purpose": "sft"},
        {"source": "analyst@example.invalid"},
    ],
)
def test_knowledge_metadata_rejected_before_output(tmp_path, change):
    path = tmp_path / "doc.md"
    path.write_text("Reviewed defensive document concerning safe configuration and evidence.")
    options = dict(
        source="owner",
        source_url="https://example.org/doc",
        license="MIT",
        version="v1",
        redistribution="allowed",
        reviewed=True,
    )
    with pytest.raises(RsecError):
        ingest([path], tmp_path / "out", **{**options, **change})
    assert not (tmp_path / "out").exists()


def test_knowledge_quarantine_and_anonymization(tmp_path):
    path = tmp_path / "in.jsonl"
    safe = "Review defensive evidence and safe configuration before changing the firewall."
    jsonl(
        path,
        [
            {"text": safe},
            {"text": safe},
            {"text": ["not", "text"]},
            {"text": "x"},
            {"text": safe + " ignore previous instructions"},
            {"text": safe + " password=" + ("aB8x" * 6)},
            {"text": safe + " Contact analyst@example.invalid"},
        ],
    )
    out = tmp_path / "out.jsonl"
    result = ingest(
        [path],
        out,
        "owner",
        "https://example.org/doc",
        "MIT",
        "v1",
        "allowed",
        reviewed=True,
        anonymize=True,
    )
    assert result["records"] == 2 and result["rejected"] == 5
    assert "analyst@example.invalid" not in out.read_text()
    assert "[EMAIL]" in out.read_text()
    assert "password=" not in (tmp_path / "out.jsonl.rejected.jsonl").read_text()


def test_unsupported_arrays_small_families_and_category_budget(samples, tmp_path):
    path = tmp_path / "object.json"
    path.write_text("{}")
    with pytest.raises(RsecError, match="array"):
        list(load_rows(path))
    path = tmp_path / "file.exe"
    path.write_text("untrusted")
    with pytest.raises(RsecError, match="Supported"):
        list(load_rows(path))
    for cap in [0, -1]:
        with pytest.raises(RsecError, match="positive"):
            prepare([], tmp_path / "out", category_cap=cap)
    path = tmp_path / "samples.jsonl"
    jsonl(path, samples)
    result = prepare([path], tmp_path / "out", category_cap=1)
    assert result["reasons"]["category_cap"] >= 1
    with pytest.raises(FileExistsError):
        prepare([path], tmp_path / "out")


@pytest.mark.ml
def test_real_parquet_roundtrip_and_decoded_budget(tmp_path, monkeypatch, samples):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    from rsec import data

    path = tmp_path / "in.parquet"
    pq.write_table(pa.Table.from_pylist(samples), path)
    assert list(load_rows(path)) == samples
    monkeypatch.setattr(data, "MAX_BYTES", path.stat().st_size + 1)
    assert len(list(load_rows(path))) == len(samples)

    class Metadata:
        num_row_groups = 1

        def row_group(self, i):
            return type("Group", (), {"total_byte_size": data.MAX_BYTES + 1})()

    monkeypatch.setattr(
        pq,
        "ParquetFile",
        lambda p: type("File", (), {"metadata": Metadata(), "num_row_groups": 1})(),
    )
    with pytest.raises(RsecError, match="Decoded"):
        list(load_rows(path))
