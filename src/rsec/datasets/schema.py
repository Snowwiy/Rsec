"""Metadata contracts; only messages are eventually sent to SFT."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from rsec.config import Strict
from rsec.data import Message
from rsec.errors import RsecError
from rsec.utils import digest, identifier, read_json

STATE = Literal[
    "GENERATED",
    "AUTOMATED VALIDATION PASSED",
    "EXPERT REVIEW REQUIRED",
    "EXPERT REVIEWED",
    "REJECTED",
]


def https_url(value):
    p = urlsplit(value)
    if (
        p.scheme != "https"
        or not p.hostname
        or p.username
        or p.password
        or p.port not in (None, 443)
        or p.fragment.startswith("javascript:")
    ):
        raise RsecError("Reference/source URL must be credential-free HTTPS")
    return value


class Reference(Strict):
    id: str = Field(min_length=1, max_length=150)
    source_id: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2000)
    revision: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_url(self):
        https_url(self.url)
        return self


class Generation(Strict):
    method: Literal["deterministic_template", "manual_authoring", "external_transformation"]
    template_id: str = Field(min_length=1, max_length=200)
    generator_version: str = Field(min_length=1, max_length=100)
    generated_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    original_id: str = Field(min_length=1, max_length=200)
    authorization: str = Field(min_length=1, max_length=500)
    validation_method: str = Field(min_length=1, max_length=500)


class Review(Strict):
    status: STATE = "GENERATED"
    reviewer_id: str | None = Field(None, max_length=100)
    decision_hash: str | None = Field(None, pattern=r"^[0-9a-f]{64}$")
    automated_passed: bool = Field(False, strict=True)

    @model_validator(mode="after")
    def expert(self):
        if self.status == "EXPERT REVIEWED" and (not self.reviewer_id or not self.decision_hash):
            raise RsecError("Expert status requires an explicit hash-bound review decision")
        return self


class Candidate(Strict):
    schema_version: Literal[2] = 2
    id: str = Field(min_length=1, max_length=150)
    taxonomy_version: str = "1.0.0"
    domain: str = Field(min_length=1, max_length=100)
    subcategory: str = Field(min_length=1, max_length=100)
    difficulty: Literal["fundamental", "intermediate", "advanced", "expert"]
    language: Literal["en", "es"]
    task_type: str = Field(min_length=1, max_length=100)
    purpose: Literal["sft", "knowledge", "rag", "benchmark", "regression"]
    source_id: str = Field(min_length=1, max_length=100)
    source_revision: str = Field(min_length=1, max_length=200)
    origin_id: str = Field(min_length=1, max_length=200)
    families: list[str] = Field(min_length=1, max_length=50)
    translation_of: str | None = Field(None, max_length=150)
    programming_language: str | None = Field(None, max_length=50)
    synthetic: bool = Field(strict=True)
    messages: list[Message] = Field(min_length=2, max_length=50)
    references: list[Reference] = Field(min_length=1, max_length=30)
    asserted_ids: list[str] = Field(default_factory=list, max_length=100)
    evidence: str = Field(min_length=1, max_length=30000)
    code: str | None = Field(None, max_length=30000)
    expected_label: Literal["vulnerable", "benign", "insufficient"] | None = None
    expected_cwe: list[str] = Field(default_factory=list, max_length=30)
    generation: Generation | None = None
    review: Review = Field(default_factory=Review)

    @model_validator(mode="after")
    def validate_conversation(self):
        identifier(self.id)
        if self.synthetic and not self.generation:
            raise RsecError("Synthetic examples require generation provenance")
        roles = [m.role for m in self.messages]
        if roles[0] == "system":
            roles = roles[1:]
        if (
            not roles
            or roles[-1] != "assistant"
            or any(r != ("user" if i % 2 == 0 else "assistant") for i, r in enumerate(roles))
        ):
            raise RsecError("Conversation must alternate user/assistant and end with assistant")
        if len(set(self.families)) != len(self.families) or any(
            not f.strip() or len(f) > 200 for f in self.families
        ):
            raise RsecError("Invalid provenance families")
        return self


def content_hash(row):
    value = row.model_dump() if isinstance(row, Candidate) else dict(row)
    value.pop("review", None)
    return digest(value)


def validate_taxonomy(row, taxonomy="configs/taxonomy.json"):
    t = read_json(taxonomy) if isinstance(taxonomy, (str, Path)) else taxonomy
    if row.taxonomy_version != t["version"] or row.domain not in t["domains"]:
        raise RsecError("Unknown taxonomy version/domain")
    if (
        row.subcategory not in t["domains"][row.domain]["subcategories"]
        or row.task_type not in t["task_types"]
    ):
        raise RsecError("Unknown subcategory/task type")
    if row.programming_language and row.programming_language not in t["programming_languages"]:
        raise RsecError("Unknown programming language")
    return row
