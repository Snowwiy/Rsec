import copy

import pytest

from rsec.data import load_rows, validate_release
from rsec.datasets.linkage import (
    approximate_duplicates,
    code_fingerprint,
    contamination,
    related,
    shingles,
)
from rsec.datasets.release import (
    curate,
    read_reserved,
    split_rows,
    validate_bundle,
    validate_sft,
)
from rsec.datasets.review import Decision, apply_decisions
from rsec.datasets.schema import Candidate
from rsec.errors import RsecError
from rsec.utils import jsonl, read_json, sha256, write_json


def save(path, rows):
    jsonl(path, rows)
    return path


def test_translation_forward_reference_code_and_provenance(candidates):
    rows = [Candidate.model_validate(r) for r in candidates]
    groups, _ = related(rows)
    owners = {rows[i].id: g for g, indices in enumerate(groups) for i in indices}
    for i in range(0, len(rows), 2):
        assert owners[rows[i].id] == owners[rows[i + 1].id]
    original = rows[0].model_copy(deep=True)
    variant = original.model_copy(deep=True)
    variant.id = "renamed"
    variant.origin_id = "another"
    variant.families = ["other"]
    variant.translation_of = None
    variant.code = "# inert comment\n" + original.code.replace(" ", "  ")
    assert code_fingerprint(variant.code) == code_fingerprint(original.code)
    assert len(related([variant, original])[0]) == 1
    assert contamination([variant], [original])["contaminated_ids"] == ["renamed"]
    translated = rows[1].model_copy(deep=True)
    translated.families = ["unlinked"]
    translated.origin_id = "different"
    translated.code = None
    assert len(related([translated, rows[0]])[0]) == 1


def test_similarity_budget_and_near_duplicate_targets(candidate):
    a = Candidate.model_validate(candidate)
    b = a.model_copy(deep=True)
    b.id = "paraphrased"
    b.origin_id = "different"
    b.families = ["different"]
    b.code = None
    b.messages[1].content += " Carefully."
    assert approximate_duplicates([a, b]) == {"paraphrased"}
    b.messages[-1].content += " Different target."
    assert not approximate_duplicates([a, b])
    with pytest.raises(RsecError, match="budget"):
        related([a, b], max_pairs=0)
    b.messages[-1].content = a.messages[-1].content
    with pytest.raises(RsecError, match="budget"):
        approximate_duplicates([a, b], max_pairs=0)
    with pytest.raises(RsecError, match="budget"):
        shingles("word " * 12001)


def test_review_content_registry_and_human_guards(subset, registry, decision_for):
    row = Candidate.model_validate(subset[0])
    d = decision_for(row)
    assert apply_decisions([row], [d], registry.hash)[0].review.status == "EXPERT REVIEWED"
    changed = row.model_copy(deep=True)
    changed.evidence += " changed"
    with pytest.raises(RsecError, match="content hash"):
        apply_decisions([changed], [d], registry.hash)
    for change in ({"record_id": "unknown"}, {"registry_hash": "0" * 64}):
        with pytest.raises(RsecError, match="mismatch"):
            apply_decisions([row], [{**d, **change}], registry.hash)
    with pytest.raises(RsecError, match="Duplicate reviewer"):
        apply_decisions([row], [d, d], registry.hash)
    for change in (
        {"human_attested": False},
        {"reviewer_id": "person@example.invalid"},
        {"checks": []},
    ):
        with pytest.raises(ValueError):
            Decision.model_validate({**d, **change})
    expert = Candidate.model_validate({**subset[0], "difficulty": "expert"})
    assert (
        apply_decisions([expert], [decision_for(expert)], registry.hash)[0].review.status
        == "GENERATED"
    )
    assert (
        apply_decisions(
            [expert],
            [decision_for(expert), decision_for(expert, "second-test-reviewer")],
            registry.hash,
        )[0].review.status
        == "EXPERT REVIEWED"
    )
    assert (
        apply_decisions([row], [decision_for(row, action="reject")], registry.hash)[0].review.status
        == "REJECTED"
    )
    remediation = Candidate.model_validate({**subset[0], "task_type": "remediation"})
    d = decision_for(remediation)
    d["checks"].remove("remediation")
    with pytest.raises(RsecError, match="Remediation"):
        apply_decisions([remediation], [d], registry.hash)


