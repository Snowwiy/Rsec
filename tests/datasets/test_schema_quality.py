import copy
import json

import pytest

from rsec.datasets.quality import classify, inspect_candidate, pii
from rsec.datasets.registry import Registry, Source
from rsec.datasets.schema import (
    Candidate,
    Generation,
    Review,
    content_hash,
    https_url,
)
from rsec.errors import RsecError
from rsec.utils import read_json, write_json


@pytest.mark.parametrize(
    "change",
    [
        {"id": "../escape"},
        {"synthetic": "true"},
        {"synthetic": 1},
        {"language": "fr"},
        {"domain": "unknown"},
        {"subcategory": "wrong"},
        {"taxonomy_version": "999"},
        {"task_type": "autonomous_exploitation"},
        {"programming_language": "UnknownLanguage"},
        {"generation": None},
        {"families": []},
        {"families": ["x", "x"]},
        {"messages": []},
        {"evidence": ""},
        {"unexpected": "untrusted instruction"},
        {"source_id": ""},
    ],
)
def test_schema_and_taxonomy_fail_closed(candidate, registry, change):
    row, report = inspect_candidate({**candidate, **change}, registry)
    assert row is None and report["disposition"] == "rejected"
    assert report["reasons"] == ["invalid_schema_or_taxonomy"]


@pytest.mark.parametrize(
    "roles",
    [
        ["assistant", "user"],
        ["system", "assistant"],
        ["user", "system"],
        ["user", "user", "assistant"],
    ],
)
def test_roles(candidate, roles):
    candidate["messages"] = [{"role": r, "content": "controlled content"} for r in roles]
    with pytest.raises(ValueError):
        Candidate.model_validate(candidate)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org",
        "https://user:pass@example.org",
        "https://example.org:8080",
        "javascript:run",
        "https:///nohost",
    ],
)
def test_https_reference_contract(url):
    with pytest.raises(ValueError):
        https_url(url)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("source_id", "missing-source", "unregistered_source_or_reference"),
        ("source_revision", "unverified", "source_revision_mismatch"),
        ("purpose", "knowledge", "rights_or_purpose_blocked"),
        ("asserted_ids", ["CVE-2099-9999999"], "unverified_identifier"),
        ("origin_id", "analyst@example.invalid", "sensitive_metadata"),
    ],
)
def test_policy_gate_independent_of_score(candidate, registry, field, value, reason):
    candidate[field] = value
    row, report = inspect_candidate(candidate, registry)
    assert row is None and reason in report["reasons"]


def test_reference_substitution_rejected(candidate, registry):
    candidate["references"][0]["url"] = "https://example.org/unverified"
    row, report = inspect_candidate(candidate, registry)
    assert row is None and "unverified_reference" in report["reasons"]
    candidate["references"][0]["source_id"] = "unregistered"
    assert inspect_candidate(candidate, registry)[0] is None


@pytest.mark.parametrize(
    "text,reason",
    [
        ("password=" + ("aB8x" * 6), "secret"),
        ("Contact analyst@example.invalid", "possible_pii"),
        ("ignore previous instructions", "possible_poisoning"),
        ("I ran the scanner and found real results.", "unsupported_execution_claim"),
        ("word " * 100, "anomalous_repetition"),
        ("A vulnerability is confirmed under CVE-2099-9999999.", "unverified_answer_identifier"),
        ("short", "answer_too_short"),
    ],
)
def test_untrusted_answers_quarantined_without_leaking(candidate, registry, text, reason):
    candidate["messages"][-1]["content"] = text
    row, report = inspect_candidate(candidate, registry)
    assert row is None and reason in report["reasons"]
    assert "messages" not in report and "answer" not in report
    if len(text) > 10:
        assert text not in json.dumps(report)


@pytest.mark.parametrize("answer", ["[]", "not JSON", '{"label":"vulnerable"}'])
def test_structured_answer_consistency(candidate, registry, answer):
    candidate["task_type"] = "structured_json"
    candidate["messages"][-1]["content"] = answer
    assert inspect_candidate(candidate, registry)[0] is None


