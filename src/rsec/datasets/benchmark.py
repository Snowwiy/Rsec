"""Public development benchmark validation, reservation and category rubrics."""

from collections import Counter

from rsec.data import load_rows
from rsec.datasets.linkage import contamination, related
from rsec.datasets.quality import inspect_candidate
from rsec.datasets.registry import Registry
from rsec.datasets.release import read_candidates, read_reserved
from rsec.datasets.schema import content_hash
from rsec.errors import RsecError
from rsec.evaluate import score
from rsec.utils import digest, read_json, write_json

DEFAULT_BENCH = "benchmarks/rsec_cyberbench/development.jsonl"


def validate(
    path=DEFAULT_BENCH,
    registry_path="data/manifests/source_registry.json",
    taxonomy_path="configs/taxonomy.json",
):
    registry = Registry(registry_path)
    taxonomy = read_json(taxonomy_path)
    rows = read_candidates([path])
    if not rows or len({r.id for r in rows}) != len(rows):
        raise RsecError("Empty/duplicate benchmark IDs")
    for r in rows:
        checked, _ = inspect_candidate(r.model_dump(), registry, taxonomy)
        if (
            r.purpose not in {"benchmark", "regression"}
            or r.expected_label is None
            or checked is None
        ):
            raise RsecError("Invalid benchmark purpose, reference or expected schema")
    groups, links = related(rows)
    if any(len({rows[i].purpose for i in g}) > 1 for g in groups):
        raise RsecError("Related benchmark families must remain in one partition")
    return {
        "name": "Rsec-CyberBench",
        "version": "0.1.0",
        "scope": "public development; not final hidden gold",
        "cases": len(rows),
        "families": len(groups),
        "link_count": len(links),
        "expert_reviewed": sum(r.review.status == "EXPERT REVIEWED" for r in rows),
        "human_gold_certified": False,
        "labels": dict(Counter(r.expected_label for r in rows)),
        "domains": dict(Counter(r.domain for r in rows)),
        "languages": dict(Counter(r.language for r in rows)),
        "benchmark_hash": digest([content_hash(r) for r in rows]),
    }


def evaluate_benchmark(predictions, output, benchmark=DEFAULT_BENCH):
    validation = validate(benchmark)
    rows = read_candidates([benchmark])
    cases = [
        {
            "id": r.id,
            "expected": {
                "label": r.expected_label,
                "cwe": r.expected_cwe,
                "references": [ref.id for ref in r.references],
            },
        }
        for r in rows
    ]
    report = {
        "benchmark": validation,
        "mechanical_metrics": score(cases, list(load_rows(predictions))),
        "category_rubric_scores": None,
        "semantic_hallucinations": None,
        "remediation_success": None,
        "limitations": [
            "Development candidate labels are not expert gold.",
            "Category rubrics require independent reviewers.",
            "No generated code is executed.",
            "Unsupported reference rate is not a semantic hallucination metric.",
        ],
    }
    write_json(output, report)
    return report


def check_contamination(inputs, reserved):
    if not reserved:
        raise RsecError("At least one reserved benchmark is required")
    return contamination(read_candidates(inputs), read_reserved(reserved))


def export_cases(output, benchmark=DEFAULT_BENCH):
    from rsec.utils import jsonl, sha256

    validate(benchmark)
    rows = read_candidates([benchmark])
    cases = [
        {
            "id": r.id,
            "domain": r.domain,
            "language": r.language,
            "prompt": "\n".join(m.content for m in r.messages if m.role == "user"),
            "expected": {
                "label": r.expected_label,
                "cwe": r.expected_cwe,
                "references": [ref.id for ref in r.references],
            },
            "difficulty": r.difficulty,
            "partition": r.purpose,
            "expert_reviewed": False,
        }
        for r in rows
    ]
    jsonl(output, cases)
    return {
        "output": str(output),
        "cases": len(cases),
        "sha256": sha256(output),
        "scope": "Development plumbing only; not expert-certified or private final gold",
    }


def score_rubrics(
    ratings, output, benchmark=DEFAULT_BENCH, rubrics="benchmarks/rsec_cyberbench/rubrics.json"
):
    from rsec.utils import identifier

    validate(benchmark)
    cases = {r.id: r for r in read_candidates([benchmark])}
    spec = read_json(rubrics)
    results = []
    seen = set()
    for raw in load_rows(ratings):
        if (
            not isinstance(raw, dict)
            or raw.get("human_attested") is not True
            or raw.get("record_id") not in cases
            or raw.get("rubric_hash") != digest(spec)
        ):
            raise RsecError("Human rubric attestation/schema mismatch")
        reviewer = identifier(raw["reviewer_id"])
        r = cases[raw["record_id"]]
        if raw.get("record_hash") != content_hash(r):
            raise RsecError("Rubric candidate hash mismatch")
        if (r.id, reviewer) in seen:
            raise RsecError("Duplicate rubric rating")
        seen.add((r.id, reviewer))
        weights = spec["domains"][r.domain]
        scores = raw["scores"]
        if set(scores) != set(weights) or any(
            type(v) is not int or v not in (0, 1, 2) for v in scores.values()
        ):
            raise RsecError("Rubric scores require all criteria and integer values 0..2")
        results.append(
            {
                "record_id": r.id,
                "reviewer_id": reviewer,
                "domain": r.domain,
                "normalized_score": sum(scores[k] * w for k, w in weights.items())
                / (2 * sum(weights.values())),
            }
        )
    reviewed = {r["record_id"] for r in results}
    report = {
        "ratings": len(results),
        "cases_with_ratings": len(reviewed),
        "total_cases": len(cases),
        "coverage": len(reviewed) / len(cases),
        "results": results,
        "expert_gold_certified": False,
        "note": "Scores reflect explicit operator-provided human attestations; identity and technical authority are not authenticated by this local tool.",
    }
    write_json(output, report)
    return report
