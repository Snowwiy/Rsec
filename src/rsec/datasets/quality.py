"""Deterministic checks are evidence of process, never expert correctness."""

import json
import re
import unicodedata
from collections import Counter

from rsec.data import EMAIL, IP, PHONE, POISON, SECRET
from rsec.datasets.registry import Registry
from rsec.datasets.schema import Candidate, content_hash, validate_taxonomy
from rsec.errors import RsecError
from rsec.utils import digest


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def pii(text, registry):
    # Registered public CVE/CWE identifiers are not telephone numbers. No blanket digit exemption.
    for s in registry.sources.values():
        for value in s.identifiers:
            text = text.replace(value, "[PUBLIC_IDENTIFIER]")
    text = re.sub(
        r"\b(?:CVE-\d{4}-\d{4,10}|CWE-\d{1,5}|\d{4}-\d{2}-\d{2})\b",
        "[STRUCTURED_PUBLIC_FORMAT]",
        text,
    )
    return any(p.search(text) for p in (EMAIL, IP, PHONE))


def classify(text):
    """Hints only: annotations and expert review remain authoritative."""
    t = normalize(text)
    vocabulary = {
        "application_security": ["sql", "parameterized", "authorization", "code audit"],
        "soc_detection": ["siem", "alert", "telemetry", "edr"],
        "vulnerability_management": ["advisory", "cve-", "cvss", "affected version"],
        "infrastructure_security": ["kubernetes", "firewall", "container", "hardening"],
        "dfir": ["custody", "forensic", "timeline", "evidence preservation"],
        "grc": ["risk register", "asset owner", "risk acceptance"],
        "ai_security": ["retrieved document", "rag", "prompt injection", "llm"],
        "cryptography_identity": ["certificate", "tls", "mfa", "oauth", "private key"],
    }
    counts = {d: sum(v in t for v in words) for d, words in vocabulary.items()}
    ranked = sorted(counts, key=lambda d: (-counts[d], d))
    domain = ranked[0] if counts[ranked[0]] else None
    es = sum(
        bool(re.search(r"\b" + w + r"\b", t))
        for w in [
            "evidencia",
            "configuración",
            "datos",
            "seguridad",
            "información",
            "contraseña",
            "analiza",
        ]
    )
    en = sum(
        bool(re.search(r"\b" + w + r"\b", t))
        for w in ["evidence", "configuration", "security", "information", "analyze", "supplied"]
    )
    return {
        "domain_hint": domain,
        "language_hint": "es" if es > en else "en" if en > es else None,
        "method": "bounded keyword heuristic; not technical or human validation",
    }


