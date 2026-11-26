import copy

import pytest

from rsec.data import load_rows
from rsec.datasets.registry import Registry
from rsec.datasets.schema import Candidate, content_hash


@pytest.fixture
def registry():
    return Registry()


@pytest.fixture
def candidate():
    return copy.deepcopy(next(load_rows("data/pilot/candidates.jsonl")))


@pytest.fixture
def candidates():
    return list(load_rows("data/pilot/candidates.jsonl"))


def decision(row, registry, reviewer="test-reviewer", action="approve"):
    row = Candidate.model_validate(row) if isinstance(row, dict) else row
    return dict(
        record_id=row.id,
        record_hash=content_hash(row),
        registry_hash=registry.hash,
        reviewer_id=reviewer,
        decision=action,
        human_attested=True,
        checks=[
            "technical_correctness",
            "evidence",
            "references",
            "privacy",
            "rights",
            "remediation",
        ],
        reviewed_at="2026-11-26",
    )


@pytest.fixture
def subset(candidates):
    return [copy.deepcopy(candidates[i]) for i in (0, 8, 16, 24, 32, 40, 48, 56)]


@pytest.fixture
def decision_for(registry):
    return lambda row, reviewer="test-reviewer", action="approve": decision(
        row, registry, reviewer, action
    )
