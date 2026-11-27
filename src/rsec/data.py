"""Untrusted data ingestion and deterministic, group-disjoint dataset releases."""

import csv
import json
import random
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from rsec.config import Strict
from rsec.errors import RsecError
from rsec.utils import (
    MAX_BYTES,
    bounded_read,
    confined,
    digest,
    jsonl,
    now,
    read_json,
    sha256,
    write_json,
)

SECRET = re.compile(
    r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}|(?i:api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_+/=-]{12,}"
)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PHONE = re.compile(r"(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)")
POISON = re.compile(
    r"ignore (?:all |the )?(?:previous|system) instructions|reveal (?:the )?system prompt|ignora (?:las )?instrucciones anteriores",
    re.I,
)


class Message(Strict):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=100000)


class Record(Strict):
    id: str = Field(min_length=1, max_length=200)
    messages: list[Message] = Field(min_length=2, max_length=100)
    source: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=2000)
    license: str = Field(min_length=1, max_length=200)
    source_version: str = Field(min_length=1, max_length=200)
    group: str = Field(min_length=1, max_length=500)
    language: Literal["es", "en"]
    category: str = Field(min_length=1, max_length=100)
    synthetic: bool = Field(strict=True)
    reviewed: bool = Field(strict=True)
    purpose: Literal["sft", "benchmark", "knowledge", "rag"] = "sft"
    redistribution: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def conversation(self):
        roles = [m.role for m in self.messages]
        if roles[0] == "system":
            roles = roles[1:]
        if roles[0] != "user" or roles[-1] != "assistant":
            raise RsecError("Conversation must begin with user and end with assistant")
        if any(role != ("user" if i % 2 == 0 else "assistant") for i, role in enumerate(roles)):
            raise RsecError("Conversation roles must alternate")
        if self.license.lower() in {"unknown", "unverified", "none"} or not self.reviewed:
            raise RsecError("License/provenance and human review required")
        return self


def text_of(record):
    return "\n".join(m["content"] for m in record["messages"])


def canonical(record):
    return unicodedata.normalize("NFKC", text_of(record)).strip().casefold()


def prompts(record):
    return [
        unicodedata.normalize("NFKC", m["content"]).strip().casefold()
        for m in record["messages"]
        if m["role"] == "user"
    ]


def sensitive(text):
    return bool(SECRET.search(text) or any(p.search(text) for p in (EMAIL, IP, PHONE)))


class ProcessingLimit(RsecError):
    """A release must be reshaped before processing can safely continue."""


class SimilarityBudget:
    """Conservative work bound for the quadratic lexical baseline."""

    def __init__(self, limit=100_000_000):
        self.remaining = limit

    def __call__(self, a, b, threshold=0.92):
        if a == b:
            return True
        self.remaining -= len(a) * len(b)
        if self.remaining < 0:
            raise ProcessingLimit("Similarity budget exceeded; use smaller reviewed shards")
        return similar(a, b, threshold)


def similar(a, b, threshold=0.92):
    # Bounded quadratic baseline for curated releases, not internet-scale ingestion.
    return SequenceMatcher(None, a, b, autojunk=False).ratio() >= threshold


