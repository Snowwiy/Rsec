import http.client
import re
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from rsec import gpu
from rsec.cli import main
from rsec.data import load_rows
from rsec.datasets.evidence import Prediction, score_codebench, score_ratings
from rsec.datasets.preaudit import preaudit
from rsec.datasets.release import curate, validate_bundle
from rsec.datasets.review_security import Event, Reviewers, sign, verify
from rsec.datasets.schema import Candidate
from rsec.datasets.semantic import semantic_review
from rsec.datasets.software import CODEBENCH, pass_at_k
from rsec.errors import RsecError
from rsec.utils import digest, jsonl, read_json, sha256, write_json

HASH = "3" * 64


def test_preaudit_covers_real_inputs(tmp_path):
    report = tmp_path / "audit.jsonl"
    assert (
        preaudit(
            ["data/pilot/candidates.jsonl", "benchmarks/rsec_cyberbench/development.jsonl"], report
        )["records"]
        == 96
    )
    rows = {row["id"]: row for row in load_rows(report)}
    assert all(not row["approval"] for row in rows.values())
    assert "sumidero" in rows["pilot-001-en"]["findings"][0]
    assert "genérica" in rows["bench-002-en"]["findings"][-1]


def test_benchmark_validation_and_pass_at_k():
    assert main(["benchmark", "code-validate"]) == 0
    assert pass_at_k(5, 2, 2) == pytest.approx(0.7)
    assert pass_at_k(5, 0, 5) == 0
    assert pass_at_k(2, 1, 2) == 1
    with pytest.raises(RsecError, match=r"pass@k"):
        pass_at_k(2, 1, 3)


def prediction(case, model, sample, suite, **changes):
    response = "  exact test answer\n"
    return Prediction.model_validate(
        {
            "case_id": case["id"],
            "case_sha256": digest(case),
            "model_id": model,
            "model_revision": "revision-fixture",
            "adapter_sha256": None,
            "artifact_sha256": digest(model),
            "sample": sample,
            "response": response,
            "response_sha256": digest(response),
            "conditions": {
                "base_model": "base-fixture",
                "base_revision": "base-version",
                "tokenizer_sha256": HASH,
                "template_sha256": HASH,
                "suite_sha256": sha256(suite),
                "system_prompt": "Fixture",
                "inference": {"temperature": 0.2},
                "seed": 3,
            },
            **changes,
        }
    )


@pytest.mark.parametrize(
    "fault",
    [None, "missing", "changed_response", "different_conditions", "duplicate", "missing_assertion"],
)
def test_code_eval_checks_comparability_and_unit_evidence(tmp_path, fault):
    case = next(load_rows(CODEBENCH))
    suite = tmp_path / "suite.jsonl"
    jsonl(suite, [case])
    predictions = [
        prediction(case, model, i, suite) for model in ("base", "mixed") for i in range(2)
    ]
    evidence = [
        {
            "prediction_sha256": p.fingerprint(),
            "harness_sha256": HASH,
            "results": dict.fromkeys(case["unit_checks"], p.sample == 0 or p.model_id == "mixed"),
        }
        for p in predictions
    ]
    rows = [p.model_dump() for p in predictions]
    if fault == "missing":
        evidence.pop()
    if fault == "changed_response":
        rows[0]["response"] = "substituted"
        rows[0]["response_sha256"] = digest("substituted")
    if fault == "different_conditions":
        rows[0]["conditions"]["seed"] = 11
    if fault == "duplicate":
        rows.append(rows[0])
    if fault == "missing_assertion":
        evidence[0]["results"].pop(case["unit_checks"][0])
    pred, unit, out = (tmp_path / name for name in ("pred.jsonl", "unit.jsonl", "out.json"))
    jsonl(pred, rows)
    jsonl(unit, evidence)
    if fault:
        with pytest.raises(RsecError):
            score_codebench(suite, [pred], unit, HASH, [1, 2, 3], out)
    else:
        report = score_codebench(suite, [pred], unit, HASH, [1, 2, 3], out)
        assert predictions[0].response.startswith("  ")
        assert report["results"]["base"]["pass_at_k"] == {"1": 0.5, "2": 1.0, "3": None}
        assert report["results"]["mixed"]["unit_assertion_rate"] == 1


