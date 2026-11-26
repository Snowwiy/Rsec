"""Generate structured benchmark predictions through local inference only."""

import json

from rsec.data import load_rows
from rsec.inference import infer
from rsec.utils import jsonl


def predict(benchmark, model, output, backend="transformers", adapter=None, max_tokens=256):
    rows = []
    instruction = "Return ONLY a JSON object with label (vulnerable, benign or insufficient), cwe (array of justified CWE identifiers), references (array of provided evidence references), and answer (string). Do not invent references.\n\n"
    for case in load_rows(benchmark):
        result = infer(
            model,
            instruction + case["prompt"],
            backend=backend,
            adapter=adapter,
            max_tokens=max_tokens,
            temperature=0,
        )
        try:
            answer = json.loads(result["answer"])
            if not isinstance(answer, dict):
                answer = {}
        except json.JSONDecodeError:
            answer = {}
        # Malformed output is recorded as a schema failure, never silently repaired to correctness.
        rows.append(
            {
                **answer,
                "id": case["id"],
                "latency_seconds": result["latency_seconds"],
                "tokens_per_second": result["tokens_per_second"],
                "vram_bytes": result["vram_bytes"],
            }
        )
    jsonl(output, rows)
    return {"predictions": len(rows), "output": output, "model": model}
