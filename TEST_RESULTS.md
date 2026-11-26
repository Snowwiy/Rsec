# Test results — Phase 02 dataset engineering, 2026-11-26

Published feature implementation `849f0053bf3443b8d270945da9bdcaac6665667a`, tree `5470aefa8422c971c842c702ee7629c44b1d0f5b`; scanner-only correction `cb3d2d639ed99a0c8f16291353553fe734f224cb`, tree `81a032f9ae7052ffe1a6d3e56f5e973f9fc3e94c`. Linux/Python 3.12 CPU; no NVIDIA device. Audited Phase 01-B baseline was independently reproduced: **97 passed / 91.34% statement coverage**.

**Final local: 200 passed, 0 failed, 2 SWIG deprecation warnings; 94.02% statement coverage, 2,168 / 2,306 statements, 138 missing.** Core environment without Torch: **189 passed, 11 ML deselected**. All original 97 tests preserved; 103 additional meaningful cases. Existing protocol contracts remain in the denominator and no new coverage exclusions were added.

## Commands actually executed

Run from checkout root. Logs, heavy artifacts, temporary test attestations and source payloads remain ignored; sanitized reproducible evidence is [audits/phase02/validation.json](audits/phase02/validation.json).

| Command | Actual result |
|---|---|
| `HF_HUB_OFFLINE=1 .venv/bin/pytest -q --cov=rsec --cov-report=json:reports/phase2-coverage.json --cov-report=term-missing --junitxml=reports/phase2-pytest.xml` |200 passed, 0 failed,94.02% |
| `/workspace/scratch/faecd1545a19/core-check/bin/python -m pytest -q -m 'not ml'` |189 passed, 11 deselected; no Torch installed |
| `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` | Passed,51 Python files formatted |
| `.venv/bin/python scripts/check_repository.py` | Configs/notebooks/pins/schema/registry/benchmark and public artifact rules passed |
| `.venv/bin/python -m pip install --no-build-isolation -e . --no-deps` | Installed rsec-ai 0.2.0a0 |
| `.venv/bin/python -m pip check` | No broken requirements |
| `.venv/bin/python -m build --no-isolation` | Wheel and source distribution 0.2.0a0 built |
| `.venv/bin/pip-audit --disable-pip --no-deps -r requirements-cpu-test.lock --format=json` | No known vulnerabilities for auditable entries; torch 2.8.0+cpu skipped (non-PyPI) |
| Gitleaks 8.24.3 `git --redact --exit-code 1` | Initial 4 public-checksum false positives; after narrow config correction, history passed |
| Temporary scanner control: exact known public checksum / other synthetic high-entropy value in same path | Exit 0 / exit 1 as expected; no broad path suppression |
| `.venv/bin/rsec data sources` |22 registered, 20 external locations verified, 0 external SFT-approved |
| `.venv/bin/rsec data download --registered` |3 pinned CVE cache snapshots verified; 0 DNS; native live download initially failed DNS |
| `.venv/bin/rsec data normalize-cve --input data/raw/cve/CVE-2021-44228.json data/raw/cve/CVE-2022-22965.json data/raw/cve/CVE-2023-34362.json --output data/interim/cve-reference-final.jsonl` |3 reference indexes, no SFT/no payload redistribution |
| `.venv/bin/rsec data curate --input data/pilot/candidates.jsonl --output data/processed/phase2-pilot-final --version pilot-0.2.0` |64 structurally accepted, 0 expert approved, 64 pending, 0 rejected/quarantined; SFT blocked |
| Same curation to `data/processed/phase2-pilot-reproduced`, same version/seed | Identical full curation-manifest SHA-256 |
| `.venv/bin/rsec data validate data/processed/phase2-pilot-final` | Passed integrity/semantic staging validation; does not approve SFT |
| `.venv/bin/rsec data review data/processed/phase2-pilot-final --output reports/phase2-review-final.json` |64 record hash packet, 0 approvals |
| `.venv/bin/rsec data split data/processed/phase2-pilot-final --output data/processed/phase2-sft-blocked` | Expected exit 2: no expert-approved examples |
| `.venv/bin/rsec benchmark validate` |32 cases, 15 families, 0 expert gold |
| `.venv/bin/rsec benchmark contamination-check --input data/pilot/candidates.jsonl` |64 candidates vs 42 reserved, 0 known links to reserved cases |
| `.venv/bin/rsec benchmark export --output reports/phase2-cyberbench-cases.jsonl` |32 legacy-runner-compatible development cases; no model generation |
| `.venv/bin/rsec data stats data/processed/phase2-pilot-final --tokenizer models/gguf-cpu-validation-256 --output reports/phase2-token-final.json` |16,114 actual chat-template tokens, max 414; eligible tokens/epoch 0 |

