# Handoff · Rsec v0.1.0-alpha

Phase 01 foundation implementation is delivered for code review. Base repository had only README.md and a 2026 MIT LICENSE; that license is preserved. main is not merged. dev was created at the original main commit and the work branch is feat/rsec-foundation-v0.1.0.

## Where to continue

Read README.md / README.es.md, IMPLEMENTATION_REPORT.md and TEST_RESULTS.md. Source is src/rsec; configuration defaults are repository-relative, so run commands from the checkout root. docs/adr/001-base-model.md records the preliminary Qwen decision and primary sources. AGENTS.md contains permanent development conventions.

The implementation includes licensed acquisition contracts, separate knowledge/SFT curation, secret/PII/poison heuristics, deterministic group splits, benchmark isolation, real TRL/PEFT SFT/QLoRA paths, optimizer resume, fresh incremental adapters, local experiment/registry lifecycle, deterministic benchmarking, exports and local inference adapters. RAG/SENTRA are protocol contracts only.

## Reproduce CPU checks

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt -e .
pytest -m 'not ml'
python -m pip install torch==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-cpu-test.lock
HF_HUB_OFFLINE=1 pytest -m ml
ruff check .
ruff format --check .
python scripts/check_repository.py
pip-audit --disable-pip --no-deps -r requirements-cpu-test.lock
python -m build
```

The final complete local suite passed 39 tests. A fresh core/dev environment without torch passed 37 tests with 2 ML tests explicitly deselected. A native llama.cpp tiny-random-model conversion/quantization/completion check also passed; details and reproducibility script are in TEST_RESULTS.md. Local raw artifacts remain ignored and are not a portable delivery dependency.

## Pending and risks

No real NVIDIA device was available. QLoRA, heterogeneous DDP/FSDP, distributed checkpoint layout, Unsloth, Windows/WSL2/provider runs and 7B memory/quality remain unvalidated. Ollama and llama-cpp-python were not installed; native llama.cpp was tested separately. GPU dependencies need their own verified transitive lock. Checkpoints are trusted-local state; hashes do not authenticate an untrusted sender. Filtering and lexical similarity are heuristics, not comprehensive privacy/poisoning guarantees. Optional inference services must be configured for local-only operation.

No trained Rsec cybersecurity model exists in this delivery. Named 7B/14B/32B/SOC/DFIR variants remain future lines. No broad cybersecurity benchmark/corpus or isolated dynamic code-remediation runner is implemented. Do not claim superiority or infer physical GPU support from mocks.

## Next work

Phase 02: perform source-specific rights review, curate a bilingual corpus and independent expert-reviewed gold cases, establish frozen external benchmark families and document each source's redistribution boundary. Then physically validate a short RTX 4070 QLoRA experiment using the recorded hardware report. Measure memory and save/resume before full phase 03 training. Compare base/adapted/exported models and regression behavior before registering a release as TESTED.

Do not relicense the repository, force push, auto-merge main, disclose private material or provision paid GPU services without explicit owner authorization. Preserve prior artifacts and checkpoints. Keep reports/docs honest when a test is blocked or omitted.

## Publication mechanism

Native terminal git push could not authenticate (no terminal username/credential channel). Publication used the already-authorized GitHub connection through content-addressed tree/commit APIs. The first implementation tree was verified identical to the local Git tree, and notebooks pin its published commit. No credentials were requested or stored; no force push was used.
