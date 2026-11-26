# Dataset quality report · Phase 02

**Corpus release verdict: FAIL.** Mechanical validity is implemented; expert technical review remains absent. [Machine-readable current accounting](data/manifests/dataset_readiness.json).

| Observation | Actual result |
|---|---|
| SFT candidates processed / structurally accepted | 64 / 64 |
| Expert-approved SFT | 0 |
| Pending SFT review | 64 |
| Public benchmark/regression candidates / pending | 32 / 32 |
| Knowledge reference indexes / interpretation pending | 3 / 3 |
| Rejected / quarantined in actual corpus | 0 / 0 |
| Real human review decisions / expert gold | 0 / 0 |
| Default reserved cases / linked SFT candidates | 42 / 0 |
| Current SFT train/eval/test | 0 / 0 / 0; no release files |
| Independent reproduced pilot manifest | Identical SHA-256 in two fresh bundles |

All 96 candidate conversations are draft synthetic scenarios and retain expert-review-required states after deterministic checks. The three reference indexes have verified pinned input identity, but no affected-version/content interpretation approval. No negative test, repeated pipeline execution or legacy fixture inflates the 99 unique record count.

## What the automated checks establish

Strict schema/roles/booleans, allowed taxonomy, known source/revision/reference, declared use permission, normalization, duplicate/family/code/translation checks, registered identifier claims, response JSON consistency, length/repetition checks and narrow secret/PII/poison screening passed for the controlled corpus. The 500–1,000 high-quality pilot target is unmet. Its 64 drafts have equal domain/language breadth and fundamental/intermediate difficulty only, rather than the future training proportions.

Process dimensions are inspectable per row in `quality_observations.jsonl` in the ignored immutable curation bundle. Technical correctness and remediation verification are null, not automatically perfect scores. Reference presence and valid URLs are not evidence that an answer follows from its sources. Severity/affected versions, causal reasoning, correct remediation and professional Spanish require expert inspection.

Adversarial tests verify invalid schema/rights/reference rejection, secret/PII quarantine without plaintext, bad attestations, forged expert flags, duplicate reviewers, tampered content/policy/manifests even after checksum recomputation, translation/code overlap, missing/partial reviews and similarity resource limits. The actual SFT bridge/TRL target masks are checked in CPU integration tests using clearly test-only attestations. These do not certify the real corpus.

## Residual blockers

No approved SFT examples or independently expert-authored/adjudicated gold. No externally sourced SFT permission decision. No semantic universal dedupe/translation or hallucination detector. No isolated dynamic remediation runner. Human identities are not authenticated by the local attestation schema. Public development benchmark case-rating aggregation does not yet bind a model prediction. Small scenarios omit advanced/expert code depth and many subcategories/languages. Shared generator authorship prevents claims of independent expert benchmark construction.

Zero quarantine/rejects reflects a small controlled input and does not prove that real untrusted inputs are safe. Rights, privacy, technical review and independence gates remain mandatory even with high test coverage. See [review procedure](docs/DATASET_REVIEW_GUIDE.md).
