import copy

import pytest

from rsec.data import load_rows


@pytest.fixture
def samples():
    return copy.deepcopy(list(load_rows("data/samples/defensive.jsonl")))
