import pytest

from rsec.download import check_url, download_source


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/data",
        "https://localhost/a",
        "https://user:pass@example.com/a",
        "https://example.com:8080/a",
    ],
)
def test_url_safety(url):
    with pytest.raises(ValueError):
        check_url(url, ["example.com"])


def test_private_dns_resolution_rejected(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="Private"):
        check_url("https://example.com/a", ["example.com"])


def test_download_requires_review(tmp_path):
    with pytest.raises(ValueError, match="Review"):
        download_source(
            {"url": "https://example.com/file", "reviewed": False},
            tmp_path / "out",
            ["example.com"],
        )


def test_resumed_download_and_cache_hash(monkeypatch, tmp_path):
    import hashlib
    import io

    from rsec import download

    payload = b"reviewed defensive source content"
    destination = tmp_path / "source.txt"
    destination.with_suffix(".txt.part").write_bytes(payload[:8])

    class Response(io.BytesIO):
        status = 206
        headers = {"Content-Range": f"bytes 8-{len(payload) - 1}/{len(payload)}"}

    class Opener:
        def open(self, request, timeout):
            assert request.get_header("Range") == "bytes=8-"
            assert timeout == 30
            return Response(payload[8:])

    monkeypatch.setattr(download, "check_url", lambda *a: None)
    monkeypatch.setattr(download.urllib.request, "build_opener", lambda *a: Opener())
    source = {
        "reviewed": True,
        "license": "MIT",
        "redistribution": "allowed",
        "url": "https://example.com/source",
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    assert download.download_source(source, destination, ["example.com"])["status"] == "downloaded"
    assert destination.read_bytes() == payload
    assert download.download_source(source, destination, ["example.com"])["status"] == "cached"
    destination.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="unexpected"):
        download.download_source(source, destination, ["example.com"])
