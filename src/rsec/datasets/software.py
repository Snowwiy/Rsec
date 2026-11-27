"""Local CodeBench contracts and deterministic, review-gated replay planning."""

import shutil
from collections import Counter
from math import comb
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from rsec.config import Strict
from rsec.data import load_rows
from rsec.datasets.linkage import contamination, related
from rsec.datasets.registry import Registry
from rsec.datasets.release import (
    manifest,
    read_candidates,
    read_reserved,
    validate_sft,
    verify_files,
)
from rsec.datasets.schema import Candidate, content_hash
from rsec.errors import RsecError
from rsec.utils import digest, identifier, jsonl, read_json, sha256, write_json

CODEBENCH = "benchmarks/rsec_codebench/development.jsonl"
SOFTWARE_TAXONOMY = "configs/software_taxonomy.json"
RESERVED = ("benchmarks/suite.jsonl", "benchmarks/rsec_cyberbench/development.jsonl", CODEBENCH)


class CodeCase(Strict):
    schema_version: Literal["codebench-1"]
    id: str = Field(max_length=100)
    family: str = Field(max_length=100)
    language: Literal["en", "es"]
    category: str
    prompt: str = Field(min_length=20, max_length=12000)
    unit_checks: list[str] = Field(max_length=30)

    @model_validator(mode="after")
    def check_ids(self):
        for value in (self.id, self.family, *self.unit_checks):
            identifier(value)
        if len(set(self.unit_checks)) != len(self.unit_checks):
            raise RsecError("Duplicate CodeBench check")
        return self

    def reservation(self):
        return Candidate(
            id=self.id,
            domain="software_engineering",
            subcategory=self.category,
            taxonomy_version="software-1.0.0",
            difficulty="intermediate",
            language=self.language,
            task_type="review",
            purpose="benchmark",
            source_id="rsec-codebench",
            source_revision="codebench-1",
            origin_id=self.family,
            families=[self.family],
            synthetic=False,
            messages=[
                {"role": "user", "content": self.prompt},
                {"role": "assistant", "content": "Reserved evaluation material."},
            ],
            evidence="Reserved software engineering development case.",
            references=[
                {
                    "id": "rsec-codebench",
                    "source_id": "rsec-codebench",
                    "url": "https://github.com/Snowwiy/Rsec",
                    "revision": "codebench-1",
                }
            ],
        )


def load_codebench(path):
    rows = [CodeCase.model_validate(row) for row in load_rows(path)]
    categories = read_json(SOFTWARE_TAXONOMY)["domains"]["software_engineering"]["subcategories"]
    if not rows or len({r.id for r in rows}) != len(rows):
        raise RsecError("Empty/duplicate CodeBench records")
    family_categories = {}
    for row in rows:
        if (
            row.category not in categories
            or family_categories.setdefault(row.family, row.category) != row.category
        ):
            raise RsecError("Unknown or inconsistent CodeBench category")
    return rows


def codebench_summary(path):
    rows = load_codebench(path)
    return {
        "cases": len(rows),
        "families": len({r.family for r in rows}),
        "languages": dict(Counter(r.language for r in rows)),
        "functional_cases": sum(bool(r.unit_checks) for r in rows),
        "suite_sha256": sha256(path),
        "scope": "public development candidates; no execution or expert gold",
    }


def pass_at_k(n, correct, k):
    if not 0 <= correct <= n or not 1 <= k <= n:
        raise RsecError("pass@k requires 0 <= correct <= n and 1 <= k <= n")
    return 1.0 - (comb(n - correct, k) / comb(n, k) if n - correct >= k else 0.0)


