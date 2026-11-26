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
        path = Path(name)
        assert path.stat().st_size < 1024 * 1024, f"Heavy artifact in Git: {name}"
        assert path.suffix not in {".gguf", ".safetensors", ".pt", ".bin"}, name
    print(
        "Repository configurations, samples, notebook code, workflow pins and artifact limits passed."
    )


if __name__ == "__main__":
    main()