def load_rows(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise RsecError("Input too large; shard into files below 64 MiB")
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(path)
        if (
            sum(
                parquet.metadata.row_group(i).total_byte_size for i in range(parquet.num_row_groups)
            )
            > MAX_BYTES
        ):
            raise RsecError("Decoded Parquet exceeds processing budget")
        yield from parquet.read().to_pylist()
        return
    text = bounded_read(path)
    if path.suffix == ".jsonl":
        for number, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    yield {"_invalid_line": number}
    elif path.suffix == ".json":
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise RsecError("JSON must be an array")
        yield from rows
    elif path.suffix == ".csv":
        import io

        for row in csv.DictReader(io.StringIO(text)):
            try:
                row["messages"] = json.loads(row["messages"])
                for key in ("synthetic", "reviewed"):
                    row[key] = json.loads(row[key].lower())
                yield row
            except (ValueError, KeyError, TypeError, AttributeError):
                yield {"_invalid_csv": True}
    elif path.suffix in {".txt", ".md"}:
        yield {"purpose": "knowledge", "text": text, "file_hash": sha256(path)}
    else:
        raise RsecError("Supported: JSON/JSONL/CSV/Parquet/Markdown/text")


def prepare(inputs, output, seed=42, benchmarks=(), anonymize=False, category_cap=None):
    if category_cap is not None and (isinstance(category_cap, bool) or category_cap < 1):
        raise RsecError("Category cap must be positive")
    output = Path(output)
    if output.exists():
        raise FileExistsError("Choose a new dataset release directory")
    heldout = [
        Record.model_validate(r.get("provenance", r)).model_dump()
        for p in benchmarks
        for r in load_rows(p)
    ]
    reserved = [canonical(r) for r in heldout]
    reserved_prompts = [p for r in heldout for p in prompts(r)]
    reserved_groups = {r["group"] for r in heldout}
    compare = SimilarityBudget()
    accepted, rejected, seen, ids = [], [], [], set()
    counts = Counter()
    for path in inputs:
        for raw in load_rows(path):
            if len(accepted) + len(rejected) >= 10000:
                raise RsecError("Curated release limit is 10000 records; shard the input")
            reason = None
            try:
                row = Record.model_validate(raw).model_dump()
                for message in row["messages"]:
                    message["content"] = unicodedata.normalize("NFKC", message["content"]).strip()
                Record.model_validate(row)
                content = text_of(row)
                if row["purpose"] != "sft":
                    reason = "not_sft"
                elif SECRET.search(content):
                    reason = "secret"
                elif POISON.search(content):
                    reason = "possible_poisoning"
                elif any(p.search(content) for p in (EMAIL, IP, PHONE)):
                    if anonymize:
                        for m in row["messages"]:
                            for pattern, replacement in (
                                (EMAIL, "[EMAIL]"),
                                (IP, "[IP]"),
                                (PHONE, "[PHONE]"),
                            ):
                                m["content"] = pattern.sub(replacement, m["content"])
                    else:
                        reason = "possible_pii"
                normalized = canonical(row)
                if len(normalized) < 40 or len(normalized) > 100000:
                    reason = reason or "quality_length"
                if (
                    row["group"] in reserved_groups
                    or any(compare(normalized, v) for v in reserved)
                    or any(compare(p, v) for p in prompts(row) for v in reserved_prompts)
                ):
                    reason = reason or "benchmark_contamination"
                if row["id"] in ids or any(compare(normalized, v) for v in seen):
                    reason = reason or "duplicate"
                if category_cap and counts[row["category"]] >= category_cap:
                    reason = reason or "category_cap"
                metadata_text = json.dumps({k: v for k, v in row.items() if k != "messages"})
                if SECRET.search(metadata_text) or any(
                    p.search(metadata_text) for p in (EMAIL, IP, PHONE)
                ):
                    reason = reason or "sensitive_metadata"
                if not reason:
                    accepted.append(row)
                    seen.append(normalized)
                    ids.add(row["id"])
                    counts[row["category"]] += 1
            except ProcessingLimit:
                raise
            except (ValidationError, TypeError, ValueError, KeyError):
                reason = "invalid_schema_or_unreviewed"
            if reason:
                # Quarantine is metadata only: never persist rejected secrets or PII.
                rejected.append({"record_hash": digest(raw), "reason": reason})
    # Similarity and provenance union prevent related examples crossing a split boundary.
    parent = list(range(len(accepted)))
    questions = [prompts(r) for r in accepted]

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, row in enumerate(accepted):
        for j in range(i):
            if (
                row["group"] == accepted[j]["group"]
                or compare(seen[i], seen[j], 0.75)
                or any(compare(a, b, 0.75) for a in questions[i] for b in questions[j])
            ):
                parent[root(i)] = root(j)
    groups = {}
    for i, row in enumerate(accepted):
        groups.setdefault(root(i), []).append(row)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    if len(keys) < 3:
        raise RsecError("Need at least three independent accepted families for train/eval/test")
    n_eval = max(1, round(len(keys) * 0.1))
    n_test = max(1, round(len(keys) * 0.1))
    splits = {
        "test": keys[:n_test],
        "eval": keys[n_test : n_test + n_eval],
        "train": keys[n_test + n_eval :],
    }
    output.mkdir(parents=True)
    for split, selected in splits.items():
        jsonl(output / f"{split}.jsonl", [r for k in selected for r in groups[k]])
    jsonl(output / "rejected_records.jsonl", rejected)
    report = {
        "accepted": len(accepted),
        "rejected": len(rejected),
        "reasons": dict(Counter(r["reason"] for r in rejected)),
        "categories": dict(counts),
        "languages": dict(Counter(r["language"] for r in accepted)),
    }
    write_json(output / "dataset_quality_report.json", report)
    manifest = {
        "version": 1,
        "created_at": now(),
        "seed": seed,
        "transform": "NFKC; schema; secret/PII/poison heuristics; similarity union; group split",
        "anonymized": anonymize,
        "inputs": [{"sha256": sha256(p), "filename": Path(p).name} for p in inputs],
        "benchmarks": [{"sha256": sha256(p), "filename": Path(p).name} for p in benchmarks],
        "files": {p.name: sha256(p) for p in output.iterdir()},
        "families": {s: len(v) for s, v in splits.items()},
    }
    write_json(output / "dataset_manifest.json", manifest)
    validate_release(output)
    return {"output": str(output), **report}


def validate_release(directory):
    directory = Path(directory)
    manifest = read_json(directory / "dataset_manifest.json")
    if manifest.get("version") == 3:
        from rsec.datasets.software import validate_mixed_release

        return validate_mixed_release(directory)
    if manifest.get("version") == 2:
        from rsec.datasets.release import validate_sft

        return validate_sft(directory)
    required = {
        "train.jsonl",
        "eval.jsonl",
        "test.jsonl",
        "rejected_records.jsonl",
        "dataset_quality_report.json",
    }
    if not required.issubset(manifest["files"]):
        raise RsecError("Incomplete manifest")
    for name, expected in manifest["files"].items():
        if sha256(confined(directory, name)) != expected:
            raise RsecError("Dataset file integrity mismatch")
    groups, contents, ids, questions = set(), [], set(), []
    compare = SimilarityBudget()
    for split in ("train", "eval", "test"):
        rows = [
            Record.model_validate(r).model_dump() for r in load_rows(directory / f"{split}.jsonl")
        ]
        if not rows:
            raise RsecError(f"Empty {split} split")
        current = {r["group"] for r in rows}
        if groups & current:
            raise RsecError("Group leakage across splits")
        current_contents = [canonical(r) for r in rows]
        current_questions = [p for r in rows for p in prompts(r)]
        if any(compare(a, b, 0.75) for a in current_contents for b in contents) or any(
            compare(a, b, 0.75) for a in current_questions for b in questions
        ):
            raise RsecError("Near-duplicate leakage across splits")
        for r in rows:
            if (
                r["id"] in ids
                or r["purpose"] != "sft"
                or SECRET.search(text_of(r))
                or POISON.search(text_of(r))
                or any(pattern.search(text_of(r)) for pattern in (EMAIL, IP, PHONE))
                or sensitive(json.dumps({k: v for k, v in r.items() if k != "messages"}))
            ):
                raise RsecError("Unsafe or duplicate training record")
            ids.add(r["id"])
        groups.update(current)
        contents.extend(current_contents)
        questions.extend(current_questions)
    return {
        "status": "TESTED",
        "records": len(ids),
        "manifest_sha256": sha256(directory / "dataset_manifest.json"),
    }