@pytest.mark.parametrize("changed", ["prediction", "rubric", "method", None])
def test_response_ratings_are_bound_and_methods_separate(tmp_path, changed):
    case = next(load_rows(CODEBENCH))
    p = prediction(case, "base", 0, CODEBENCH)
    rubric = {"version": "v1", "weights": {"quality": 2}}
    row = {
        "prediction_sha256": p.fingerprint(),
        "rubric_sha256": digest(rubric),
        "evaluator": "test-only-fixture",
        "method": "human",
        "status": "reviewed",
        "scores": {"quality": 1},
        "evidence": "Synthetic scorer test",
        "date": "2026-11-26",
    }
    if changed in {"prediction", "rubric"}:
        row[changed + "_sha256"] = HASH
    elif changed == "method":
        row["method"] = "ai_assisted"
    path = tmp_path / "ratings.jsonl"
    jsonl(path, [row])
    if changed:
        with pytest.raises(ValueError):
            score_ratings({p.fingerprint(): p}, path, rubric, {p.case_id: rubric["weights"]})
    else:
        scored = score_ratings({p.fingerprint(): p}, path, rubric, {p.case_id: rubric["weights"]})
        assert scored[0]["method"] == "human" and scored[0]["mean"] == 0.5


def test_semantic_flags_candidates_without_promoting(tmp_path):
    from rsec.datasets.linkage import prompt_text
    from rsec.datasets.software import CodeCase

    input_path, reserve, vectors, report = (
        tmp_path / n for n in ("candidates.jsonl", "reserved.jsonl", "vectors.json", "report.json")
    )
    row = next(load_rows("data/pilot/candidates.jsonl"))
    held = next(load_rows(CODEBENCH))
    jsonl(input_path, [row])
    jsonl(reserve, [held])
    keys = [
        digest(prompt_text(r))
        for r in (Candidate.model_validate(row), CodeCase.model_validate(held).reservation())
    ]
    write_json(
        vectors,
        {
            "model": "mock-embedder",
            "revision": "test-only",
            "dimension": 2,
            "vectors": {k: [0.5, 0.4] for k in keys},
        },
    )
    result = semantic_review([input_path], [reserve], vectors, 0.95, report)
    assert result["possible_links"][0]["candidate_id"] == row["id"]
    assert result["status"] == "HUMAN REVIEW REQUIRED"


def test_reject_and_pending_reviews_do_not_break_bundle(tmp_path, subset, decision_for):
    rows = subset
    source, decisions, out = (
        tmp_path / "input.jsonl",
        tmp_path / "decisions.jsonl",
        tmp_path / "out",
    )
    jsonl(source, rows)
    rejected = Candidate.model_validate(rows[0])
    jsonl(decisions, [decision_for(rejected, action="reject")])
    result = curate([source], out, "rejection-check", decisions_path=decisions)
    assert result["quarantined"] == 1
    assert validate_bundle(out)["records"] == 7


@pytest.fixture
def local_reviewer(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("OpenSSL is absent")
    private = tmp_path / "fixture-private.pem"
    public = tmp_path / "fixture-public.pem"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private)], check=True
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True
    )
    path = tmp_path / "reviewers.json"
    config = {
        "id": "unit-test-authority",
        "display_name": "Disposable test authority",
        "domains": ["application_security"],
        "active": True,
        "added_on": "2026-01-01",
        "public_key": public.name,
        "key_sha256": sha256(public),
        "permissions": ["review"],
    }
    write_json(path, {"reviewers": [config]})
    return path, private


def test_ed25519_signatures_reject_tampering_and_fixture_flag(local_reviewer):
    path, key = local_reviewer
    reviewers = Reviewers(path)
    event = Event.model_validate(
        {
            "decision": {
                "record_id": "candidate",
                "record_hash": HASH,
                "registry_hash": HASH,
                "reviewer_id": "unit-test-authority",
                "decision": "reject",
                "human_attested": True,
                "checks": [],
                "reviewed_at": "2026-11-26",
            },
            "revision_sha256": HASH,
            "domain": "application_security",
            "action": "request_changes",
            "comments": "Synthetic approval-path exercise only",
            "proposed_answer": "revision",
        }
    )
    signed = sign(event, reviewers, key)
    assert verify(signed, reviewers).event.comments == event.comments
    signed.event.comments = "changed"
    with pytest.raises(RsecError, match="Ed25519"):
        verify(signed, reviewers)
    value = read_json(path)
    value["reviewers"][0]["fixture"] = True
    write_json(path, value, overwrite=True)
    with pytest.raises(RsecError, match="authorized"):
        verify(signed, Reviewers(path))


