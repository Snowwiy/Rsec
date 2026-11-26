"""Identity-bound evaluation records. Content is parsed as data and never executed."""

from collections import Counter, defaultdict
from math import isfinite
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from rsec.config import Strict
from rsec.data import load_rows
from rsec.datasets.schema import content_hash
from rsec.errors import RsecError
from rsec.utils import digest, identifier, write_json

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, Field(min_length=1, max_length=24000)]


class Conditions(Strict):
    base_model: str = Field(min_length=1, max_length=200)
    base_revision: str = Field(min_length=1, max_length=200)
    tokenizer_sha256: Hash
    template_sha256: Hash
    suite_sha256: Hash
    system_prompt: Text
    seed: int = Field(strict=True)
    inference: dict[str, str | int | float | bool | None] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def finite_options(self):
        if any(type(value) is float and not isfinite(value) for value in self.inference.values()):
            raise RsecError("Inference configuration requires finite values")
        return self


class Prediction(Strict):
    case_id: str
    case_sha256: Hash
    model_id: str
    model_revision: str = Field(min_length=1, max_length=200)
    adapter_sha256: Hash | None
    artifact_sha256: Hash
    sample: int = Field(strict=True, ge=0, le=999)
    conditions: Conditions
    response: Annotated[
        str, StringConstraints(min_length=1, max_length=24000, strip_whitespace=False)
    ]
    response_sha256: Hash

    @model_validator(mode="after")
    def valid_response(self):
        identifier(self.case_id)
        identifier(self.model_id)
        if self.response_sha256 != digest(self.response):
            raise RsecError("Response checksum does not match")
        return self

    def fingerprint(self):
        return digest(self.model_dump())


class Rating(Strict):
    prediction_sha256: Hash
    rubric_sha256: Hash
    evaluator: str
    method: Literal["ai_assisted", "human", "independent_adjudication"]
    evidence: Text
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    scores: dict[str, Annotated[int, Field(strict=True, ge=0, le=2)]] = Field(min_length=1)
    status: Literal["draft", "reviewed"]

    @model_validator(mode="after")
    def valid_evaluator(self):
        identifier(self.evaluator)
        if self.method == "ai_assisted" and self.status != "draft":
            raise RsecError("AI-assisted ratings must remain drafts")
        return self


class UnitEvidence(Strict):
    prediction_sha256: Hash
    harness_sha256: Hash
    results: dict[str, Annotated[bool, Field(strict=True)]] = Field(min_length=1)


def load_predictions(paths, cases, suite_hash):
    predictions = {}
    profiles = {}
    observed = set()
    for path in paths:
        for raw in load_rows(path):
            p = Prediction.model_validate(raw)
            if p.case_sha256 != cases.get(p.case_id) or p.conditions.suite_sha256 != suite_hash:
                raise RsecError("Prediction case or suite changed")
            profile = (
                p.model_revision,
                p.adapter_sha256,
                p.artifact_sha256,
                digest(p.conditions.model_dump()),
            )
            if profiles.setdefault(p.model_id, profile) != profile:
                raise RsecError("Mixed versions or inference conditions within one model")
            key = (p.model_id, p.case_id, p.sample)
            if key in observed:
                raise RsecError("Duplicate prediction sample")
            observed.add(key)
            predictions[p.fingerprint()] = p
    if not predictions or len({profile[-1] for profile in profiles.values()}) != 1:
        raise RsecError("Predictions require one comparable set of inference conditions")
    return predictions


def score_ratings(predictions, ratings, rubric, dimensions):
    scores = defaultdict(list)
    seen = set()
    for raw in load_rows(ratings):
        rating = Rating.model_validate(raw)
        p = predictions.get(rating.prediction_sha256)
        if p is None or rating.rubric_sha256 != digest(rubric):
            raise RsecError("Rating does not match the prediction or rubric revision")
        key = (rating.prediction_sha256, rating.evaluator)
        if key in seen:
            raise RsecError("Duplicate evaluator for prediction")
        seen.add(key)
        weight = dimensions[p.case_id]
        if set(weight) != set(rating.scores):
            raise RsecError("Rating dimensions do not match rubric")
        value = sum(weight[k] * rating.scores[k] for k in weight) / (2 * sum(weight.values()))
        bucket = (p.model_id, rating.method, rating.status)
        scores[bucket].append(
            {
                "prediction_sha256": rating.prediction_sha256,
                "case_id": p.case_id,
                "evaluator": rating.evaluator,
                "evidence": rating.evidence,
                "date": rating.date,
                "scores": rating.scores,
                "normalized_score": value,
            }
        )
    return [
        {
            "model_id": model,
            "method": method,
            "status": state,
            "ratings": ratings,
            "mean": sum(r["normalized_score"] for r in ratings) / len(ratings),
        }
        for (model, method, state), ratings in sorted(scores.items())
    ]


