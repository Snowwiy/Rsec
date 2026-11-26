import pytest

from rsec.data import load_rows
from rsec.knowledge import ingest
from rsec.utils import read_json


def test_knowledge_is_not_implicitly_supervised(tmp_path):
    path = tmp_path / "authorized.md"
    path.write_text(
        "La seguridad de una aplicación requiere validar los datos y preservar evidencia."
    )
    output = tmp_path / "knowledge.jsonl"
    result = ingest(
        [path], output, "owner", "https://example.org/doc", "MIT", "1", "allowed", reviewed=True
    )
    assert result["records"] == 1
    row = list(load_rows(output))[0]
    assert row["purpose"] == "knowledge"
    assert row["language"] == "es"
    assert row["trusted"] is False
    assert read_json(str(output) + ".manifest.json")["records"] == 1
    with pytest.raises(ValueError, match="license"):
        ingest(
            [path], tmp_path / "other", "owner", "https://example.org/doc", "MIT", "1", "allowed"
        )


def test_sensitive_metadata_rejected(samples, tmp_path):
    from rsec.data import prepare
    from rsec.utils import jsonl

    samples[0]["source"] = "analyst@example.invalid"
    source = tmp_path / "records.jsonl"
    jsonl(source, samples)
    result = prepare([source], tmp_path / "output")
    assert result["reasons"]["sensitive_metadata"] == 1
