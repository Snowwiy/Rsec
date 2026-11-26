"""Immutable curation bundles and an explicit expert-reviewed bridge to phase-01 SFT."""

from pathlib import Path

from rsec.data import Record, load_rows
from rsec.datasets.linkage import approximate_duplicates, contamination, related
from rsec.datasets.quality import inspect_candidate, normalize, summarize
from rsec.datasets.registry import Registry
from rsec.datasets.review import apply_decisions
from rsec.datasets.schema import Candidate, content_hash
from rsec.datasets.stats import statistics
from rsec.errors import RsecError
from rsec.utils import confined, digest, identifier, jsonl, read_json, sha256, write_json


def read_candidates(paths):
    rows = []
    for p in paths:
        for raw in load_rows(p):
            if len(rows) >= 10000:
                raise RsecError("Curation row limit exceeded; shard input")
            rows.append(Candidate.model_validate(raw))
    return rows


def read_reserved(paths):
    rows = []
    for path in paths:
        for raw in load_rows(path):
            if len(rows) >= 10000:
                raise RsecError("Reserved benchmark row limit exceeded")
            if isinstance(raw, dict) and raw.get("schema_version") == 2:
                rows.append(Candidate.model_validate(raw))
            elif isinstance(raw, dict) and "provenance" in raw:
                old = Record.model_validate(raw["provenance"])
                code = __import__("re").findall(
                    r"```[^\n]*\n(.*?)```", raw["prompt"], __import__("re").S
                )
                rows.append(
                    Candidate.model_validate(
                        {
                            "id": old.id,
                            "domain": "application_security",
                            "subcategory": "code_audit",
                            "difficulty": "intermediate",
                            "language": old.language,
                            "task_type": "grounded_qa",
                            "purpose": "benchmark",
                            "source_id": "rsec-cyberbench",
                            "source_revision": "cyberbench-0.1.0",
                            "origin_id": old.group,
                            "families": [old.group],
                            "synthetic": old.synthetic,
                            "messages": [m.model_dump() for m in old.messages],
                            "evidence": raw["prompt"],
                            "code": "\n".join(code) or None,
                            "references": [
                                {
                                    "id": "rsec-bench-spec",
                                    "source_id": "rsec-cyberbench",
                                    "url": "https://github.com/Snowwiy/Rsec",
                                    "revision": "cyberbench-0.1.0",
                                }
                            ],
                            "generation": {
                                "method": "external_transformation",
                                "template_id": "legacy-reservation-only",
                                "generator_version": "1.0.0",
                                "generated_at": "2026-11-26",
                                "original_id": old.id,
                                "authorization": "Existing MIT repository fixture; reservation only",
                                "validation_method": "Legacy schema; no expert or SFT promotion",
                            },
                        }
                    )
                )
            else:
                raise RsecError("Unsupported reserved benchmark schema")
    return rows


def manifest(root, name, metadata):
    files = {
        str(p.relative_to(root)): sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and p != root / name
    }
    write_json(root / name, {**metadata, "files": files})


def verify_files(root, name):
    root = Path(root)
    if (root / name).is_symlink():
        raise RsecError("Symlink manifest rejected")
    m = read_json(root / name)
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p != root / name}
    if any(p.is_symlink() for p in root.rglob("*")) or actual != set(m["files"]):
        raise RsecError("Release file inventory mismatch")
    for relative, expected in m["files"].items():
        if sha256(confined(root, relative)) != expected:
            raise RsecError("Release integrity mismatch")
    return m


def split_rows(rows, seed=42):
    groups, links = related(rows)
    if len(groups) < 3:
        raise RsecError("Need three independent expert-reviewed SFT families")
    groups.sort(key=lambda g: digest({"seed": seed, "ids": sorted(rows[i].id for i in g)}))
    ntest = max(1, round(len(groups) * 0.05))
    neval = max(1, round(len(groups) * 0.10))
    selections = {
        "test": groups[:ntest],
        "eval": groups[ntest : ntest + neval],
        "train": groups[ntest + neval :],
    }
    return {
        s: [
            (rows[i], "family-" + digest(sorted(rows[j].id for j in g))[:20]) for g in gs for i in g
        ]
        for s, gs in selections.items()
    }, links


def legacy(row, group, registry):
    s = registry.get(row.source_id)
    return Record.model_validate(
        {
            "id": row.id,
            "messages": [m.model_dump() for m in row.messages],
            "source": s.name,
            "source_url": s.url,
            "license": s.license,
            "source_version": row.source_revision,
            "group": group,
            "language": row.language,
            "category": row.domain,
            "synthetic": row.synthetic,
            "reviewed": True,
            "purpose": "sft",
            "redistribution": s.redistribution_conditions,
        }
    ).model_dump()


