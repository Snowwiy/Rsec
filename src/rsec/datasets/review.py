"""Explicit operator review attestations, bound to immutable candidate content."""

from collections import defaultdict
from typing import Literal

from pydantic import Field, model_validator

from rsec.config import Strict
from rsec.datasets.schema import content_hash
from rsec.errors import RsecError
from rsec.utils import digest, identifier


class Decision(Strict):
    record_id: str
    record_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    registry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_id: str = Field(min_length=1, max_length=100)
    decision: Literal["approve", "reject"]
    human_attested: bool = Field(strict=True)
    checks: list[
        Literal[
            "technical_correctness", "evidence", "references", "privacy", "rights", "remediation"
        ]
    ]
    reviewed_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

    @model_validator(mode="after")
    def attestation(self):
        identifier(self.reviewer_id)
        if self.human_attested is not True:
            raise RsecError("Human review cannot be inferred by automation")
        if self.decision == "approve" and not {
            "technical_correctness",
            "evidence",
            "references",
            "privacy",
            "rights",
        }.issubset(self.checks):
            raise RsecError("Expert approval requires all technical/provenance/privacy checks")
        return self


def apply_decisions(rows, decisions, registry_hash):
    grouped = defaultdict(list)
    ids = {r.id for r in rows}
    for raw in decisions:
        d = Decision.model_validate(raw)
        if d.record_id not in ids or d.registry_hash != registry_hash:
            raise RsecError("Review registry/record mismatch")
        grouped[d.record_id].append(d)
    for r in rows:
        # Incoming JSON cannot self-authorize expert status without the separate decisions.
        r.review.status = "GENERATED"
        r.review.reviewer_id = None
        r.review.decision_hash = None
        ds = grouped[r.id]
        if any(d.record_hash != content_hash(r) for d in ds):
            raise RsecError("Review content hash mismatch")
        if len({d.reviewer_id for d in ds}) != len(ds):
            raise RsecError("Duplicate reviewer decision")
        if any(d.decision == "reject" for d in ds):
            r.review.status = "REJECTED"
        elif len(ds) >= (2 if r.difficulty in {"advanced", "expert"} else 1):
            if r.task_type == "remediation" and any("remediation" not in d.checks for d in ds):
                raise RsecError("Remediation review missing")
            r.review.status = "EXPERT REVIEWED"
            # Lead reviewer ID; the hash-bound ledger retains every participating reviewer.
            r.review.reviewer_id = min(d.reviewer_id for d in ds)
            r.review.decision_hash = digest(
                [d.model_dump() for d in sorted(ds, key=lambda d: d.reviewer_id)]
            )
    return rows
