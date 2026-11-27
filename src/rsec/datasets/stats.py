"""Actual tokenizer measurements are distinct from whitespace observations."""

import json
from collections import Counter
from pathlib import Path

from rsec.errors import RsecError
from rsec.utils import digest, sha256


def distribution(values):
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "max": None,
            "sum": 0,
        }
    v = sorted(values)

    def q(p):
        k = (len(v) - 1) * p
        i = int(k)
        return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (k - i)

    return {
        "count": len(v),
        "mean": sum(v) / len(v),
        "median": q(0.5),
        "p90": q(0.9),
        "p95": q(0.95),
        "p99": q(0.99),
        "max": max(v),
        "sum": sum(v),
    }


def statistics(rows, tokenizer_path=None):
    result = {
        "records": len(rows),
        "domains": dict(Counter(r.domain for r in rows)),
        "languages": dict(Counter(r.language for r in rows)),
        "difficulties": dict(Counter(r.difficulty for r in rows)),
        "whitespace_units": distribution(
            [sum(len(m.content.split()) for m in r.messages) for r in rows]
        ),
        "serialized_utf8_bytes": sum(
            len((json.dumps(r.model_dump(), ensure_ascii=False) + "\n").encode()) for r in rows
        ),
        "tokenizer_tokens": None,
        "tokens_per_epoch_eligible_sft": None,
        "contexts": None,
        "note": "Whitespace units are not tokenizer counts; memory feasibility and training time are not measured.",
    }
    if tokenizer_path:
        from transformers import AutoTokenizer

        path = Path(tokenizer_path).resolve(strict=True)
        if any(p.is_symlink() for p in path.rglob("*")):
            raise RsecError("Materialized local tokenizer required")
        tokenizer = AutoTokenizer.from_pretrained(
            str(path), local_files_only=True, trust_remote_code=False
        )
        if not tokenizer.chat_template:
            raise RsecError("Official/reviewed chat template required")
        counts = []
        eligible = 0
        for r in rows:
            tokens = tokenizer.apply_chat_template(
                [m.model_dump() for m in r.messages], tokenize=True, return_dict=False
            )
            counts.append(len(tokens))
            if r.purpose == "sft" and r.review.status == "EXPERT REVIEWED":
                eligible += len(tokens)
        result.update(
            tokenizer_tokens=distribution(counts),
            tokens_per_epoch_eligible_sft=eligible,
            contexts={
                str(n): {
                    "over_context": sum(c > n for c in counts),
                    "within_context": sum(c <= n for c in counts),
                }
                for n in (1024, 2048, 4096, 8192)
            },
            tokenizer_identity={
                "files": {
                    p.name: sha256(p)
                    for p in path.iterdir()
                    if p.is_file() and p.suffix in {".json", ".jinja", ".model", ".txt"}
                },
                "chat_template_hash": digest(tokenizer.chat_template),
            },
            token_lengths=[{"id": r.id, "tokens": n} for r, n in zip(rows, counts, strict=True)],
        )
    return result