def export_sft(rows, output, registry, decisions, taxonomy, seed, reserved):
    output = Path(output)
    splits, links = split_rows(rows, seed)
    output.mkdir(parents=True, exist_ok=False)
    for s, selected in splits.items():
        jsonl(output / (s + ".jsonl"), [legacy(r, g, registry) for r, g in selected])
    jsonl(output / "curation_records.jsonl", [r.model_dump() for r in rows])
    jsonl(output / "reviews.jsonl", decisions)
    jsonl(output / "reserved.jsonl", [r.model_dump() for r in reserved])
    write_json(output / "source_registry.json", read_json(registry.path))
    write_json(output / "taxonomy.json", taxonomy)
    jsonl(output / "rejected_records.jsonl", [])
    write_json(
        output / "dataset_quality_report.json",
        {
            "accepted": len(rows),
            "rejected": 0,
            "groups": len(set(g for selected in splits.values() for _, g in selected)),
            "link_count": len(links),
        },
    )
    manifest(
        output,
        "dataset_manifest.json",
        {
            "version": 2,
            "kind": "expert-reviewed-sft",
            "seed": seed,
            "registry_hash": registry.hash,
            "taxonomy_hash": digest(taxonomy),
            "records": len(rows),
            "transform": "phase2 quality + explicit reviews + provenance/translation/code/lexical family split",
        },
    )
    validate_sft(output)


def curate(
    inputs,
    output,
    version,
    registry_path="data/manifests/source_registry.json",
    taxonomy_path="configs/taxonomy.json",
    reserved_paths=(),
    decisions_path=None,
    seed=42,
    anonymize=False,
):
    identifier(version)
    output = Path(output)
    if output.exists():
        raise FileExistsError("Choose a new immutable curation directory")
    registry = Registry(registry_path)
    taxonomy = read_json(taxonomy_path)
    reserved = read_reserved(reserved_paths)
    decisions = list(load_rows(decisions_path)) if decisions_path else []
    valid = []
    reports = []
    ids = set()
    seen = set()
    for p in inputs:
        for raw in load_rows(p):
            if len(reports) >= 10000:
                raise RsecError("Curation row limit exceeded")
            row, report = inspect_candidate(raw, registry, taxonomy, anonymize)
            if row:
                key = digest([normalize(m.content) for m in row.messages])
                if row.id in ids or key in seen:
                    report["reasons"] = ["duplicate_id_or_exact_content"]
                    report["disposition"] = "quarantined"
                    row = None
                else:
                    ids.add(row.id)
                    seen.add(key)
            if row:
                valid.append(row)
            reports.append(report)
    apply_decisions(valid, decisions, registry.hash)
    duplicates = approximate_duplicates(valid)
    check = contamination(valid, reserved)
    blocked = set(check["contaminated_ids"])
    clean = []
    by_hash = {r["record_hash"]: r for r in reports}
    for row in valid:
        report = by_hash[content_hash(row)]
        if row.id in duplicates:
            report["reasons"] = ["approximate_duplicate"]
            report["disposition"] = "quarantined"
        elif row.id in blocked:
            report["reasons"] = ["reserved_contamination"]
            report["disposition"] = "quarantined"
        elif row.review.status == "REJECTED":
            report["reasons"] = ["review_rejected"]
            report["disposition"] = "quarantined"
        else:
            row.review.automated_passed = True
            if row.review.status != "EXPERT REVIEWED":
                row.review.status = "EXPERT REVIEW REQUIRED"
            report["disposition"] = (
                "expert_reviewed" if row.review.status == "EXPERT REVIEWED" else "pending_review"
            )
            clean.append(row)
    quality = summarize(clean, reports)
    quality["version"] = version
    quality["contamination"] = check
    output.mkdir(parents=True, exist_ok=False)
    jsonl(output / "records.jsonl", [r.model_dump() for r in clean])
    jsonl(
        output / "quarantine.jsonl",
        [
            {
                "record_hash": r["record_hash"],
                "reasons": r["reasons"],
                "disposition": r["disposition"],
            }
            for r in reports
            if r["reasons"]
        ],
    )
    jsonl(output / "quality_observations.jsonl", reports)
    jsonl(output / "reviews.jsonl", decisions)
    jsonl(output / "reserved.jsonl", [r.model_dump() for r in reserved])
    write_json(output / "quality_report.json", quality)
    write_json(output / "statistics.json", statistics(clean))
    write_json(output / "source_registry.json", read_json(registry_path))
    write_json(output / "taxonomy.json", taxonomy)
    eligible = [r for r in clean if r.purpose == "sft" and r.review.status == "EXPERT REVIEWED"]
    enough_families = bool(eligible) and len(related(eligible)[0]) >= 3
    quality["sft_release"] = (
        "available"
        if enough_families
        else "BLOCKED: fewer than three expert-approved families"
        if eligible
        else "BLOCKED: no expert-approved examples"
    )
    if enough_families:
        export_sft(eligible, output / "sft", registry, decisions, taxonomy, seed, reserved)
    write_json(
        output / "release_status.json",
        {
            "version": version,
            "sft": quality["sft_release"],
            "training_readiness": "NOT READY",
            "expert_approved_sft": len(eligible),
        },
    )
    manifest(
        output,
        "curation_manifest.json",
        {
            "version": 2,
            "kind": "curation",
            "dataset_version": version,
            "inputs": [{"filename": Path(p).name, "sha256": sha256(p)} for p in inputs],
            "registry_hash": registry.hash,
            "taxonomy_hash": digest(taxonomy),
            "seed": seed,
        },
    )
    validate_bundle(output)
    return {"output": str(output), **quality}


