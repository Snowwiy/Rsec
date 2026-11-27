# Rsec-CyberBench report · development 0.1.0

Status: **IMPLEMENTED / structurally TESTED; expert independence and final gold BLOCKED.** No real model performance was measured. A final private suite does not exist and none was published.

| Item | Actual count |
|---|---:|
| Public candidate cases | 32 |
| Connected families | 15 |
| Development / regression | 22 / 10 |
| EN / ES | 16 / 16 |
| Cases per each of 8 domains | 4 |
| Draft labels vulnerable / benign / insufficient | 10 / 10 / 12 |
| Expert-reviewed / private final gold | 0 / 0 |
| Actual model predictions / actual human rubric ratings | 0 / 0 |

`rsec benchmark validate` verifies schema, source/references, draft expected labels, allowed purpose and family-disjoint development/regression partitions. Current benchmark content digest (canonical content hashes): `80c63ac74b7ca54fee0a4f7e4252e4b6ceed9733277ae2a785b7c6c083590a95`. JSONL file SHA-256: `e0df221dcd9ace29245a12e309f5681c9e5631b917cbdea812ff0f084e987180`. These are different hash representations, not conflicting identities.

The 32 candidate cases plus 10 old fixtures form the 42 default training reservations. No known link to 64 pilot candidates was detected under lexical/declared lineage/code checks. This is not a universal semantic independence guarantee. Separate scenario specifications share an authored generator and have no independent human gold review.

Domain-weighted human rubrics, safe/unsafe and ambiguous examples, uncertainty and references are present. Mechanical label/CWE/schema/reference metrics are implemented and tested; actual precision/recall/accuracy/F1/false-positive/false-negative scores for Rsec or the base are **not available**. Semantic hallucinations, remediation success and real category ratings are **not measured**. Temporary test outputs only validate scoring math and malformed-input failures.

`rubric-score` binds case and rubric hashes, validates human-attested integer scores 0..2 and reports coverage; it does not certify expert identity or bind ratings to model outputs. Use only for candidate/reference review until prediction/model bindings are implemented. An average case rating must not be promoted to comparative model accuracy.

For future runs, export with `rsec benchmark export --output reports/cyberbench-cases.jsonl`, then use `rsec predict --benchmark reports/cyberbench-cases.jsonl ...` and the existing comparable-condition `rsec evaluate` gate. All prompts/reference context, model/tokenizer/template revisions and generation settings must match. Public development results can support debugging only. Final blind evaluation requires independent evaluator-held cases outside Git. See [design](docs/BENCHMARK_DESIGN.md) and [contamination policy](docs/BENCHMARK_CONTAMINATION_POLICY.md).
