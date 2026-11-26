# Handoff — Rsec v0.1.0-alpha, Phase 01-B

Independent audit verdict: **PASS WITH CONDITIONS** for foundation review into `dev`. No merge, specialized training, external billing or infrastructure provisioning was performed. The existing MIT license is unchanged.

## Current authoritative state

Read INDEPENDENT_AUDIT.md, SECURITY_AUDIT.md, MLOPS_VALIDATION.md, GPU_VALIDATION_PLAN.md, DATASET_READINESS.md, TEST_RESULTS.md and REVIEW_BEFORE_MERGE.md. These supersede initial capability assertions where findings A01–A15 apply. AGENTS.md remains the development contract.

Work updates the original PR #1 and branch `feat/rsec-foundation-v0.1.0`, based on its actual initial head `48709e49c2650793f8af792344988552151de158`, not stale dev. Audited code commit published through the authorized GitHub connection: `44084096dc231b7726ca1490c5e65f69a01956f9` (tree `6bd98e7db4c7d9ac05633e1db57fbe6121312929`). Notebook revisions pin that code commit; subsequent reporting commits do not change its implementation. Main/dev were not merged.

The published code's CPU quality, security and offline ML workflows all passed: runs [45901526841](https://github.com/Snowwiy/Rsec/actions/runs/45901526841), [45901526945](https://github.com/Snowwiy/Rsec/actions/runs/45901526945), [45901526883](https://github.com/Snowwiy/Rsec/actions/runs/45901526883). Inspect PR checks for the final documentation head too; prior CI is not a substitute for its checks.

## Corrections and validation

Fixed SFT token-length counting for Transformers' structured default return, benchmark question leakage, missing predict CLI, subset label schemas, regression comparability, adapter/pickle and checkpoint integrity boundaries, CSV multiline handling, sensitive knowledge metadata, strict provenance flags and processing budgets. Experimental FSDP dtype/optimizer choices were corrected against official PEFT guidance. Unsloth 2026.11.12 is **BLOCKED** by confirmed Transformers/TRL/datasets dependency conflicts; its active optional requirement was removed.

Actual local final suite: **97 passed**, **91.34% statement coverage** (initial independently reproduced: 39 / 75.15%). Core environment with no torch: **88 passed**, 9 ML tests explicitly deselected. Real CPU tests inspect TRL labels/padding/loss, optimizer step 2 → 3, tamper rejection, merged logits, offline generation and scoring. Native Q4_K_M conversion/template/generation were repeated; the resulting hash matches historical evidence. Optional runtime contract tests use doubles and do not demonstrate those engines running.

## Reproduce

From checkout root, use a clean Python 3.12 venv for core; install `requirements-dev.txt -e .`, then run `pytest -m 'not ml'`, Ruff, repository validation and build. For real tiny ML install official `torch==2.8.0+cpu` then `requirements-cpu-test.lock` and run `HF_HUB_OFFLINE=1 pytest --cov=rsec`. Full commands/results are in TEST_RESULTS.md. Do not use the CPU lock for CUDA.

The native script accepts `--tokenizer /local/reviewed-tokenizer` to work without HF cache/network. Use a new output directory and clean pinned llama.cpp checkout. Existing heavy artifacts remain ignored and are not required to clone the code. Materialize HF inference/export bases with snapshot_download(local_dir=...), because local model guards reject cache symlinks.

## Gates and next work

Fase 02 can start source-specific rights review, bilingual curation and independently reviewed frozen gold benchmarks. No real corpus or specialized Rsec model exists. Do not treat fixtures as validated knowledge or reference predictions as actual quality results.

GPU validation remains pending: RTX 4070 single-GPU QLoRA, RTX 3060 alone, heterogeneous DDP/FSDP, topology/P2P/NCCL, FP16/BF16, physical OOM, distributed optimizer layouts/save/resume/export, Linux/WSL2, and 7B memory/quality. Two 12 GB cards do not provide one contiguous 24 GB allocation. Follow GPU_VALIDATION_PLAN.md; smoke mode is CPU, not a CUDA test. Optional Ollama/llama-cpp-python and provider notebook sessions have not run.

Remaining limitations: lexical deduplication and privacy/poison heuristics, unsigned integrity manifests, no GPU lock, no semantic hallucination metric or dynamic remediation runner, repository-relative defaults, repeated model loads per benchmark case, operator-asserted registry TESTED, and initialization failures before Experiment not always recorded. See the audit risk register. RAG/SENTRA remain protocol contracts only.

Preserve dataset releases/checkpoints, add sources/replay only through the same screening/provenance process, keep test families frozen, and compare base/adapted/exported models before registering releases. Do not force push, delete existing work, auto-merge or provision paid services.

## Publication

Changes were published using the authorized GitHub tree/commit/ref APIs, with expected-head checks, fast-forward updates and tree equality against locally tested Git content. No credential was requested/stored. Local verification commits can have different author/timestamp hashes from Cloud-created commits while their trees are identical; use the published SHA above for reproduction.
