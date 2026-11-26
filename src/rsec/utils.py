"""Bounded reads, content hashes, confined paths and atomic output."""

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from rsec.errors import RsecError

MAX_BYTES = 64 * 1024 * 1024


def now():
    return datetime.now(UTC).isoformat()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bounded_read(path, limit=MAX_BYTES):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise RsecError(f"File exceeds {limit} bytes")
    return data.decode("utf-8")


def confined(root, relative):
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or target == root:
        raise RsecError("Path must remain below its configured root")
    return target


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", value) or value in {".", ".."}:
        raise RsecError("Invalid identifier")
    return value


def atomic_write(path, content, overwrite=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".rsec-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)  # atomic no-clobber, including concurrent writers
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_json(path, value, overwrite=False):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", overwrite)


def read_json(path):
    return json.loads(bounded_read(path))


def jsonl(path, rows):
    atomic_write(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
