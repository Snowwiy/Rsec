"""Append-only experiment records and immutable local model registration."""

import csv
import json
import math
import uuid
from pathlib import Path

from rsec.errors import RsecError
from rsec.utils import atomic_write, confined, identifier, now, read_json, sha256, write_json


class Experiment:
    def __init__(self, root, metadata, run_id=None):
        self.id = identifier(run_id or f"run-{uuid.uuid4().hex[:16]}")
        self.path = confined(root, self.id)
        self.path.mkdir(parents=True, exist_ok=False)
        self.metadata = {"id": self.id, "created_at": now(), "status": "running", **metadata}
        write_json(self.path / "run.json", self.metadata)

    def log(self, metrics):
        # Call only on world process zero. Do not log prompts or source records.
        with (self.path / "metrics.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": now(), **metrics}) + "\n")

    def finish(self, status, **details):
        self.metadata.update(status=status, finished_at=now(), **details)
        write_json(self.path / "run.json", self.metadata, overwrite=True)
        rows = (
            [json.loads(line) for line in (self.path / "metrics.jsonl").read_text().splitlines()]
            if (self.path / "metrics.jsonl").exists()
            else []
        )
        import io

        output = io.StringIO()
        fields = sorted({k for r in rows for k in r})
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        atomic_write(self.path / "metrics.csv", output.getvalue(), overwrite=True)
        atomic_write(
            self.path / "summary.md",
            f"# {self.id}\n\nStatus: {status}\n\nMetric observations: {len(rows)}. See metrics.csv.\n",
            overwrite=True,
        )
        losses = [
            (float(r["step"]), float(r["loss"]))
            for r in rows
            if isinstance(r.get("loss"), (int, float))
            and isinstance(r.get("step"), (int, float))
            and math.isfinite(r["loss"])
        ]
        if losses:
            xmax = max(x for x, _ in losses) or 1
            ymin, ymax = min(y for _, y in losses), max(y for _, y in losses)
            span = ymax - ymin or 1
            points = " ".join(
                f"{50 + x / xmax * 500:.2f},{250 - (y - ymin) / span * 200:.2f}" for x, y in losses
            )
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300"><rect width="600" height="300" fill="white"/><path d="M50 30V250H570" fill="none" stroke="black"/><polyline points="{points}" fill="none" stroke="#1565c0" stroke-width="2"/><text x="50" y="20">Observed training loss: {ymin:.4g} to {ymax:.4g}</text><text x="260" y="285">Optimizer step</text></svg>\n'
            atomic_write(self.path / "loss.svg", svg, overwrite=True)


def list_runs(root="experiments"):
    return [read_json(p) for p in sorted(Path(root).glob("run-*/run.json"))]


class Registry:
    def __init__(self, root="models/registry"):
        self.root = Path(root)

    def register(self, metadata):
        required = {
            "id",
            "rsec_version",
            "base_model",
            "revision",
            "architecture",
            "adapters",
            "config",
            "dataset_hash",
            "trained_at",
            "hardware",
            "commit",
            "metrics",
            "license",
            "artifacts",
            "validation",
            "compatibility",
            "limitations",
        }
        if not required.issubset(metadata):
            raise RsecError(f"Missing model metadata: {sorted(required - metadata.keys())}")
        if not metadata["artifacts"]:
            raise RsecError("Cannot register nonexistent weights")
        artifacts = []
        for name in metadata["artifacts"]:
            path = Path(name).resolve(strict=True)
            artifacts.append(
                {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            )
        path = confined(self.root, identifier(metadata["id"]) + ".json")
        write_json(path, {**metadata, "artifacts": artifacts})
        return {"id": metadata["id"], "record": str(path)}

    def list(self):
        return [read_json(p) for p in sorted(self.root.glob("*.json")) if p.name != "active.json"]

    def activate(self, model_id):
        record = read_json(confined(self.root, identifier(model_id) + ".json"))
        if record["validation"] != "TESTED":
            raise RsecError("Activation requires recorded independent validation")
        for item in record["artifacts"]:
            if sha256(item["path"]) != item["sha256"]:
                raise RsecError("Model integrity mismatch")
        write_json(
            self.root / "active.json", {"id": model_id, "activated_at": now()}, overwrite=True
        )
        return {"active": model_id}