def score_codebench(suite, paths, unit_results, harness_hash, k_values, output, ratings=None):
    from rsec.datasets.software import load_codebench, pass_at_k
    from rsec.utils import sha256

    cases = {c.id: c for c in load_codebench(suite)}
    predictions = load_predictions(
        paths, {c.id: digest(c.model_dump()) for c in cases.values()}, sha256(suite)
    )
    evidence = {}
    for raw in load_rows(unit_results):
        record = UnitEvidence.model_validate(raw)
        pred = predictions.get(record.prediction_sha256)
        if (
            pred is None
            or record.harness_sha256 != harness_hash
            or record.prediction_sha256 in evidence
        ):
            raise RsecError("Unit evidence does not match a unique response and harness")
        if set(record.results) != set(cases[pred.case_id].unit_checks):
            raise RsecError("Missing or unexpected unit assertions")
        evidence[record.prediction_sha256] = record
    unit_cases = {c.id for c in cases.values() if c.unit_checks}
    if not unit_cases or not k_values or any(k < 1 for k in k_values):
        raise RsecError("Functional cases and positive k are required")
    samples = defaultdict(set)
    passed = Counter()
    assertions = Counter()
    total = Counter()
    for fingerprint, pred in predictions.items():
        if pred.case_id in unit_cases:
            if fingerprint not in evidence:
                raise RsecError("Missing unit evidence for a functional prediction")
            key = (pred.model_id, pred.case_id)
            observed = evidence[fingerprint].results.values()
            samples[key].add(pred.sample)
            passed[key] += all(observed)
            assertions[pred.model_id] += sum(observed)
            total[pred.model_id] += len(observed)
    models = {p.model_id for p in predictions.values()}
    coverage = [{c: samples[model, c] for c in unit_cases} for model in sorted(models)]
    if any(
        not values or values != coverage[0][c] for model in coverage for c, values in model.items()
    ):
        raise RsecError("Functional metrics require all cases and matched sample budgets")
    code_rubric = {
        "version": "codebench-1",
        "weights": {"problem_solving": 3, "correctness": 3, "maintainability": 2, "security": 2},
    }
    report = {
        "kind": "Rsec-CodeBench",
        "conditions_sha256": digest(next(iter(predictions.values())).conditions.model_dump()),
        "functional_cases": len(unit_cases),
        "results": {
            model: {
                "unit_assertions_passed": assertions[model],
                "unit_assertions_total": total[model],
                "unit_assertion_rate": assertions[model] / total[model],
                "pass_at_k": {
                    str(k): sum(
                        pass_at_k(len(samples[model, c]), passed[model, c], k) for c in unit_cases
                    )
                    / len(unit_cases)
                    if all(len(samples[model, c]) >= k for c in unit_cases)
                    else None
                    for k in sorted(set(k_values))
                },
            }
            for model in sorted(models)
        },
        "rubric": code_rubric,
        "ratings": score_ratings(
            predictions, ratings, code_rubric, dict.fromkeys(cases, code_rubric["weights"])
        )
        if ratings
        else [],
        "evidence_source": "operator-imported unit results; this scorer does not execute or authenticate the harness",
    }
    write_json(output, report)
    return report


def score_cyber_ratings(suite, paths, ratings, rubric_path, output):
    from rsec.datasets.benchmark import validate
    from rsec.datasets.release import read_candidates
    from rsec.utils import read_json, sha256

    validate(suite)
    cases = read_candidates([suite])
    predictions = load_predictions(paths, {r.id: content_hash(r) for r in cases}, sha256(suite))
    rubric = read_json(rubric_path)
    dimensions = {r.id: rubric["domains"][r.domain] for r in cases}
    report = {
        "suite": "Rsec-CyberBench",
        "rubric_sha256": digest(rubric),
        "ratings": score_ratings(predictions, ratings, rubric, dimensions),
    }
    write_json(output, report)
    return report
