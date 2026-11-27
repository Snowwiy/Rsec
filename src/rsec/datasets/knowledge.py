"""CVE JSON becomes reference material, never automatic question/answer gold."""

from pathlib import Path

from rsec.datasets.registry import Registry
from rsec.errors import RsecError
from rsec.utils import jsonl, read_json, sha256, write_json


def normalize_cve(inputs, output, registry_path="data/manifests/source_registry.json"):
    registry = Registry(registry_path)
    source = registry.get("cve-program")
    if not registry.permission(source.id, "knowledge"):
        raise RsecError("CVE reference rights not approved")
    rows = []
    for name in inputs:
        p = Path(name)
        expected = source.snapshots.get(p.name)
        if not expected or sha256(p) != expected:
            raise RsecError("CVE snapshot integrity mismatch")
        raw = read_json(p)
        meta = raw["cveMetadata"]
        identifier = meta["cveId"]
        if identifier not in source.identifiers or meta["state"] != "PUBLISHED":
            raise RsecError("Unverified CVE identifier/state")
        # Keep the untrusted original locally. No model answer is synthesized from it.
        rows.append(
            {
                "id": identifier,
                "taxonomy_version": "1.0.0",
                "domain": "vulnerability_management",
                "subcategory": "advisories",
                "task_type": "reference_document",
                "difficulty": None,
                "document_languages": sorted(
                    {
                        d.get("lang")
                        for d in raw.get("containers", {}).get("cna", {}).get("descriptions", [])
                        if d.get("lang")
                    }
                ),
                "purpose": "knowledge",
                "source_id": source.id,
                "source_revision": source.version,
                "input_sha256": expected,
                "published_at": meta.get("datePublished"),
                "reference_url": "https://www.cve.org/CVERecord?id=" + identifier,
                "trusted": False,
                "sft_eligible": False,
                "redistribution_enabled": False,
                "note": "Local official record exists; content/affected-version interpretation still requires review.",
            }
        )
    if len({r["id"] for r in rows}) != len(rows):
        raise RsecError("Duplicate CVE records")
    jsonl(output, rows)
    write_json(
        str(output) + ".manifest.json",
        {
            "registry_hash": registry.hash,
            "sha256": sha256(output),
            "records": len(rows),
            "purpose": "knowledge",
        },
    )
    return {
        "output": str(output),
        "records": len(rows),
        "sft_eligible": 0,
        "redistributed_payloads": 0,
    }
