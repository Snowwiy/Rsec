import hashlib
import io
import sys
import types

import pytest

from rsec import download
from rsec.errors import RsecError
from rsec.utils import read_json


def source(payload):
    return dict(
        reviewed=True,
        license="MIT",
        redistribution="allowed",
        url="https://example.org/data",
        sha256=hashlib.sha256(payload).hexdigest(),
    )


@pytest.mark.parametrize(
    "change", [{"reviewed": "false"}, {"license": "unknown"}, {"sha256": "bad"}]
)
def test_bad_acquisition_metadata_rejected(tmp_path, change):
    with pytest.raises(RsecError):
        download.download_source(
            {**source(b"fixture"), **change}, tmp_path / "out", ["example.org"]
        )


def test_hash_mismatch_never_published_and_invalid_range(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "check_url", lambda *a: None)

    class Response(io.BytesIO):
        status = 200
        headers = {}

    class Opener:
        def open(self, *a, **k):
            return Response(b"wrong bytes")

    monkeypatch.setattr(download.urllib.request, "build_opener", lambda *a: Opener())
    path = tmp_path / "out"
    with pytest.raises(RsecError, match="SHA-256"):
        download.download_source(source(b"expected"), path, [])
    assert not path.exists() and not (tmp_path / "out.part").exists()
    Response.status = 206
    with pytest.raises(RsecError, match="partial"):
        download.download_source(source(b"expected"), path, [])


def test_retries_exhausted_symlinks_and_size(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "check_url", lambda *a: None)
    monkeypatch.setattr(download.time, "sleep", lambda *a: None)
    calls = []

    class Opener:
        def open(self, *a, **k):
            calls.append(1)
            raise OSError("synthetic failure")

    monkeypatch.setattr(download.urllib.request, "build_opener", lambda *a: Opener())
    path = tmp_path / "out"
    with pytest.raises(OSError):
        download.download_source(source(b"fixture"), path, [])
    assert len(calls) == 3
    partial = tmp_path / "out.part"
    partial.symlink_to(tmp_path / "outside")
    with pytest.raises(RsecError, match="Symlink"):
        download.download_source(source(b"fixture"), path, [])
    partial.unlink()
    partial.write_bytes(b"12345")
    monkeypatch.setattr(download, "MAX_BYTES", 4)
    with pytest.raises(RsecError, match="large"):
        download.download_source(source(b"fixture"), path, [])


def test_hf_streaming_is_untrusted_and_bounded(monkeypatch, tmp_path):
    monkeypatch.setitem(
        sys.modules,
        "datasets",
        types.SimpleNamespace(load_dataset=lambda *a, **k: iter([{"text": "fixture"}])),
    )
    out = tmp_path / "data.jsonl"
    result = download.acquire_hf("fixture", "0" * 40, out, "MIT", reviewed=True)
    assert result["records"] == 1
    assert read_json(str(out) + ".provenance.json")["sha256"] == result["sha256"]
    with pytest.raises(RsecError, match="Reviewed"):
        download.acquire_hf("fixture", "main", out, "MIT", reviewed=True)
    monkeypatch.setattr(download, "MAX_BYTES", 1)
    with pytest.raises(RsecError, match="limit"):
        download.acquire_hf("fixture", "0" * 40, tmp_path / "large", "MIT", reviewed=True)
    assert not (tmp_path / "large").exists()
