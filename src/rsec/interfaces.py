"""Future local RAG/SENTRA contracts. No network services or vector database required."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Evidence:
    text: str
    source_id: str
    source_url: str
    revision: str
    sha256: str
    trusted: bool


class Retriever(Protocol):
    def search(self, query: str, limit: int = 5) -> list[Evidence]:
        """Return versioned evidence, never executable instructions."""
        ...


class LocalAnalyzer(Protocol):
    def analyze(self, event: dict, evidence: list[Evidence]) -> dict:
        """Return findings, uncertainties, references and remediations as JSON data."""
        ...