def test_local_ui_review_can_be_exported(tmp_path, local_reviewer):
    registry_path, private = local_reviewer
    row = next(load_rows("data/pilot/candidates.jsonl"))
    path, bundle, ledger = tmp_path / "input.jsonl", tmp_path / "bundle", tmp_path / "ledger"
    jsonl(path, [row])
    curate([path], bundle, "ui-fixture")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cmd = [
        sys.executable,
        "-m",
        "rsec.cli",
        "data",
        "review-ui",
        str(bundle),
        "--ledger",
        str(ledger),
        "--port",
        str(port),
        "--reviewers",
        str(registry_path),
        "--reviewer",
        "unit-test-authority",
        "--private-key",
        str(private),
    ]
    with subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE) as server:
        try:
            assert "Rsec review UI" in server.stdout.readline()
            con = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            con.request("GET", "/?id=" + row["id"])
            response = con.getresponse()
            body = response.read().decode()
            assert response.status == 200 and "frame-ancestors" in response.getheader(
                "Content-Security-Policy"
            )
            token = re.search(r'name="csrf" value="([^"]+)"', body).group(1)
            form = urlencode(
                {"csrf": token, "id": row["id"], "action": "request_changes", "human": "yes"}
            )
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "http://outside.invalid",
            }
            con.request("POST", "/decision", form, headers)
            denied = con.getresponse()
            denied.read()
            assert denied.status == 403 and not ledger.exists()
            headers["Origin"] = f"http://127.0.0.1:{port}"
            con.request("POST", "/decision", form, headers)
            saved = con.getresponse()
            saved.read()
            assert saved.status == 303
            con.close()
        finally:
            server.terminate()
    output = tmp_path / "decisions.jsonl"
    assert (
        main(
            [
                "data",
                "review-export",
                str(bundle),
                "--reviewers",
                str(registry_path),
                "--ledger",
                str(ledger),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert len(list(ledger.glob("*.json"))) == 1
    assert list(load_rows(output)) == []


def test_gpu_telemetry_keeps_fields_and_no_cpu_fallback(monkeypatch):
    import sys

    fake = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(
        gpu,
        "command",
        lambda _: "0, GPU-example, RTX, pci, 999, 12288, 78, 9, N/A, 6, 2, 4, 8, 8.9",
    )
    item = gpu.nvidia_devices()[0]
    assert item["uuid"] == "GPU-example" and item["temperature_c"] is None
    with pytest.raises(RsecError, match="CPU fallback is disabled"):
        gpu.require_cuda(0)


def test_mixed_replay_preserves_eval_and_revalidates_materialized_split(
    tmp_path, subset, decision_for
):
    from rsec.data import validate_release
    from rsec.datasets.registry import Registry
    from rsec.datasets.release import export_sft, manifest
    from rsec.datasets.schema import content_hash
    from rsec.datasets.software import SOFTWARE_TAXONOMY, make_replay_plan, materialize_replay

    cyber, software, mixed = (tmp_path / name for name in ("cyber", "software", "mixed"))
    rows = [Candidate.model_validate(r) for r in subset]
    export_sft(
        rows,
        cyber,
        Registry(),
        [decision_for(r) for r in rows],
        read_json("configs/taxonomy.json"),
        42,
        [],
    )
    catalog = Registry("data/manifests/software_source_registry.json")
    src = catalog.get("sqlite-completeness")
    notes = [
        "Explain stable ordering for a fictional record sequence.",
        "Describe a recurrence for a made-up billing schedule.",
        "Compare memory use for two fictional buffer formats.",
        "Design a timeout boundary for a toy batch processor.",
    ]
    examples, decisions = [], []
    for i, text in enumerate(notes):
        row = rows[i].model_copy(deep=True)
        row.id = row.origin_id = f"software-test-{i}"
        row.families = [row.id]
        row.code = None
        row.taxonomy_version = "software-1.0.0"
        row.domain, row.subcategory, row.task_type = (
            "software_engineering",
            "architecture",
            "design",
        )
        row.source_id, row.source_revision, row.references = src.id, src.version, src.references
        row.expected_label = None
        row.expected_cwe = row.asserted_ids = []
        row.messages[1].content = text
        row.messages[-1].content = "This text exists only to exercise fixture eligibility."
        examples.append(row)
        decisions.append(
            {
                **decision_for(row),
                "record_hash": content_hash(row),
                "registry_hash": catalog.hash,
            }
        )
    export_sft(examples, software, catalog, decisions, read_json(SOFTWARE_TAXONOMY), 42, [])
    preview = make_replay_plan(cyber, software, tmp_path / "preview.json", 4, 0.5, 42)
    assert preview["selected_examples"] == {"software": 2, "cyber": 2}
    materialize_replay(cyber, software, mixed, 4, 0.5, 42)
    for split in ("eval", "test"):
        assert list(load_rows(mixed / (split + ".jsonl"))) == [
            *load_rows(cyber / (split + ".jsonl")),
            *load_rows(software / (split + ".jsonl")),
        ]
    assert validate_release(mixed)["records"] == 8
    p = mixed / "train.jsonl"
    vals = list(load_rows(p))
    p.unlink()
    jsonl(p, list(reversed(vals)))
    manifest(mixed, "new.json", {"version": 3, "kind": "reviewed-mixed-replay"})
    recreated = read_json(mixed / "new.json")
    recreated["files"].pop("dataset_manifest.json")
    (mixed / "new.json").unlink()
    write_json(mixed / "dataset_manifest.json", recreated, overwrite=True)
    with pytest.raises(RsecError, match="frozen plan"):
        validate_release(mixed)


def test_private_gold_rejects_same_author_and_accepts_independent_fixture(
    tmp_path, local_reviewer, monkeypatch
):
    from rsec.datasets.gold import import_gold
    from rsec.datasets.registry import Registry
    from rsec.datasets.schema import content_hash

    registry_path, private = local_reviewer
    people = read_json(registry_path)
    people["reviewers"][0]["permissions"].append("adjudicate")
    extra_key = tmp_path / "unused-author-public.pem"
    subprocess.run(
        [
            "openssl",
            "genpkey",
            "-algorithm",
            "Ed25519",
            "-out",
            str(tmp_path / "unused-author-private.pem"),
        ],
        check=True,
    )
    subprocess.run(
        [
            "openssl",
            "pkey",
            "-in",
            str(tmp_path / "unused-author-private.pem"),
            "-pubout",
            "-out",
            str(extra_key),
        ],
        check=True,
    )
    people["reviewers"].append(
        {
            **people["reviewers"][0],
            "id": "different-test-author",
            "public_key": extra_key.name,
            "key_sha256": sha256(extra_key),
            "permissions": ["review"],
        }
    )
    write_json(registry_path, people, overwrite=True)

    policy = tmp_path / "sources.json"
    source = read_json("data/manifests/source_registry.json")["sources"][1]
    source["id"] = "evaluator-test-source"
    for ref in source["references"]:
        ref["source_id"] = source["id"]
    write_json(policy, {"schema_version": 1, "sources": [source]})
    catalog = Registry(policy)
    row = Candidate.model_validate(next(load_rows("benchmarks/rsec_cyberbench/development.jsonl")))
    row.id = row.origin_id = "private-fixture"
    row.families = [row.id]
    row.purpose = "benchmark"
    row.task_type = "grounded_qa"
    row.source_id = source["id"]
    row.references = catalog.get(row.source_id).references
    row.programming_language = row.code = None
    row.expected_label = "benign"
    row.expected_cwe = row.asserted_ids = []
    row.messages[
        1
    ].content = "Review a fictitious deployment process for a synthetic dry-run environment."
    row.messages[
        -1
    ].content = "The procedure reported in this artificial input is restricted to dry-run."
    record = content_hash(row)
    event = Event.model_validate(
        {
            "decision": {
                "record_id": row.id,
                "record_hash": record,
                "registry_hash": catalog.hash,
                "reviewer_id": "unit-test-authority",
                "decision": "approve",
                "human_attested": True,
                "checks": ["technical_correctness", "evidence", "references", "privacy", "rights"],
                "reviewed_at": "2026-11-26",
            },
            "revision_sha256": digest([row.id, record]),
            "domain": row.domain,
            "action": "approve",
            "comments": "Disposable test workflow only",
        }
    )
    case_path, author_path, ledger = (
        tmp_path / p for p in ("case.jsonl", "authors.json", "events.jsonl")
    )
    jsonl(case_path, [row.model_dump()])
    jsonl(ledger, [sign(event, Reviewers(registry_path), private).model_dump(mode="json")])
    (tmp_path / "configs").mkdir()
    shutil.copyfile("configs/taxonomy.json", tmp_path / "configs/taxonomy.json")
    monkeypatch.chdir(tmp_path)
    for directory in ("data/pilot", "benchmarks/rsec_codebench", "benchmarks/rsec_cyberbench"):
        from pathlib import Path

        Path(directory).mkdir(parents=True, exist_ok=True)
    for name in (
        "data/pilot/candidates.jsonl",
        "benchmarks/rsec_codebench/development.jsonl",
        "benchmarks/rsec_cyberbench/development.jsonl",
        "benchmarks/suite.jsonl",
    ):
        Path(name).touch()
    write_json(author_path, {row.id: "unit-test-authority"})
    args = (case_path, author_path, ledger, registry_path, policy, "benchmarks/private/test-only")
    with pytest.raises(RsecError, match="independent"):
        import_gold(*args)
    write_json(author_path, {row.id: "different-test-author"}, overwrite=True)
    assert import_gold(*args)["cases"] == 1