def plan_replay(cyber, software, max_rows, software_share, seed, extra_reserved=()):
    if not 2 <= max_rows <= 10000 or not 0 < software_share < 1:
        raise RsecError("Replay needs at least two rows and a share strictly between 0 and 1")
    reserved = read_reserved([*RESERVED, *extra_reserved])
    groups = {}
    track_rows = {}
    train = {}
    manifests = {}
    held = list(reserved)
    for track, path in (("cyber", cyber), ("software", software)):
        root = Path(path)
        result = validate_sft(root)
        catalog = Registry(root / "source_registry.json")
        manifests[track] = result["manifest_sha256"]
        expected = "software-1.0.0" if track == "software" else "1.0.0"
        taxonomy_path = SOFTWARE_TAXONOMY if track == "software" else "configs/taxonomy.json"
        if read_json(root / "taxonomy.json") != read_json(taxonomy_path):
            raise RsecError("Replay requires the frozen taxonomy for each track")
        rows = read_candidates([root / "curation_records.jsonl"])
        track_rows[track] = rows
        if any(row.taxonomy_version != expected for row in rows):
            raise RsecError("Replay track/taxonomy mismatch")
        train_ids = {r["id"] for r in load_rows(root / "train.jsonl")}
        track_train = [r for r in rows if r.id in train_ids]
        # Validate current catalog permissions as well as the reviewed release snapshot.
        current_catalog = Registry(
            "data/manifests/software_source_registry.json"
            if track == "software"
            else "data/manifests/source_registry.json"
        )
        if any(
            not current_catalog.permission(row.source_id, "sft")
            or current_catalog.get(row.source_id) != catalog.get(row.source_id)
            for row in track_train
        ):
            raise RsecError("Replay source rights changed since review")
        held.extend(r for r in rows if r.id not in train_ids)
        held.extend(read_candidates([root / "reserved.jsonl"]))
        train[track] = track_train
        groups[track] = related(track_train)[0]
    combined = [*train["cyber"], *train["software"]]
    if len({r.id for r in combined}) != len(combined):
        raise RsecError("Replay releases contain duplicate record IDs")
    if contamination(track_rows["cyber"], track_rows["software"])["contaminated_ids"]:
        raise RsecError("Replay tracks contain linked duplicate families")
    if contamination(combined, held)["contaminated_ids"]:
        raise RsecError("Replay would expose a reserved or held-out family")
    limit = max(1, min(max_rows - 1, round(max_rows * software_share)))
    quotas = {"software": limit, "cyber": max_rows - limit}
    entries = []
    actual = {}
    for track, quota in quotas.items():
        rows = train[track]
        ordered = sorted(groups[track], key=lambda g: digest([seed, sorted(rows[i].id for i in g)]))
        remaining = quota
        for group in ordered:
            if len(group) <= remaining:
                entries.extend(
                    {"track": track, "id": rows[i].id, "content_sha256": content_hash(rows[i])}
                    for i in group
                )
                remaining -= len(group)
        actual[track] = quota - remaining
    if not all(actual.values()):
        raise RsecError("Replay quota cannot fit a complete family from both tracks")
    return {
        "schema_version": 1,
        "request": {"max_rows": max_rows, "software_share": software_share},
        "seed": seed,
        "input_manifests": manifests,
        "reserved_content_sha256": digest(sorted(content_hash(r) for r in held)),
        "planned_examples": dict(quotas),
        "selected_examples": actual,
        "schedule": sorted(entries, key=lambda entry: digest([seed, entry])),
        "scope": "train-only schedule; preserve input evaluation splits; no optimization run",
    }


def make_replay_plan(cyber, software, output, max_rows, software_share, seed, extra_reserved=()):
    report = plan_replay(cyber, software, max_rows, software_share, seed, extra_reserved)
    write_json(output, report)
    return report


def mixed_splits(plan, cyber, software):
    roots = {"cyber": Path(cyber), "software": Path(software)}
    index = {
        track: {row["id"]: row for row in load_rows(root / "train.jsonl")}
        for track, root in roots.items()
    }
    result = {
        "train": [index[entry["track"]][entry["id"]] for entry in plan["schedule"]],
        **{
            split: [row for root in roots.values() for row in load_rows(root / (split + ".jsonl"))]
            for split in ("eval", "test")
        },
    }
    all_ids = [row["id"] for rows in result.values() for row in rows]
    if len(set(all_ids)) != len(all_ids):
        raise RsecError("Mixed release contains duplicate IDs across tracks or splits")
    return result


def materialize_replay(cyber, software, output, max_rows, software_share, seed, extra_reserved=()):
    report = plan_replay(cyber, software, max_rows, software_share, seed, extra_reserved)
    splits = mixed_splits(report, cyber, software)
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    for track, source in (("cyber", cyber), ("software", software)):
        shutil.copytree(source, root / track, symlinks=True)
    jsonl(
        root / "extra_reserved.jsonl", [row.model_dump() for row in read_reserved(extra_reserved)]
    )
    write_json(root / "replay_plan.json", report)
    for split, rows in splits.items():
        jsonl(root / (split + ".jsonl"), rows)
    manifest(root, "dataset_manifest.json", {"version": 3, "kind": "reviewed-mixed-replay"})
    return validate_mixed_release(root)


def validate_mixed_release(root):
    root = Path(root)
    saved = verify_files(root, "dataset_manifest.json")
    if saved.get("version") != 3 or saved.get("kind") != "reviewed-mixed-replay":
        raise RsecError("Unknown mixed release format")
    report = read_json(root / "replay_plan.json")
    checks = plan_replay(
        root / "cyber",
        root / "software",
        seed=report["seed"],
        extra_reserved=[root / "extra_reserved.jsonl"],
        **report["request"],
    )
    expected_splits = mixed_splits(checks, root / "cyber", root / "software")
    if report != checks or any(
        list(load_rows(root / (split + ".jsonl"))) != rows
        for split, rows in expected_splits.items()
    ):
        raise RsecError("Mixed release does not match the frozen plan")
    return {
        "status": "TESTED",
        "records": sum(map(len, expected_splits.values())),
        "manifest_sha256": sha256(root / "dataset_manifest.json"),
    }
