"""Validate repository invariants without executing notebooks or source data."""

import ast
import json
import re
import subprocess
from pathlib import Path

import yaml

from rsec.config import load_training
from rsec.data import Record, load_rows


def main():
    for path in Path("configs/profiles").glob("*.yaml"):
        load_training(profile=path.stem)
    for path in Path("configs").rglob("*.yaml"):
        yaml.safe_load(path.read_text())
    for row in load_rows("data/samples/defensive.jsonl"):
        Record.model_validate(row)
    for path in Path("notebooks").glob("*.ipynb"):
        notebook = json.loads(path.read_text())
        assert notebook["nbformat"] == 4
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                assert not cell["outputs"], "Committed notebook outputs are forbidden"
                ast.parse("".join(cell["source"]))
    for path in Path(".github/workflows").glob("*.yml"):
        text = path.read_text()
        assert "pull_request_target" not in text
        assert "contents: read" in text
        for action in re.findall(r"uses:\s*(\S+)", text):
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", action), action
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    for name in filter(None, tracked):
        assert not name.startswith(
            (
                "benchmarks/private/",
                "data/reviews/",
                "data/raw/",
                "data/interim/",
                "data/processed/",
                "data/quarantine/",
                "models/",
                "checkpoints/",
                "exports/",
                "experiments/",
                "reports/",
            )
        ), "Private evaluation/review material is forbidden"
        path = Path(name)
        assert path.stat().st_size < 1024 * 1024, f"Heavy artifact in Git: {name}"
        assert path.suffix not in {".gguf", ".safetensors", ".pt", ".bin", ".pem", ".key"}, name
    from rsec.datasets.benchmark import validate
    from rsec.datasets.registry import Registry
    from rsec.datasets.software import CODEBENCH, codebench_summary

    catalog = Registry()
    Registry("data/manifests/software_source_registry.json")
    codebench_summary(CODEBENCH)
    for name in filter(None, tracked):
        if name.startswith(("data/", "benchmarks/")) and Path(name).suffix == ".jsonl":
            for row in load_rows(name):
                if isinstance(row, dict) and row.get("schema_version") == 2:
                    source = catalog.get(row["source_id"])
                    assert source.status == "APPROVED" and source.redistribution_allowed, (
                        "Restricted source data cannot be versioned publicly"
                    )
    validate()
    print(
        "Repository configurations, samples, notebook code, workflow pins and artifact limits passed."
    )


if __name__ == "__main__":
    main()