def validate_bundle(root):
    root = Path(root)
    m = verify_files(root, "curation_manifest.json")
    if m.get("version") != 2 or m.get("kind") != "curation":
        raise RsecError("Unknown curation manifest")
    registry = Registry(root / "source_registry.json")
    taxonomy = read_json(root / "taxonomy.json")
    if registry.hash != m["registry_hash"] or digest(taxonomy) != m["taxonomy_hash"]:
        raise RsecError("Policy snapshot mismatch")
    rows = read_candidates([root / "records.jsonl"])
    decisions = list(load_rows(root / "reviews.jsonl"))
    apply_decisions(rows, decisions, registry.hash)
    for r in rows:
        checked, _ = inspect_candidate(r.model_dump(), registry, taxonomy)
        if checked is None:
            raise RsecError("Unsafe curated record")
    if contamination(rows, read_candidates([root / "reserved.jsonl"]))["contaminated_ids"]:
        raise RsecError("Reserved contamination")
    if (root / "sft").exists():
        validate_sft(root / "sft")
    return {
        "status": "TESTED",
        "records": len(rows),
        "version": m["dataset_version"],
        "manifest_sha256": sha256(root / "curation_manifest.json"),
    }


def validate_sft(root):
    root = Path(root)
    m = verify_files(root, "dataset_manifest.json")
    if m.get("version") != 2 or m.get("kind") != "expert-reviewed-sft":
        raise RsecError("Unknown SFT release")
    registry = Registry(root / "source_registry.json")
    taxonomy = read_json(root / "taxonomy.json")
    if registry.hash != m["registry_hash"] or digest(taxonomy) != m["taxonomy_hash"]:
        raise RsecError("SFT policy snapshot mismatch")
    rows = read_candidates([root / "curation_records.jsonl"])
    apply_decisions(rows, list(load_rows(root / "reviews.jsonl")), registry.hash)
    if len({r.id for r in rows}) != len(rows) or any(
        r.review.status != "EXPERT REVIEWED" or r.purpose != "sft" for r in rows
    ):
        raise RsecError("Expert-reviewed SFT required")
    for r in rows:
        checked, _ = inspect_candidate(r.model_dump(), registry, taxonomy)
        if checked is None:
            raise RsecError("Unsafe SFT metadata/content")
    if contamination(rows, read_candidates([root / "reserved.jsonl"]))["contaminated_ids"]:
        raise RsecError("SFT reserved contamination")
    owner = {}
    by_id = {r.id: r for r in rows}
    seen = set()
    group_owner = {}
    for s in ("train", "eval", "test"):
        actual = list(load_rows(root / (s + ".jsonl")))
        if not actual:
            raise RsecError("Empty SFT split")
        for raw in actual:
            old = Record.model_validate(raw).model_dump()
            rid = old["id"]
            if rid in seen or rid not in by_id:
                raise RsecError("SFT record inventory mismatch")
            if old != legacy(by_id[rid], old["group"], registry):
                raise RsecError("SFT bridge mismatch")
            if old["group"] in group_owner and group_owner[old["group"]] != s:
                raise RsecError("SFT group leakage")
            group_owner[old["group"]] = s
            seen.add(rid)
            owner[rid] = s
    if seen != set(by_id):
        raise RsecError("Missing SFT examples")
    groups, _ = related(rows)
    if any(len({owner[rows[i].id] for i in g}) != 1 for g in groups):
        raise RsecError("SFT translation/code/provenance leakage")
    return {
        "status": "TESTED",
        "records": len(seen),
        "manifest_sha256": sha256(root / "dataset_manifest.json"),
    }
