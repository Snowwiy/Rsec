# Handoff — Rsec v0.2.0-alpha, Phase 02

**DATASET READINESS: FAIL** for an approved SFT release. **TRAINING READINESS: NOT READY.** Infrastructure implemented/tested and available for review; zero expert-approved SFT and zero independent expert gold. No specialized model, paid services or merge.

## Authoritative state and publication

[Draft dependent PR #2](https://github.com/Snowwiy/Rsec/pull/2), branch `feat/rsec-dataset-engineering-v0.2.0`, based exactly on PR #1 audited head `758896318f106a3c48f3f73860bf329881d264ec`. PR #1 remains open/draft toward dev; main/dev remain at `f42f893948cc2388d4025920d545e4dcc74cf5a9` at inspection. Feature code `849f0053bf3443b8d270945da9bdcaac6665667a`, tree `5470aefa8422c971c842c702ee7629c44b1d0f5b`. Scanner correction `cb3d2d639ed99a0c8f16291353553fe734f224cb`, tree `81a032f9ae7052ffe1a6d3e56f5e973f9fc3e94c`. Cloud commits use expected-head, non-force updates and equality against the locally tested Git tree; local verification commit IDs can differ by author/time.

All three corrected code head workflows passed: [CPU45908654504](https://github.com/Snowwiy/Rsec/actions/runs/45908654504), [offline ML45908654526](https://github.com/Snowwiy/Rsec/actions/runs/45908654526), [security45908654641](https://github.com/Snowwiy/Rsec/actions/runs/45908654641). Inspect final reporting-head CI as well. Initial security CI failed on public tokenizer hashes; narrow path AND exact-hash exceptions fixed it, and a synthetic negative scanner control still rejects another value in the same file.

First read AGENTS.md, DATASET_ENGINEERING_REPORT.md, DATASET_CARD.md, DATASET_QUALITY_REPORT.md, BENCHMARK_REPORT.md, TRAINING_READINESS.md, TEST_RESULTS.md and REVIEW_BEFORE_MERGE.md. Historical Phase 01-B audit/GPU reports remain applicable; their old dataset counts are historical. Notebook pins intentionally remain on audited Phase 01 CPU/GPU infrastructure; Phase 02 data commands are documented in the checkout, not silently added to unexecuted provider notebooks.

## What exists and what does not

Registry 22 = 20 verified external locations + 2 internal fixture sources. Policy APPROVED 3/REVIEW REQUIRED 18/RESTRICTED 1/REJECTED 0. External SFT approved 0. Three pinned official CVE documents, 66,108 bytes, fetched through the authorized GitHub connector, matched to official blob IDs and frozen SHA-256. Native direct DNS failed; subsequent registry cache verification passed without DNS. Raw payloads and 3 reference indexes remain ignored, not redistributed. Their hashes/source identity are public sanitized evidence.

Pilot 64 = 32 controlled scenarios × EN/ES, 8 per domain, 32 EN/32 ES, 32 fundamental/32 intermediate. Benchmark 32 = 15 families, 4 per domain, 16 EN/16 ES, 22 development/10 regression, labels 10 vulnerable/10 benign/12 insufficient. All 96 conversations await real expert review. Reference interpretation pending 3; total 99 unique processed/99 pending, 0 approved/0 rejected/0 quarantined. No private gold. No train/eval/test SFT files. The 500–1,000 quality-conditional target is unmet, not padded.

Candidate schema/quality, source rights/references, metadata-only quarantine, immutable policy snapshots, complete inventory validation, explicit human ledger, group/code/translation leakage guards, reviewed-only SFT bridge, actual tokenizer stats, CLI and public rubric scaffolding are implemented. Legacy prepare supports existing fixtures; it is not Phase 02 expert promotion. `rubric-score` reviews cases, not output-bound comparative model ratings. No semantic truth detector or dynamic remediation runner exists.

## Reproduction

Use Python 3.12 and `requirements-dev.txt -e .` for core. Run `pytest -m 'not ml'`, Ruff, repository validation and build. Real tiny CPU ML additionally requires the official `torch==2.8.0+cpu` wheel and `requirements-cpu-test.lock`; run `HF_HUB_OFFLINE=1 pytest --cov=rsec`. Actual final 200 passed/94.02%; no-Torch core 189 passed/11 deselected. No prior tests removed. Detailed commands/evidence in TEST_RESULTS.md and audits/phase02/validation.json.

```bash
rsec data sources
rsec data download --registered
rsec data curate --input data/pilot/candidates.jsonl --output data/processed/new-pilot --version pilot-0.2.0
rsec data validate data/processed/new-pilot
rsec data review data/processed/new-pilot --output reports/new-review.json
rsec benchmark validate
rsec benchmark contamination-check --input data/pilot/candidates.jsonl
```

Choose new output paths. Split correctly blocks without actual decisions. The pilot generator reproduces input bytes; two fresh pilot bundles had manifest SHA-256 `764a04ba9506a660ef8b254941ad93280c5f737bff6272dd050a1c04951973af`. Existing reviewed local tokenizer measured 16,114 conversation tokens, mean 251.78/max 414, eligible tokens/epoch 0. Local tokenizer files/weights are not committed; a fresh checkout can inspect recorded identities or supply its own reviewed materialized tokenizer. Whitespace counts are not tokenizer counts.

## Next agent / integration

Obtain actual qualified bilingual review, externally authorized SFT sources and independent expert-authored/adjudicated gold. Do not invent reviewer identities or copy temporary pytest attestations. Keep final evaluator content and private review records outside Git. Add prediction/model hash binding before using human rubric scores for comparative model approval. Add deliberate source adapters and semantic/cross-shard checks before scale. Follow the 11 Phase 03 steps in TRAINING_READINESS.md only after data gates and separate authorization.

Keep the primary audited PyTorch/Transformers/PEFT/TRL/BitsAndBytes/Accelerate path. Unsloth 2026.11.12 remains BLOCKED by Transformers/TRL/datasets conflicts; pins/training code unchanged. Physical NF4/QLoRA 4070,3060, DDP/FSDP, FP16/BF16, OOM/resume, WSL2/Linux and provider sessions remain pending. Two 12 GB cards are separate allocations, not a contiguous 24 GB pool. Historical tiny CPU GGUF success does not establish future specialization quality.

Integrate only after human review: merge PR #1 into dev, verify audited ancestry/content, retarget PR #2 to dev and rerun checks. If #1 is squashed/rebased, compare content and resolve with a normal merge commit where needed; do not force push/discard work. PR #2 currently targets the foundation branch to avoid duplicating Phase 01 differences. No automatic merge is authorized.