def inspect_candidate(raw, registry=None, taxonomy="configs/taxonomy.json", anonymize=False):
    registry = registry or Registry()
    try:
        row = validate_taxonomy(Candidate.model_validate(raw), taxonomy)
    except (ValueError, TypeError, KeyError):
        return None, {
            "record_hash": digest(raw),
            "reasons": ["invalid_schema_or_taxonomy"],
            "disposition": "rejected",
        }
    for m in row.messages:
        m.content = unicodedata.normalize("NFKC", m.content).strip()
    row.evidence = unicodedata.normalize("NFKC", row.evidence).strip()
    content = "\n".join([m.content for m in row.messages] + [row.evidence, row.code or ""])
    reasons = []
    if SECRET.search(content):
        reasons.append("secret")
    if POISON.search(content):
        reasons.append("possible_poisoning")
    if pii(content, registry):
        if anonymize and not row.code:
            for m in row.messages:
                for p, replacement in ((EMAIL, "[EMAIL]"), (IP, "[IP]"), (PHONE, "[PHONE]")):
                    m.content = p.sub(replacement, m.content)
            for p, replacement in ((EMAIL, "[EMAIL]"), (IP, "[IP]"), (PHONE, "[PHONE]")):
                row.evidence = p.sub(replacement, row.evidence)
            # Redaction changes reviewed content; no review status survives it.
            row.review.status = "GENERATED"
            row.review.reviewer_id = None
            row.review.decision_hash = None
        else:
            reasons.append("possible_pii")
    metadata = row.model_dump(exclude={"messages", "evidence", "code", "review"})
    # Revision strings are public commit identifiers; protect all other metadata.
    metadata.pop("source_revision", None)
    if SECRET.search(json.dumps(metadata)) or pii(json.dumps(metadata), registry):
        reasons.append("sensitive_metadata")
    allowed = {v for s in registry.sources.values() for v in s.identifiers}
    try:
        source = registry.get(row.source_id)
        if source.version != row.source_revision:
            reasons.append("source_revision_mismatch")
        if not registry.permission(row.source_id, row.purpose):
            reasons.append("rights_or_purpose_blocked")
        if any(not registry.reference(r) for r in row.references):
            reasons.append("unverified_reference")
        if any(v not in allowed for v in row.asserted_ids):
            reasons.append("unverified_identifier")
    except RsecError:
        reasons.append("unregistered_source_or_reference")
    answer = row.messages[-1].content
    if not answer.strip() or not all(m.content.strip() for m in row.messages):
        reasons.append("empty_content")
    if len(content) > 60000:
        reasons.append("length_budget")
    if len(answer.split()) < 3:
        reasons.append("answer_too_short")
    if re.search(r"\b(?:I ran|I executed|I scanned|he ejecutado|ejecuté)\b", answer, re.I):
        reasons.append("unsupported_execution_claim")
    words = normalize(answer).split()
    if len(words) > 30 and len(set(words)) / len(words) < 0.15:
        reasons.append("anomalous_repetition")
    mentioned = set(re.findall(r"\b(?:CVE-\d{4}-\d{4,10}|CWE-\d+)\b", answer))
    if mentioned - allowed and row.expected_label != "insufficient":
        reasons.append("unverified_answer_identifier")
    if row.task_type == "structured_json" or answer.startswith("{"):
        try:
            parsed = json.loads(answer)
            if not isinstance(parsed, dict):
                reasons.append("invalid_structured_answer")
            elif row.expected_label and parsed.get("label") != row.expected_label:
                reasons.append("inconsistent_answer")
        except ValueError:
            reasons.append("invalid_structured_answer")
    if row.review.status == "REJECTED":
        reasons.append("review_rejected")
    dimensions = {
        "schema": 1,
        "provenance_and_rights": int(not any("source" in r or "rights" in r for r in reasons)),
        "reference_registry_match": int("unverified_reference" not in reasons),
        "evidence_present": int(bool(row.evidence.strip())),
        "nonempty_answer": int(bool(answer.strip())),
        "technical_correctness": None,
        "remediation_verified": None,
        "clarity_surface": int("anomalous_repetition" not in reasons),
    }
    checked = [v for v in dimensions.values() if v is not None]
    report = {
        "record_hash": content_hash(row),
        "reasons": sorted(set(reasons)),
        "automatic_score": round(sum(checked) / len(checked) * 100, 2),
        "dimensions": dimensions,
        "classification_hint": classify(content),
        "limitations": [
            "Score measures verifiable process dimensions, not technical truth or expert approval"
        ],
    }
    if reasons:
        report["disposition"] = "quarantined"
        return None, report
    row.review.automated_passed = True
    if row.review.status != "EXPERT REVIEWED":
        row.review.status = "EXPERT REVIEW REQUIRED"
    report["disposition"] = (
        "expert_reviewed" if row.review.status == "EXPERT REVIEWED" else "pending_review"
    )
    return row, report


def summarize(rows, reports):
    return {
        "processed": len(reports),
        "structurally_accepted": len(rows),
        "approved_sft": sum(
            r.purpose == "sft" and r.review.status == "EXPERT REVIEWED" for r in rows
        ),
        "pending_review": sum(r.review.status != "EXPERT REVIEWED" for r in rows),
        "rejected": sum(r["disposition"] == "rejected" for r in reports),
        "quarantined": sum(r["disposition"] == "quarantined" for r in reports),
        "reasons": dict(Counter(reason for r in reports for reason in r["reasons"])),
        "domains": dict(Counter(r.domain for r in rows)),
        "languages": dict(Counter(r.language for r in rows)),
        "difficulties": dict(Counter(r.difficulty for r in rows)),
        "purposes": dict(Counter(r.purpose for r in rows)),
    }
