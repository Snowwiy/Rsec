"""Compare local embedding exports without downloading models or interpreting source text."""

from math import isfinite, sqrt

from rsec.datasets.linkage import prompt_text
from rsec.datasets.release import read_candidates, read_reserved
from rsec.errors import RsecError
from rsec.utils import digest, read_json, write_json


def semantic_review(inputs, reserved, vectors, threshold, output):
    candidates = read_candidates(inputs)
    holdouts = read_reserved(reserved)
    if not 0 < threshold <= 1 or len(candidates) * len(holdouts) > 200000:
        raise RsecError("Invalid semantic threshold or comparison budget exceeded")
    package = read_json(vectors)
    if not isinstance(package.get("model"), str) or not isinstance(package.get("revision"), str):
        raise RsecError("Identify the embedding model and its revision")
    prompts = {digest(prompt_text(r)) for r in [*candidates, *holdouts]}
    dimension, matrix = package["dimension"], package["vectors"]
    if type(dimension) is not int or not 1 <= dimension <= 4096 or set(matrix) != prompts:
        raise RsecError("Embedding inventory or dimension mismatch")
    normalized = {}
    for key, vector in matrix.items():
        if len(vector) != dimension or any(
            type(v) not in (int, float) or not isfinite(v) for v in vector
        ):
            raise RsecError("Invalid embedding components")
        scale = max(abs(v) for v in vector)
        if not scale:
            raise RsecError("Zero embedding")
        scaled = [v / scale for v in vector]
        norm = sqrt(sum(v * v for v in scaled))
        normalized[key] = [v / norm for v in scaled]
    pairs = []
    if len(candidates) * len(holdouts) * dimension > 30_000_000:
        raise RsecError("Semantic operation budget exceeded")
    for row in candidates:
        query = normalized[digest(prompt_text(row))]
        for held in holdouts:
            item = normalized[digest(prompt_text(held))]
            score = min(1.0, sum(a * b for a, b in zip(query, item, strict=True)))
            if score >= threshold:
                pairs.append({"candidate_id": row.id, "reserved_id": held.id, "cosine": score})
    report = {
        "model": package["model"],
        "revision": package["revision"],
        "embedding_export_sha256": digest(package),
        "threshold": threshold,
        "possible_links": pairs,
        "status": "HUMAN REVIEW REQUIRED",
    }
    write_json(output, report)
    return report