def test_curate_pending_reproducible_and_no_self_expert(tmp_path, subset, registry):
    subset[0]["review"] = {
        "status": "EXPERT REVIEWED",
        "reviewer_id": "fabricated",
        "decision_hash": "0" * 64,
    }
    path = save(tmp_path / "input.jsonl", subset)
    a = tmp_path / "a"
    b = tmp_path / "b"
    result = curate([path], a, "pilot-test")
    curate([path], b, "pilot-test")
    assert result["approved_sft"] == 0 and result["pending_review"] == 8
    assert not (a / "sft").exists()
    for name in ["records.jsonl", "quality_report.json", "curation_manifest.json"]:
        assert sha256(a / name) == sha256(b / name)
    assert validate_bundle(a)["records"] == 8
    with pytest.raises(FileExistsError):
        curate([path], a, "same")
    with pytest.raises(RsecError):
        curate([path], tmp_path / "escape", "../escape")


def test_expert_bridge_reuses_actual_legacy_record_contract(tmp_path, subset, decision_for):
    path = save(tmp_path / "input.jsonl", subset)
    decisions = save(tmp_path / "decisions.jsonl", [decision_for(r) for r in subset])
    output = tmp_path / "release"
    report = curate([path], output, "test-approval-fixture", decisions_path=decisions)
    assert report["approved_sft"] == len(subset)
    assert validate_sft(output / "sft")["records"] == len(subset)
    assert validate_release(output / "sft")["records"] == len(subset)
    owners = {}
    for split in ["train", "eval", "test"]:
        rows = list(load_rows(output / "sft" / f"{split}.jsonl"))
        assert rows
        for r in rows:
            assert "review" not in r and "taxonomy_version" not in r
            assert r["reviewed"] is True
            assert r["group"] not in owners or owners[r["group"]] == split
            owners[r["group"]] = split


@pytest.mark.parametrize(
    "attack",
    ["changed_bytes", "extra_file", "path_traversal", "symlink", "policy_hash", "unknown_version"],
)
def test_bundle_tampering_rejected(tmp_path, subset, attack):
    source = save(tmp_path / "input.jsonl", subset)
    root = tmp_path / "release"
    curate([source], root, "test")
    if attack == "changed_bytes":
        (root / "records.jsonl").write_text("{}\n")
    elif attack == "extra_file":
        (root / "unexpected.txt").write_text("inert")
    elif attack == "symlink":
        (root / "unexpected").symlink_to(tmp_path / "input.jsonl")
    else:
        m = read_json(root / "curation_manifest.json")
        if attack == "path_traversal":
            m["files"]["../input.jsonl"] = sha256(source)
        elif attack == "policy_hash":
            m["registry_hash"] = "0" * 64
        else:
            m["version"] = 999
        write_json(root / "curation_manifest.json", m, overwrite=True)
    with pytest.raises((RsecError, OSError)):
        validate_bundle(root)