The three external payloads were really fetched via the authorized GitHub connector and matched to official pinned Git blobs before local SHA-256 pinning. Native HTTPS DNS failure is not counted as successful native acquisition. Subsequent cache-only validation does not demonstrate native live networking. Source and CISA 403 limits are documented in DATASET_SOURCES.md.

Corrected code head hosted checks all succeeded: [CPU45908654504](https://github.com/Snowwiy/Rsec/actions/runs/45908654504), [offline ML45908654526](https://github.com/Snowwiy/Rsec/actions/runs/45908654526), [security45908654641](https://github.com/Snowwiy/Rsec/actions/runs/45908654641). Initial code head security run 45908274891 failed on 4 exact public tokenizer hashes; the failure is retained in reporting and fixed without history rewrite. Check [PR #2](https://github.com/Snowwiy/Rsec/pull/2) for final reporting-head checks.

## Coverage by module

| Module | Statement coverage |
|---|---|
| src/rsec/__init__.py | 100.00% |
| src/rsec/artifacts.py | 96.88% |
| src/rsec/cli.py | 97.55% |
| src/rsec/config.py | 98.44% |
| src/rsec/data.py | 95.18% |
| src/rsec/datasets/__init__.py | 100.00% |
| src/rsec/datasets/benchmark.py | 98.55% |
| src/rsec/datasets/cli.py | 96.58% |
| src/rsec/datasets/knowledge.py | 100.00% |
| src/rsec/datasets/linkage.py | 98.94% |
| src/rsec/datasets/pilot.py | 100.00% |
| src/rsec/datasets/quality.py | 99.07% |
| src/rsec/datasets/registry.py | 99.07% |
| src/rsec/datasets/release.py | 93.43% |
| src/rsec/datasets/review.py | 100.00% |
| src/rsec/datasets/schema.py | 100.00% |
| src/rsec/datasets/stats.py | 93.94% |
| src/rsec/download.py | 91.00% |
| src/rsec/environment.py | 72.55% |
| src/rsec/errors.py | 100.00% |
| src/rsec/evaluate.py | 98.82% |
| src/rsec/export.py | 93.48% |
| src/rsec/inference.py | 91.95% |
| src/rsec/interfaces.py | 0.00% |
| src/rsec/knowledge.py | 92.19% |
| src/rsec/predict.py | 100.00% |
| src/rsec/tracking.py | 94.29% |
| src/rsec/train.py | 80.77% |
| src/rsec/utils.py | 98.15% |

Coverage measures exercised lines, not expert data correctness or hardware support. Training remains80.77% because CUDA/distributed/OOM branches require physical tests. Rubric/transport/review doubles verify math/validation contracts, not real reviewer identities, network availability or model quality.

## Meaningful negative/integration cases

Tests cover missing/unknown licenses, disallowed purposes, exact source/reference revisions, role/boolean/schema/taxonomy failures, heuristic language/domain mismatches, empty/inconsistent/long answers, secret/PII/poison detection, quarantine without sensitive content, exact/approximate duplicates, forward translation links and code fingerprints, default benchmark reservations, forged expert flags, hash/policy-bound decisions, duplicate/insufficient reviewers and partial review. Tamper tests include inventory additions, nested manifest names, symlinks, modified bridge content, and recomputed file hashes that still fail semantic checks. Generator bytes, distributions, contexts and local tokenizer metadata exclusion are asserted. Real CPU TRL checks the reviewed-test bridge target masks/loss. Case rubric scores are checked against weighted hand calculations and invalid attestations. No real corpus review is inferred from these temporary test fixtures.

## Explicitly not executed / not measured

No specialized Rsec training, actual expert corpus review, independent expert gold, model baseline/adapter quality benchmark, semantic hallucination measurement, dynamic remediation runner, CUDA/NF4/QLoRA, physical4070/3060/DDP/FSDP, real OOM, distributed optimizer recovery, Unsloth, Ollama/bindings/providers or Windows/WSL2 execution. Phase 01-B native tiny GGUF results below are historical; Phase 02 did not rerun or modify native export code. No training duration, VRAM fit or speed estimate was invented.

The Phase 01-B and original Phase01 evidence below is preserved as history, not the current test count.

---

# Test results — independent Phase 01-B, 2026-11-26

Audited implementation: `44084096dc231b7726ca1490c5e65f69a01956f9`; tested local tree `6bd98e7db4c7d9ac05633e1db57fbe6121312929`. Linux/Python 3.12.14, PyTorch 2.8.0+cpu, no NVIDIA device. Same pinned CPU stack as initial Phase 01. The initial suite was rerun unchanged before auditing: **39 passed / 75.15% statement coverage**.

## Commands and actual results

Commands below were executed from the checkout root, with `.venv/bin` tools unless an explicit interpreter is shown. Raw logs/weights remain ignored; sanitized evidence is versioned in `audits/phase01b/validation.json`.

| Command / check | Actual result |
|---|---|
| `HF_HUB_OFFLINE=1 .venv/bin/pytest -q --cov=rsec --cov-report=json:reports/audit-baseline-coverage.json --cov-report=term-missing` | 39 passed; 75.15% before changes |
| `HF_HUB_OFFLINE=1 .venv/bin/pytest -q --cov=rsec --cov-report=json:reports/audit-coverage.json --cov-report=term-missing --junitxml=reports/audit-pytest.xml` | **97 passed**, 0 failed, 2 SWIG/SentencePiece deprecation warnings; **91.34%**, 1,224 / 1,340 statements |
| `/workspace/scratch/faecd1545a19/core-check/bin/python -m pytest -q -m 'not ml'` | **88 passed**, 9 explicitly deselected; core environment has no torch |
| `.venv/bin/ruff check .` / `.venv/bin/ruff format --check .` | Passed |
| Extracted notebook Python: `ruff check --ignore E402` | Passed; E402 excluded because cells import packages after installation |
| `.venv/bin/python scripts/check_repository.py` | Configs, sample schemas, notebook Python syntax, workflow pins and tracked-artifact rules passed |
| `.venv/bin/python -m build` | Wheel and source distribution built |
| `.venv/bin/python -m pip check` | No broken requirements |
| Accelerate `load_config_from_file` sobre single/DDP/FSDP1 YAML | Los tres perfiles se parsean; sin lanzamiento físico |
| `.venv/bin/pip-audit --disable-pip --no-deps -r requirements-cpu-test.lock --format=json` | No known vulnerabilities in pinned CPU requirements |
| Gitleaks 8.24.3 `git --redact` / `git --pre-commit --staged --redact` | No leaks detected in history / staged changes |
| `pip download --no-deps --only-binary=:all: unsloth==2026.11.12` and wheel METADATA inspection | Downloaded without execution; three real incompatible requirements confirmed |
| `HF_HUB_OFFLINE=1 .venv/bin/python scripts/validate_gguf.py --llama-cpp /workspace/scratch/faecd1545a19/llama-cpp-validation --output exports/audit-native-01b` | Initial offline attempt failed: HF tokenizer cache absent. Not counted as success |
| Same native command with `--tokenizer models/gguf-cpu-validation-256 --output exports/audit-native-01b-local` | Converter, Q4_K_M quantizer and native generation passed; new destination, reused reviewed local tokenizer |
| GGUFReader metadata and local tokenizer comparison | 15 tensors, chat template exactly preserved; native Q4 hash equals historical hash |

Corrected-code GitHub workflows also passed: [CPU quality 45901526841](https://github.com/Snowwiy/Rsec/actions/runs/45901526841), [offline ML 45901526883](https://github.com/Snowwiy/Rsec/actions/runs/45901526883), [security 45901526945](https://github.com/Snowwiy/Rsec/actions/runs/45901526945). These runs are bound to the code commit above; inspect the PR for newer reporting commits.

## Coverage by module

No module was excluded to increase coverage. Protocol interfaces remain future contracts in the denominator. CPU doubles cover external API/error contracts, not the external hardware or engines.

| Module | Statement coverage |
|---|---|
| __init__.py | 100.00% |
| artifacts.py | 96.88% |
| cli.py | 97.44% |
| config.py | 98.44% |
| data.py | 94.67% |
| download.py | 91.00% |
| environment.py | 72.55% |
| errors.py | 100.00% |
| evaluate.py | 98.82% |
| export.py | 93.48% |
| inference.py | 91.95% |
| interfaces.py | 0.00% |
| knowledge.py | 92.19% |
| predict.py | 100.00% |
| tracking.py | 94.29% |
| train.py | 80.77% |
| utils.py | 96.30% |

Training remains 80.77% because CUDA loading, distributed operations, real interruption/OOM and incremental CUDA branches are not physically exercised. This limitation is retained explicitly instead of claiming physical support by increasing mock coverage.

## Meaningful new assertions

58 additional cases check benchmark questions with altered answers/families; internal leakage and tampered hashes/metadata; strict booleans and malformed schemas; CSV multiline/Parquet; bounded similarity; knowledge privacy and quarantine; fixed-label metrics against hand calculations; comparable baseline conditions and malformed output; CLI dispatch and secret-safe errors; download hash/range/retry limits; pickle/symlink/checkpoint inventory rejection; real TRL multi-turn target labels/padding/manual causal cross entropy; overlength target preservation; optimizer state step 2 → 3; adapter/merged logits; empty tensors and converter failures. No generated code is executed.

Native Q4_K_M: 60,040,704 bytes, SHA-256 `ba72a4435a6c4d03c549154aa61010fbc8acfcf53fe9f607c1bb07615e16b6d7`. Template digest: `2e2d2512cfe46af53dc1eed45368ecaab26ac4461c480e6b69fe571cf0ceaa75`. The converter warning `Unknown RoPE type: default` remained nonfatal on this tiny fixture; native loading/generation passed, with no quantizer fallback reported. No model-quality or 7B claim follows.

## Not executed

No CUDA hardware, actual QLoRA, heterogeneous DDP/FSDP, physical OOM, distributed resume/export, Unsloth execution, Ollama server, llama-cpp-python engine, provider notebook session, Windows/WSL2 installation, real cybersecurity corpus training, independent semantic gold assessment or dynamic remediation runner. Optional API tests use doubles; physical statuses remain pending/BLOCKED as described in the audit.

The earlier Phase 01 evidence below is preserved as history, not the current test count. Its assertions superseded by findings A01–A15 should be read with INDEPENDENT_AUDIT.md.

---

# Phase 01 historical test evidence · 2026-11-26

## Environment

Linux x86_64, kernel 6.18.57, glibc 2.41, Python 3.12.14. PyTorch 2.8.0+cpu. No NVIDIA/CUDA device and no nvidia-smi. Approximately 9.7 GiB host RAM; available memory varied during native compilation. Installed ML versions and rights metadata are in docs/DEPENDENCIES.md. No full model weights were downloaded; the official Qwen tokenizer was acquired for a random tiny export fixture.

## Phase 01 results (historical)

| Check actually executed | Result |
|---|---|
| HF_HUB_OFFLINE=1 pytest -q --cov=rsec --cov-report=json | 39 passed; 0 failed; 75.15% statement coverage |
| Fresh core/dev environment, no PyTorch installed; pytest -m 'not ml' | 37 passed, 2 explicitly deselected ML tests |
| ruff check . and ruff format --check . | Passed |
| python scripts/check_repository.py | Passed: configs, notebook syntax, pinned workflow actions, samples and tracked artifact limits |
| python -m build | Wheel and source distribution built successfully |
| rsec data prepare / validate on bundled fixtures | 12 accepted, 0 rejected; reproducible disjoint train/eval/test with verified manifest |
| Accelerate config parser on single/DDP/FSDP files | All three configurations parsed; physical launch not executed |
| pip-audit --disable-pip --no-deps -r requirements-cpu-test.lock | No known vulnerabilities found in the frozen CPU set at execution time |
| Gitleaks 8.24.3 on staged project changes / Git history | Passed after restricting scope to repository content; ignored model tokenizer fixtures are not committed |
| scripts/validate_gguf.py with a clean pinned native build | Real Qwen2 conversion, Q4_K_M quantization and four-token native CPU generation completed |

The ML integration test actually optimizes tiny random weights with LoRA, evaluates, writes checkpoints, restores optimizer/scheduler state, continues training, exports an adapter, safely merges it, generates locally and runs the benchmark prediction/scoring path. A tampered optimizer checkpoint is rejected. This is not a mock training success and does not measure cybersecurity proficiency. Reference prediction scores are only tests of the scorer.

## Native export evidence

llama.cpp: b671865c7bd44c8c2d4709b5f707bd55f7f612fd. Built llama-quantize and llama-completion with a CPU CMake build. Python converter subset: gguf 0.19.0, sentencepiece 0.2.1; CMake 4.2.3. Reproduction command:

```bash
HF_HUB_OFFLINE=1 python scripts/validate_gguf.py \
  --llama-cpp /local/reviewed-llama.cpp --output exports/unique-validation-run
```

This needs the official tokenizer already cached; --allow-network permits its initial public download. It creates random one-layer Qwen2 weights (hidden size 256) so K-quantization block dimensions are valid. Final Q4_K_M file: 60,040,704 bytes; SHA-256 `ba72a4435a6c4d03c549154aa61010fbc8acfcf53fe9f607c1bb07615e16b6d7`. The quantizer reported no fallback tensors for this fixture. Native completion returned successfully and generated four tokens. No throughput number is presented as expected production performance.

The first 64-wide fixture used fallback quantization; it is not the evidence for the final K-quantization check. A missing converter dependency was corrected, then conversion and inference were rerun. Earlier API and generation-input failures were fixed before the final passing suite. Two third-party SWIG/SentencePiece deprecation warnings remained; no project test failed.

## Security evidence and limits

The frozen CPU dependency audit passed. GPU, Unsloth and third-party runtime stacks were not physically tested or transitively locked. Local Gitleaks release bytes were verified against publisher SHA-256 `9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c`. Workflows pin source/action SHAs and read-only permissions. No weights, checkpoints or downloaded native toolchains enter Git.

## Not executed / pending

- Real 7B base evaluation or cybersecurity specialization training: GPU VALIDATION PENDING.
- NVIDIA QLoRA/FP16/BF16, OOM handling under physical load and CUDA memory measurements: GPU VALIDATION PENDING.
- RTX 4070 / RTX 3060 / combined DDP/FSDP benchmarks and distributed checkpoint recovery: GPU VALIDATION PENDING.
- Unsloth execution, live third-party corpus ingestion, optional Parquet round trip, Ollama and llama-cpp-python: not runtime tested.
- Colab/Kaggle provider sessions and native Windows/WSL2 installation: not executed; notebook Python cells were parsed/linted only.
- GitHub-hosted workflow outcomes: inspect the PR checks; local results do not assert remote CI success.
- Broad independently curated cybersecurity gold data, semantic hallucination assessment and isolated dynamic remediation tests: NOT IMPLEMENTED.

No omitted physical checks are counted as passing, and no synthetic fixture result is represented as a trained-model benchmark.
