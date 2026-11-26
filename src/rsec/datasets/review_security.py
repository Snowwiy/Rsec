"""Local review authority and OpenSSL Ed25519 verification."""

import base64
import json
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from rsec.config import Strict
from rsec.datasets.evidence import Hash
from rsec.datasets.review import Decision
from rsec.datasets.schema import content_hash
from rsec.errors import RsecError
from rsec.utils import bounded_read, digest, identifier, read_json, sha256

POLICY = "rsec-review-1"


class Reviewer(Strict):
    id: str
    display_name: str = Field(min_length=1, max_length=120)
    domains: list[str] = Field(min_length=1, max_length=50)
    active: bool = Field(strict=True)
    added_on: date
    fixture: bool = Field(default=False, strict=True)
    public_key: str = Field(min_length=1, max_length=200)
    key_sha256: Hash
    permissions: list[Literal["review", "adjudicate"]] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_id(self):
        identifier(self.id)
        return self


class Event(Strict):
    policy: Literal["rsec-review-1"] = POLICY
    decision: Decision
    revision_sha256: Hash
    domain: str
    action: Literal["approve", "reject", "request_changes", "quarantine", "comment"]
    comments: str = Field(max_length=4000)
    proposed_answer: str | None = Field(None, max_length=24000)

    @model_validator(mode="after")
    def check_action(self):
        if (self.action == "approve") != (self.decision.decision == "approve"):
            raise RsecError("Review action and decision differ")
        if self.action == "approve" and self.proposed_answer:
            raise RsecError("A proposed revision must receive separate review")
        return self


class SignedEvent(Strict):
    event: Event
    key_sha256: Hash
    signature: str = Field(pattern=r"^[A-Za-z0-9+/]{86}==$")


class Reviewers:
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        items = [Reviewer.model_validate(row) for row in read_json(self.path)["reviewers"]]
        self.items = {row.id: row for row in items}
        if len(self.items) != len(items) or len({row.key_sha256 for row in items}) != len(items):
            raise RsecError("Reviewers must have distinct IDs and public keys")

    def authority(self, reviewer_id, domain):
        row = self.items.get(reviewer_id)
        if (
            row is None
            or row.fixture
            or not row.active
            or domain not in row.domains
            or "review" not in row.permissions
        ):
            raise RsecError("Reviewer is not authorized for this domain")
        key = self.path.parent / row.public_key
        if (
            Path(row.public_key).name != row.public_key
            or key.is_symlink()
            or key.stat().st_size > 4096
        ):
            raise RsecError("Public key must be a bounded adjacent PEM file")
        if sha256(key) != row.key_sha256:
            raise RsecError("Reviewer public key changed")
        # DER SubjectPublicKeyInfo prefix for Ed25519, validated before any operation.
        der = openssl(["pkey", "-pubin", "-in", str(key), "-outform", "DER"])
        if len(der) != 44 or der[:12] != bytes.fromhex("302a300506032b6570032100"):
            raise RsecError("Reviewer key must be Ed25519")
        return row, key


def openssl(args):
    binary = shutil.which("openssl")
    if not binary:
        raise RsecError("OpenSSL 3 with Ed25519 support is required")
    result = subprocess.run([binary, *args], capture_output=True, timeout=10, check=False)
    if result.returncode:
        raise RsecError("Ed25519 operation failed")
    return result.stdout


def payload(event):
    return json.dumps(event.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()


def sign(event, reviewers, private_key):
    row, _ = reviewers.authority(event.decision.reviewer_id, event.domain)
    path = Path(private_key)
    if path.is_symlink() or path.stat().st_size > 4096 or not bounded_read(path, 4096):
        raise RsecError("A bounded, materialized private key is required")
    with tempfile.TemporaryDirectory() as directory:
        message = Path(directory) / "message"
        message.write_bytes(payload(event))
        sig = openssl(
            [
                "pkeyutl",
                "-sign",
                "-rawin",
                "-passin",
                "pass:",
                "-inkey",
                str(path.resolve()),
                "-in",
                str(message),
            ]
        )
    signed = SignedEvent(
        event=event, key_sha256=row.key_sha256, signature=base64.b64encode(sig).decode()
    )
    verify(signed, reviewers)
    return signed


def verify(signed, reviewers):
    event = signed.event
    row, key = reviewers.authority(event.decision.reviewer_id, event.domain)
    if (
        signed.key_sha256 != row.key_sha256
        or date.fromisoformat(event.decision.reviewed_at) < row.added_on
    ):
        raise RsecError("Review key or date is inconsistent with registration")
    with tempfile.TemporaryDirectory() as directory:
        message, signature = Path(directory) / "message", Path(directory) / "signature"
        message.write_bytes(payload(event))
        signature.write_bytes(base64.b64decode(signed.signature, validate=True))
        openssl(
            [
                "pkeyutl",
                "-verify",
                "-rawin",
                "-pubin",
                "-inkey",
                str(key),
                "-in",
                str(message),
                "-sigfile",
                str(signature),
            ]
        )
    return signed


def event_id(signed):
    return digest(signed.model_dump(mode="json"))


def bind(event, rows, registry_hash):
    d = event.decision
    row = rows.get(d.record_id)
    if (
        row is None
        or d.record_hash != content_hash(row)
        or event.revision_sha256 != digest([row.id, d.record_hash])
    ):
        raise RsecError("Review event does not match the selected record revision")
    if row.domain != event.domain or d.registry_hash != registry_hash:
        raise RsecError("Review domain or source policy changed")
    return row