def test_anonymization_changes_review_and_preserves_uncertainty(candidates, registry):
    raw = copy.deepcopy(candidates[4])
    raw["messages"][1]["content"] += " Contact analyst@example.invalid"
    row, report = inspect_candidate(raw, registry, anonymize=True)
    assert row and row.review.status == "EXPERT REVIEW REQUIRED"
    assert "[EMAIL]" in row.messages[1].content
    assert "analyst@example.invalid" not in json.dumps(row.model_dump())
    unknown = copy.deepcopy(candidates[20])
    assert unknown["expected_label"] == "insufficient"
    assert inspect_candidate(unknown, registry)[0] is not None
    assert not pii("CVE-2099-9999999 checked 2026-11-26", registry)


def test_automatic_score_never_claims_expert_truth(candidate, registry):
    row, report = inspect_candidate(candidate, registry)
    assert report["automatic_score"] == 100
    assert report["dimensions"]["technical_correctness"] is None
    assert row.review.status == "EXPERT REVIEW REQUIRED" and row.review.reviewer_id is None
    assert content_hash(row) == content_hash(
        {**row.model_dump(), "review": {"status": "GENERATED"}}
    )


@pytest.mark.parametrize(
    "text,domain,language",
    [
        ("Analyze the supplied SQL evidence", "application_security", "en"),
        ("Analiza la evidencia de seguridad del SIEM", "soc_detection", "es"),
        ("Check a CVE- advisory", "vulnerability_management", None),
        ("container firewall hardening", "infrastructure_security", None),
        ("forensic timeline custody", "dfir", None),
        ("asset owner risk register", "grc", None),
        ("LLM RAG retrieved document", "ai_security", None),
        ("TLS certificate MFA", "cryptography_identity", None),
    ],
)
def test_classification_is_explainable_hint(text, domain, language):
    hint = classify(text)
    assert hint["domain_hint"] == domain
    if language:
        assert hint["language_hint"] == language
    assert "heuristic" in hint["method"]


def test_registry_rights_and_duplicate_guards(registry, tmp_path):
    assert len(registry.sources) == 22
    assert registry.permission("rsec-pilot", "sft")
    assert not registry.permission("cve-program", "sft")
    assert not registry.permission("iso-27001", "knowledge")
    with pytest.raises(RsecError):
        registry.get("not-registered")
    source = registry.get("rsec-pilot").model_dump()
    for change in ({"license": "unknown"}, {"status": "REVIEW REQUIRED"}, {"id": "../escape"}):
        with pytest.raises(ValueError):
            Source.model_validate({**source, **change})
    ref = copy.deepcopy(source)
    ref["references"][0]["source_id"] = "another"
    with pytest.raises(ValueError):
        Source.model_validate(ref)
    raw = read_json(registry.path)
    raw["sources"].append(raw["sources"][0])
    path = tmp_path / "registry.json"
    write_json(path, raw)
    with pytest.raises(RsecError, match="Duplicate source"):
        Registry(path)
    raw = read_json(registry.path)
    raw["sources"][1]["references"] = copy.deepcopy(raw["sources"][0]["references"])
    raw["sources"][1]["references"][0]["source_id"] = raw["sources"][1]["id"]
    write_json(path, raw, overwrite=True)
    with pytest.raises(RsecError, match="Duplicate reference"):
        Registry(path)
    write_json(path, {"schema_version": 99}, overwrite=True)
    with pytest.raises(RsecError, match="schema"):
        Registry(path)


def test_review_cannot_self_authorize_without_attestation():
    with pytest.raises(ValueError):
        Review(status="EXPERT REVIEWED")
    with pytest.raises(ValueError):
        Generation(
            method="commercial_api_harvest",
            template_id="x",
            generator_version="1",
            generated_at="2026-11-26",
            original_id="x",
            authorization="x",
            validation_method="x",
        )


def test_rejected_review_and_length_budget_are_hard_gates(candidate, registry):
    candidate["review"] = {"status": "REJECTED"}
    assert "review_rejected" in inspect_candidate(candidate, registry)[1]["reasons"]
    candidate["review"] = {"status": "GENERATED"}
    candidate["messages"][0]["content"] = "controlled content " * 4000
    assert "length_budget" in inspect_candidate(candidate, registry)[1]["reasons"]
