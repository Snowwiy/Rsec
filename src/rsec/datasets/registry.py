"""Source-specific permissions, pinned acquisition and offline reference validation."""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from rsec.config import Strict
from rsec.data import SECRET
from rsec.datasets.schema import Reference, https_url
from rsec.download import download_source
from rsec.errors import RsecError
from rsec.utils import confined, identifier, now, read_json, sha256, write_json


class Source(Strict):
    id: str
    name: str = Field(min_length=1, max_length=200)
    url: str
    organization: str
    version: str
    published_at: str | None = None
    checked_at: str
    acquired_at: str | None = None
    license: str
    license_url: str
    public_access: bool = Field(strict=True)
    download_allowed: bool = Field(strict=True)
    training_allowed: bool = Field(strict=True)
    redistribution_allowed: bool = Field(strict=True)
    training_conditions: str
    redistribution_conditions: str
    restrictions: str
    format: str
    quality_estimate: str
    domains: list[str]
    status: Literal["APPROVED", "REVIEW REQUIRED", "RESTRICTED", "REJECTED"]
    review_method: str
    intended_uses: list[Literal["sft", "knowledge", "rag", "benchmark", "regression"]]
    references: list[Reference] = Field(default_factory=list)
    identifiers: list[str] = Field(default_factory=list)
    snapshot_sha256: str | None = Field(None, pattern=r"^[0-9a-f]{64}$")
    snapshots: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def rights(self):
        identifier(self.id)
        https_url(self.url)
        https_url(self.license_url)
        if any(r.source_id != self.id for r in self.references):
            raise RsecError("Reference owner mismatch")
        if self.status == "APPROVED" and self.license.strip().lower() in {
            "",
            "unknown",
            "unverified",
            "none",
        }:
            raise RsecError("Unknown source license cannot be approved")
        if self.status != "APPROVED" and self.training_allowed:
            raise RsecError("Unapproved sources cannot authorize training")
        return self


class Registry:
    def __init__(self, path="data/manifests/source_registry.json"):
        self.path = Path(path)
        raw = read_json(path)
        if raw.get("schema_version") != 1:
            raise RsecError("Unknown source registry schema")
        sources = [Source.model_validate(r) for r in raw["sources"]]
        self.sources = {r.id: r for r in sources}
        if len(self.sources) != len(sources):
            raise RsecError("Duplicate source IDs")
        refs = [r.id for s in sources for r in s.references]
        if len(refs) != len(set(refs)):
            raise RsecError("Duplicate reference IDs")
        self.hash = sha256(path)

    def get(self, source_id):
        if source_id not in self.sources:
            raise RsecError("Unregistered source")
        return self.sources[source_id]

    def permission(self, source_id, purpose):
        s = self.get(source_id)
        return (
            s.status == "APPROVED"
            and purpose in s.intended_uses
            and (purpose != "sft" or s.training_allowed)
        )

    def reference(self, ref):
        source = self.get(ref.source_id)
        return any(ref.model_dump() == r.model_dump() for r in source.references)

    def summary(self):
        from collections import Counter

        return {
            "sources": len(self.sources),
            "states": dict(Counter(s.status for s in self.sources.values())),
            "registry_sha256": self.hash,
            "items": [s.model_dump() for s in self.sources.values()],
        }


def acquire_registry(
    config="configs/datasets.yaml",
    output="data/raw",
    registry="data/manifests/source_registry.json",
):
    import yaml

    from rsec.utils import bounded_read

    settings = yaml.safe_load(bounded_read(config))
    if not isinstance(settings, dict):
        raise RsecError("Dataset config must be a mapping")
    catalog = Registry(registry)
    results = []
    # The legacy source contract remains valid; new entries bind to registry permissions.
    for entry in settings.get("registered_sources", []):
        source = catalog.get(entry["source_id"])
        if source.status != "APPROVED" or not source.download_allowed:
            raise RsecError("Source rights block acquisition")
        if source.version != entry["revision"] or entry["sha256"] != source.snapshots.get(
            Path(entry["filename"]).name
        ):
            raise RsecError("Acquisition revision/hash differs from source registry")
        from rsec.datasets.quality import pii

        if SECRET.search(entry["url"]) or pii(entry["url"], catalog):
            raise RsecError("Sensitive source URL rejected")
        destination = confined(output, entry["filename"])
        contract = {
            "url": entry["url"],
            "sha256": entry["sha256"],
            "reviewed": True,
            "license": source.license,
            "redistribution": source.redistribution_conditions,
        }
        # Verified cache reads must not require DNS/network in an offline environment.
        from urllib.parse import urlsplit

        https_url(entry["url"])
        if urlsplit(entry["url"]).hostname not in settings["allowed_hosts"]:
            raise RsecError("Acquisition host is not allowlisted")
        if destination.exists():
            if sha256(destination) != entry["sha256"]:
                raise RsecError("Cached source integrity mismatch")
            result = {"status": "cached", "sha256": entry["sha256"]}
        else:
            result = download_source(contract, destination, settings["allowed_hosts"])
        write_json(
            str(destination) + ".provenance.json",
            {
                "source_id": source.id,
                "revision": source.version,
                "sha256": sha256(destination),
                "registry_hash": catalog.hash,
                "acquired_at": source.acquired_at if result["status"] == "cached" else now(),
                "verified_at": now(),
                "transport": "local-cache-hash-verified"
                if result["status"] == "cached"
                else "bounded-https",
            },
            overwrite=True,
        )
        results.append({"source_id": source.id, "filename": entry["filename"], **result})
    return {
        "sources": results,
        "registry_sha256": catalog.hash,
        "network_requests_needed": sum(r["status"] != "cached" for r in results),
    }
