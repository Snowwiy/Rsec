# Rsec Phase 02 dataset engineering report

Date: 2026-11-26 · version: v0.2.0-alpha · [dependent draft PR #2](https://github.com/Snowwiy/Rsec/pull/2).

**DATASET READINESS: FAIL** for releasing an approved SFT corpus. **TRAINING READINESS: NOT READY.** The implemented infrastructure is available for code review; the approved corpus and independent expert gold exit criteria are unmet. The pilot size goal is not met and no low-quality padding was generated to meet it. No specialized model was trained.

## Starting state and implemented scope

PR #1 was verified open/draft at `758896318f106a3c48f3f73860bf329881d264ec`, with dev/main still at `f42f893948cc2388d4025920d545e4dcc74cf5a9`. The 97-test / 91.34% audited baseline was reproduced before changes. Phase 02 branches from that audited head. Published feature code: `849f0053bf3443b8d270945da9bdcaac6665667a`, tree `5470aefa8422c971c842c702ee7629c44b1d0f5b`; narrow scanner configuration correction: `cb3d2d639ed99a0c8f16291353553fe734f224cb`.

Implemented: 1.0.0 taxonomy, conservative source/license registry, bounded pinned acquisition, CVE reference normalization, Candidate v2, deterministic bilingual draft generation, quality checks, metadata-only quarantine, provenance/translation/code/lexical linkage, hash-bound human review ledgers, immutable policy-snapshotted curation, reviewed-only SFT bridge, local tokenizer statistics, public development/regression scaffold, domain rubrics and CLI. Training stack, optimization code, model exports and original dependency pins remain unchanged.

Not complete: 500–1,000 expert-reviewed pilot, external SFT rights approval, independent expert gold/private final evaluation, semantic multilingual deduplication, authenticated expert identity, model-output-bound rubric ratings, dynamic remediation validation, bulk source-specific adapters, full RAG and real GPU validation. Configuration support is not physical validation.

## Actual data accounting

| Purpose | Unique processed | Expert approved | Pending technical review | Rejected | Quarantined |
|---|---:|---:|---:|---:|---:|
| Intended SFT candidates | 64 | 0 | 64 | 0 | 0 |
| Public development / regression candidates | 32 | 0 | 32 | 0 | 0 |
| Acquired CVE reference indexes | 3 | 0 | 3 interpretations | 0 | 0 |
| Total | **99** | **0** | **99** | **0** | **0** |

The 96 conversations need human expert review; the other three are reference metadata, not candidate answers. Repeated validation runs, old 12 sample conversations, old 10 benchmark fixtures and negative pytest inputs are not counted as new corpus rows. No SFT train/eval/test release exists: actual counts 0/0/0. No private gold exists or was published.

20 external source locations were verified, plus 2 internal sources. APPROVED 3 / REVIEW REQUIRED 18 / RESTRICTED 1 / REJECTED 0. Approval is scoped; **external sources approved for SFT: 0**. Only three CVE JSON files (66,108 bytes) were fetched using the authorized GitHub connector and matched to official pinned blob IDs. Raw payloads are not versioned. Native HTTPS failed DNS; cached registry acquisition was tested successfully without DNS. See [sources](docs/DATASET_SOURCES.md) and [rights](docs/LICENSE_MATRIX.md).

## Distribution and reproducibility

Each of eight domains has 8 pilot and 4 benchmark cases; three knowledge indexes additionally belong to Vulnerability Management. Pilot: 32 EN/32 ES, 32 fundamental/32 intermediate, no advanced/expert. Benchmark: 16 EN/16 ES, 15 families, 22 development and 10 regression cases. Advisory proportions remain future targets. Python/JavaScript examples do not establish coverage of the other configured programming languages.

Pilot input SHA-256: `459b76721ee5472adfe31ad2409b2f7bd64b86408e0a996df3acdb125b4c2077`.
Benchmark input SHA-256: `e0df221dcd9ace29245a12e309f5681c9e5631b917cbdea812ff0f084e987180`.
Two fresh curation bundles with identical inputs/version/seed produced identical manifest SHA-256: `764a04ba9506a660ef8b254941ad93280c5f737bff6272dd050a1c04951973af`. Acquisition observation times are separate from deterministic curation identity. Fixtures are byte-reproduced by the generator in tests; UTF-8/LF is explicit.

```bash
rsec data sources
rsec data pilot --output data/interim/pilot-rebuilt.jsonl
rsec data pilot --benchmark --output data/interim/benchmark-rebuilt.jsonl
rsec data curate --input data/pilot/candidates.jsonl --output data/processed/pilot-rebuild --version pilot-0.2.0
rsec data validate data/processed/pilot-rebuild
rsec data quality data/processed/pilot-rebuild
rsec data review data/processed/pilot-rebuild --output reports/pilot-review-packet.json
rsec benchmark validate
rsec benchmark contamination-check --input data/pilot/candidates.jsonl
rsec benchmark export --output reports/development-cases.jsonl
```

These are reproducible equivalents of executed commands using fresh output names. Review packet creation approves zero rows. `data split` correctly rejects the current unreviewed pilot. Default reservation checked 42 cases and found zero linked pilot rows, within the explicitly documented lexical/lineage limits. Same-generator public drafts do not establish independent expert authorship.

## Measurement and tests

Measured using the existing reviewed local Qwen tokenizer and its official chat template, without new model weights: **16,114 conversation tokens**, mean 251.78, median 261.5, p90 279, p95 291.2, p99 381.87, max 414. Zero over-context cases at 1024/2048/4096/8192. **Eligible SFT tokens per epoch: 0.** Serialized pilot records: 155,760 UTF-8 bytes. Bench conversation tokens: 8,006. Length fitting is not a 12 GB VRAM feasibility result. No training time, throughput or GPU memory claim is made.

Final local suite: **200 passed**, 0 failed, 94.02% statement coverage (2,168 / 2,306), core without Torch **189 passed / 11 ML deselected**. All original 97 tests remain. Meaningful additions exercise rights, source/reference revisions, tampered manifests, forged statuses, partial review, translation/code linkage, secrets/PII, invalid schemas, deterministic release, CLI and actual tokenizer/TRL bridge targets. Ruff, build, package consistency and repository checks passed. CPU lock pip-audit reported no known vulnerabilities for auditable entries; the non-PyPI `torch==2.8.0+cpu` entry was skipped and GPU graph is not audited by that command.

Initial code head CI: CPU quality and offline ML passed; security failed on four public tokenizer-checksum false positives. `.gitleaks.toml` retains all default rules and allows only the two exact public SHA-256 matches in the two statistics files, with path AND match conditions. History scan then passed; a temporary synthetic unallowlisted high-entropy value in the same path still fails. No credential was found and no history rewrite was performed. Inspect the final reporting head's three checks before review; [TEST_RESULTS.md](TEST_RESULTS.md) records run evidence.

## Risks, integration and next work

Heuristic privacy/poison/semantic filters miss real attacks and can flag benign material. Unsigned manifests and operator attestations do not authenticate an adversary replacing the trust root. No broad external ingestion or expert technical verification occurred. Current modest controlled scenarios do not measure model capability or real incident performance.

Merge consideration is limited to infrastructure after human review and passing final-head CI. First review/integrate PR #1 into dev, confirm dev contains the audited history, then retarget PR #2 to dev and rerun checks. Preserve ancestry where possible. A squash/rebase integration needs explicit comparison and a normal merge/conflict-resolution commit if histories diverge; do not force push or discard prior work. No automatic merge was performed.

Before Phase 03 obtain actual qualified bilingual reviews, approved source rights and an independently authored/adjudicated final benchmark; grow the pilot only with justified quality. Then follow [TRAINING_READINESS.md](TRAINING_READINESS.md) and [GPU_VALIDATION_PLAN.md](GPU_VALIDATION_PLAN.md). Unsloth remains optional/experimental and blocked by the existing audited version conflict. No paid API/service, specialized training, repository visibility change or private-data publication occurred.
