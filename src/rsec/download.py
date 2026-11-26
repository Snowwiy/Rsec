"""Explicitly reviewed HTTPS sources only. No archives or remote code execution."""

import ipaddress
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from rsec.errors import RsecError
from rsec.utils import MAX_BYTES, bounded_read, confined, sha256, write_json


def check_url(url, hosts):
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in hosts
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise RsecError("Only allowlisted credential-free HTTPS sources are permitted")
    for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise RsecError("Private/local network source rejected")


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, request, fp, code, message, headers, url):
        check_url(url, self.hosts)
        return super().redirect_request(request, fp, code, message, headers, url)


def download_source(source, destination, hosts):
    if not source.get("reviewed") or not source.get("license") or not source.get("redistribution"):
        raise RsecError("Review source license and redistribution before acquisition")
    expected = source["sha256"]
    if not re.fullmatch("[0-9a-f]{64}", expected):
        raise RsecError("An independently obtained SHA-256 is required")
    url = source["url"]
    check_url(url, hosts)
    destination = Path(destination)
    if destination.exists():
        if sha256(destination) == expected:
            return {"status": "cached", "sha256": expected}
        raise RsecError("Existing download has unexpected content")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    if partial.is_symlink():
        raise RsecError("Symlink partial download rejected")
    opener = urllib.request.build_opener(SafeRedirect(hosts))
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > MAX_BYTES:
            raise RsecError("Partial download too large")
        headers = {"User-Agent": "Rsec/0.1.0", "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            with opener.open(urllib.request.Request(url, headers=headers), timeout=30) as response:
                resumed = response.status == 206 and response.headers.get(
                    "Content-Range", ""
                ).startswith(f"bytes {offset}-")
                if response.status == 206 and not resumed:
                    raise RsecError("Unexpected partial response")
                if not resumed:
                    offset = 0
                with partial.open("ab" if resumed else "wb") as stream:
                    for chunk in iter(lambda: response.read(64 * 1024), b""):
                        offset += len(chunk)
                        if offset > MAX_BYTES:
                            raise RsecError("Download exceeds 64 MiB")
                        stream.write(chunk)
            if sha256(partial) != expected:
                partial.unlink()
                raise RsecError("Source SHA-256 mismatch")
            # Atomic no-clobber publication.
            import os

            os.link(partial, destination)
            partial.unlink()
            return {"status": "downloaded", "sha256": expected}
        except (OSError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(0.25 * 2**attempt)
    raise RuntimeError("Download failed")


def acquire(config="configs/datasets.yaml", output="data/raw"):
    settings = yaml.safe_load(bounded_read(config))
    results = []
    for source in settings["sources"]:
        path = confined(output, source["filename"])
        result = download_source(source, path, settings["allowed_hosts"])
        from rsec.utils import now

        write_json(
            str(path) + ".provenance.json",
            {**source, "acquired_at": now(), **result},
            overwrite=True,
        )
        results.append(result)
    return {"sources": results, "note": "No network request when sources is empty"}


def acquire_hf(dataset_id, revision, output, license_name, reviewed=False, split="train"):
    """Pinned HF acquisition after explicit license review; exported as untrusted JSONL."""
    if not reviewed or not license_name or not re.fullmatch("[0-9a-f]{40}", revision):
        raise RsecError("Reviewed license and pinned dataset SHA required")
    from datasets import load_dataset

    from rsec.utils import jsonl, now

    rows = []
    total = 0
    for row in load_dataset(dataset_id, revision=revision, split=split, streaming=True):
        import json

        total += len(json.dumps(row).encode())
        if total > MAX_BYTES or len(rows) >= 10000:
            raise RsecError("Dataset exceeds acquisition limit; select a smaller reviewed split")
        rows.append(row)
    jsonl(output, rows)
    write_json(
        str(output) + ".provenance.json",
        {
            "dataset_id": dataset_id,
            "revision": revision,
            "license": license_name,
            "acquired_at": now(),
            "sha256": sha256(output),
        },
    )
    return {"records": len(rows), "sha256": sha256(output)}
