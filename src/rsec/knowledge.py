"""Curate knowledge/RAG documents separately from supervised examples."""

import json
import unicodedata
from pathlib import Path

from rsec.data import EMAIL, IP, PHONE, POISON, SECRET, load_rows, sensitive
from rsec.errors import RsecError
from rsec.utils import digest, jsonl, now, sha256, write_json


def classify(text):
    lowered = text.lower()
    domain = "general_security"
    for name, terms in {
        "appsec": ["sql", "xss", "code"],
        "soc": ["alert", "siem", "event"],
        "dfir": ["forensic", "evidence"],
        "hardening": ["firewall", "configuration"],
        "vulnerability": ["cve-", "cwe-"],
    }.items():
        if any(term in lowered for term in terms):
            domain = name
            break
    language = (
        "es"
        if any(word in lowered.split() for word in ("seguridad", "para", "una", "los", "evidencia"))
        else "en"
    )
    return domain, language


def ingest(
    inputs,
    output,
    source,
    source_url,
    license,
    version,
    redistribution,
    reviewed=False,
    purpose="knowledge",
    anonymize=False,
):
    metadata = [source, source_url, license, version, redistribution]
    if (
        reviewed is not True
        or any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in metadata)
        or license.strip().lower() in {"unknown", "unverified", "none"}
    ):
        raise RsecError("Knowledge acquisition requires source-specific license review")
    if sensitive(json.dumps(metadata)):
        raise RsecError("Sensitive knowledge provenance metadata rejected")
    if purpose not in {"knowledge", "rag"}:
        raise RsecError("Documents cannot be automatically converted to SFT")
    if Path(output).exists():
        raise FileExistsError("Choose a new knowledge release path")
    accepted, rejected, seen = [], [], set()
    for path in inputs:
        for raw in load_rows(path):
            if len(accepted) + len(rejected) >= 10000:
                raise RsecError("Knowledge release limit exceeded; shard the input")
            text = raw.get("text") if isinstance(raw, dict) else None
            if text is not None and not isinstance(text, str):
                rejected.append({"record_hash": digest(raw), "reason": "invalid_text"})
                continue
            if text is None:
                text = json.dumps(raw, ensure_ascii=False)
            text = unicodedata.normalize("NFKC", text).strip()
            reason = None
            if len(text) < 40 or len(text) > 100000:
                reason = "quality_length"
            elif SECRET.search(text):
                reason = "secret"
            elif POISON.search(text):
                reason = "possible_poisoning"
            elif any(pattern.search(text) for pattern in (EMAIL, IP, PHONE)):
                if anonymize:
                    for pattern, replacement in (
                        (EMAIL, "[EMAIL]"),
                        (IP, "[IP]"),
                        (PHONE, "[PHONE]"),
                    ):
                        text = pattern.sub(replacement, text)
                else:
                    reason = "possible_pii"
            key = digest(text)
            if key in seen:
                reason = reason or "duplicate"
            if reason:
                rejected.append({"record_hash": digest(raw), "reason": reason})
                continue
            domain, language = classify(text)
            seen.add(key)
            accepted.append(
                {
                    "id": key,
                    "text": text,
                    "source": source,
                    "source_url": source_url,
                    "license": license,
                    "version": version,
                    "redistribution": redistribution,
                    "purpose": purpose,
                    "category": domain,
                    "language": language,
                    "classification_method": "keyword heuristic; human verification required",
                    "acquired_at": now(),
                    "input_sha256": sha256(path),
                    "transform": "NFKC; heuristic screening; optional anonymization",
                    "trusted": False,
                }
            )
    if not accepted:
        raise RsecError("No acceptable documents")
    jsonl(output, accepted)
    jsonl(str(output) + ".rejected.jsonl", rejected)
    write_json(
        str(output) + ".manifest.json",
        {
            "sha256": sha256(output),
            "records": len(accepted),
            "rejected": len(rejected),
            "purpose": purpose,
        },
    )
    return {"output": str(output), "records": len(accepted), "rejected": len(rejected)}
