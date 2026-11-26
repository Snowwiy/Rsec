"""Materialize authored per-scenario preaudit notes against the original candidate hashes."""

import json

from rsec.datasets.quality import inspect_candidate
from rsec.datasets.registry import Registry
from rsec.datasets.release import read_candidates
from rsec.datasets.schema import content_hash
from rsec.errors import RsecError
from rsec.utils import jsonl, read_json

NOTES = "audits/phase02b/preaudit_notes.json"


def preaudit(inputs, output, notes_path=NOTES):
    notes = read_json(notes_path)
    rows = read_candidates(inputs)
    original = {
        row.id: content_hash(row)
        for row in read_candidates(
            ["data/pilot/candidates.jsonl", "benchmarks/rsec_cyberbench/development.jsonl"]
        )
    }
    registry = Registry()
    reports = []
    for row in rows:
        if content_hash(row) != original.get(row.id):
            raise RsecError("Preaudit notes apply only to the original frozen record revision")
        label = row.expected_label
        per_case = None
        if row.generation and row.generation.generator_version == "1.0.0":
            slug = row.generation.original_id.split("-")
            if len(slug) == 2 and slug[0] in notes and slug[1].isdigit():
                position = int(slug[1])
                if position < len(notes[slug[0]]):
                    per_case = notes[slug[0]][position]
        if per_case is None:
            raise RsecError("No authored technical preaudit for this candidate")
        _, auto = inspect_candidate(row.model_dump(), registry)
        answer = json.loads(row.messages[-1].content)
        findings = [per_case]
        if row.language == "es":
            findings.append(
                "La pregunta está en español pero parte de la evidencia es inglés. Revisar terminología y equivalencia sin traducir identificadores ni código."
            )
        if row.purpose in {"benchmark", "regression"} and row.generation.original_id not in {
            "bench-000",
            "bench-001",
        }:
            findings.append(
                "La respuesta de referencia es genérica y no documenta la causa específica del caso."
            )
        reports.append(
            {
                "id": row.id,
                "record_sha256": content_hash(row),
                "domain": row.domain,
                "subcategory": row.subcategory,
                "language": row.language,
                "difficulty": row.difficulty,
                "family_ids": row.families,
                "translation_of": row.translation_of,
                "findings": findings,
                "evidence": {
                    "premise": json.loads(row.evidence),
                    "draft_label": label,
                    "draft_answer": answer["answer"],
                    "cwe": row.expected_cwe,
                    "source_rights": registry.get(row.source_id).training_conditions,
                },
                "proposed_corrections": [
                    per_case,
                    "Confirmar dificultad por razonamiento requerido, revisar límites y producir una nueva revisión si cambia el contenido.",
                ],
                "registered_references": [
                    {
                        "id": ref.id,
                        "revision": ref.revision,
                        "registry_match": registry.reference(ref),
                    }
                    for ref in row.references
                ],
                "automatic_validation": {
                    "disposition": auto["disposition"],
                    "reasons": auto["reasons"],
                },
                "recommendation": "human_review_and_revise",
                "status": "PENDING HUMAN DECISION",
                "approval": False,
            }
        )
    jsonl(output, reports)
    return {"records": len(reports), "status": "PENDING HUMAN DECISION", "approvals": 0}
