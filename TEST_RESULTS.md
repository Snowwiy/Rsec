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