@pytest.mark.parametrize(
    "attack",
    [
        "missing_expert",
        "bridge_message",
        "group_leakage",
        "empty_split",
        "missing_example",
        "unknown_record",
        "unsafe_content",
        "reserved",
    ],
)
def test_sft_cannot_bypass_quality_or_split_gates(tmp_path, subset, decision_for, attack):
    source = save(tmp_path / "input.jsonl", subset)
    decisions = save(tmp_path / "decisions.jsonl", [decision_for(r) for r in subset])
    root = tmp_path / "release"
    curate([source], root, "test", decisions_path=decisions)
    sft = root / "sft"
    manifest = read_json(sft / "dataset_manifest.json")
    if attack == "missing_expert":
        (sft / "reviews.jsonl").write_text("")
    elif attack == "reserved":
        (sft / "reserved.jsonl").write_text((sft / "curation_records.jsonl").read_text())
    elif attack == "unsafe_content":
        rows = list(load_rows(sft / "curation_records.jsonl"))
        rows[0]["source_id"] = "unregistered"
        (sft / "curation_records.jsonl").unlink()
        jsonl(sft / "curation_records.jsonl", rows)
    else:
        train = list(load_rows(sft / "train.jsonl"))
        evals = list(load_rows(sft / "eval.jsonl"))
        if attack == "bridge_message":
            train[0]["messages"][-1]["content"] = "Changed answer with no corresponding review."
        elif attack == "group_leakage":
            train[0]["group"] = evals[0]["group"]
        elif attack == "empty_split":
            train = []
        elif attack == "missing_example":
            train = train[1:]
        elif attack == "unknown_record":
            train[0]["id"] = "foreign-id"
        (sft / "train.jsonl").unlink()
        jsonl(sft / "train.jsonl", train)
    # Recalculate file hashes to exercise semantic checks, not just corruption detection.
    for name in manifest["files"]:
        manifest["files"][name] = sha256(sft / name)
    write_json(sft / "dataset_manifest.json", manifest, overwrite=True)
    with pytest.raises((RsecError, ValueError)):
        validate_sft(sft)


def test_quarantine_hashes_only_duplicates_unknown_inputs_and_reserved(tmp_path, candidate, subset):
    bad = copy.deepcopy(candidate)
    bad["id"] = "pii-example"
    bad["messages"][-1]["content"] = "Contact analyst@example.invalid before proceeding."
    altered = copy.deepcopy(subset[1])
    altered["id"] = "heldout-altered-answer"
    altered["messages"][-1]["content"] = "Another answer must not remove contamination."
    path = save(tmp_path / "input.jsonl", [*subset, bad, subset[0], None, altered])
    held = save(tmp_path / "held.jsonl", [subset[1]])
    result = curate([path], tmp_path / "out", "test", reserved_paths=[held])
    assert result["quarantined"] >= 3 and result["rejected"] == 1
    text = (tmp_path / "out/quarantine.jsonl").read_text()
    assert "analyst@example.invalid" not in text
    assert result["contamination"]["contaminated_ids"]
    with pytest.raises(RsecError, match="three"):
        split_rows([Candidate.model_validate(candidate)])
    assert len(read_reserved(["benchmarks/suite.jsonl"])) == 10
    malformed = save(tmp_path / "badbench.jsonl", [{"untrusted": "not a benchmark"}])
    with pytest.raises(RsecError, match="schema"):
        read_reserved([malformed])


def test_partial_human_review_does_not_destroy_a_pending_bundle(tmp_path, subset, decision_for):
    source = save(tmp_path / "input.jsonl", subset)
    decisions = save(tmp_path / "one-review.jsonl", [decision_for(subset[0])])
    result = curate(
        [source], tmp_path / "pending", "partial-review-fixture", decisions_path=decisions
    )
    assert result["approved_sft"] == 1 and result["pending_review"] == 7
    assert result["sft_release"].startswith("BLOCKED: fewer")
    assert validate_bundle(tmp_path / "pending")["records"] == 8
    assert not (tmp_path / "pending/sft").exists()


def test_nested_manifest_is_not_exempt_from_inventory(tmp_path, subset):
    source = save(tmp_path / "input.jsonl", subset)
    root = tmp_path / "release"
    curate([source], root, "test")
    (root / "unexpected").mkdir()
    write_json(root / "unexpected/curation_manifest.json", {"unexpected": True})
    with pytest.raises(RsecError, match="inventory"):
        validate_bundle(root)


def test_two_long_opaque_reviewer_ids_remain_valid(subset, registry, decision_for):
    row = Candidate.model_validate({**subset[0], "difficulty": "expert"})
    apply_decisions(
        [row], [decision_for(row, "a" * 100), decision_for(row, "b" * 100)], registry.hash
    )
    assert Candidate.model_validate(row.model_dump()).review.status == "EXPERT REVIEWED"
