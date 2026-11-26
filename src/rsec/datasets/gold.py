"""Import and freeze evaluator-owned, privately maintained gold candidates."""

from pathlib import Path

from rsec.data import load_rows
from rsec.datasets.linkage import contamination
from rsec.datasets.quality import inspect_candidate
from rsec.datasets.registry import Registry
from rsec.datasets.release import manifest, read_candidates, read_reserved
from rsec.datasets.review import apply_decisions
from rsec.datasets.review_security import Reviewers, SignedEvent, bind, verify
from rsec.datasets.software import RESERVED
from rsec.errors import RsecError
from rsec.utils import digest, jsonl, read_json, sha256, write_json


def import_gold(
    cases, authors, signed_reviews, reviewers_path, registry_path, output, reserved=(), training=()
):
    rows = read_candidates([cases])
    by_id = {r.id: r for r in rows}
    author_ids = read_json(authors)
    if not rows or len(rows) != len(by_id) or set(by_id) != set(author_ids):
        raise RsecError("Gold requires a distinct recorded author for every case")
    registry = Registry(registry_path)
    reviewers = Reviewers(reviewers_path)
    decisions = []
    for raw in load_rows(signed_reviews):
        signed = verify(SignedEvent.model_validate(raw), reviewers)
        row = bind(signed.event, by_id, registry.hash)
        reviewer_id = signed.event.decision.reviewer_id
        reviewer = reviewers.items[reviewer_id]
        author = reviewers.items.get(author_ids[row.id])
        if (
            author is None
            or author.fixture
            or author.id == reviewer_id
            or "adjudicate" not in reviewer.permissions
        ):
            raise RsecError("Gold cases require registered authors and independent adjudicators")
        if signed.event.action != "approve":
            raise RsecError("Only adjudicated approvals can enter the private final suite")
        decisions.append(signed.event.decision.model_dump())
    apply_decisions(rows, decisions, registry.hash)
    if any(
        r.purpose != "benchmark"
        or r.expected_label is None
        or r.source_id in {"rsec-pilot", "rsec-cyberbench", "rsec-codebench"}
        or r.review.status != "EXPERT REVIEWED"
        or inspect_candidate(r.model_dump(), registry)[0] is None
        for r in rows
    ):
        raise RsecError(
            "Private gold requires independent source, checked references and qualified review"
        )
    held = [
        *read_reserved([*RESERVED, *reserved]),
        *read_candidates(["data/pilot/candidates.jsonl", *training]),
    ]
    if contamination(rows, held)["contaminated_ids"]:
        raise RsecError("Private gold overlaps development or training families")
    root = Path(output).resolve()
    private = Path("benchmarks/private").resolve()
    if root == private or not root.is_relative_to(private):
        raise RsecError("Gold destination must be below ignored benchmarks/private")
    root.mkdir(parents=True, exist_ok=False)
    jsonl(root / "reserved.jsonl", [row.model_dump() for row in rows])
    jsonl(root / "adjudications.jsonl", list(load_rows(signed_reviews)))
    write_json(root / "author_ids.json", author_ids)
    write_json(root / "source_registry.json", read_json(registry_path))
    manifest(
        root,
        "gold_manifest.json",
        {
            "version": 1,
            "kind": "private-adjudicated-benchmark",
            "cases": len(rows),
            "registry_sha256": registry.hash,
            "excluded_corpus_sha256": digest([r.id for r in held]),
        },
    )
    return {"cases": len(rows), "manifest_sha256": sha256(root / "gold_manifest.json")}
