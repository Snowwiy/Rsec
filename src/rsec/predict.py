"""Generate structured benchmark predictions through local inference only."""

import json

from rsec.data import load_rows
from rsec.inference import infer
from rsec.utils import digest, jsonl, write_json

INSTRUCTION = "Return ONLY a JSON object with label (vulnerable, benign or insufficient), cwe (array of justified CWE identifiers), references (array of provided evidence references), and answer (string). Do not invent references.\n\n"


def predict(benchmark, model, output, backend="transformers", adapter=None, max_tokens=256):
    rows = []
    templates, systems = set(), set()
    cases = list(load_rows(benchmark))
    for case in cases:
        result = infer(
            model,
            INSTRUCTION + case["prompt"],
            backend=backend,
            adapter=adapter,
            max_tokens=max_tokens,
            temperature=0,
        )
        templates.add(result.get("chat_template_hash"))
        systems.add(result.get("system_hash"))
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
    write_json(
        str(output) + ".meta.json",
        {
            "prediction_hash": digest(rows),
            "benchmark_hash": digest(cases),
            "model": str(model),
            "adapter": str(adapter) if adapter else None,
            "conditions": {
                "instruction_hash": digest(INSTRUCTION),
                "backend": backend,
                "max_tokens": max_tokens,
                "temperature": 0,
                "context": 2048,
                "chat_templates": sorted(t for t in templates if t),
                "system_hashes": sorted(s for s in systems if s),
            },
        },
    )
    return {"predictions": len(rows), "output": output, "model": model}
