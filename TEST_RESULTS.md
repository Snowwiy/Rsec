# Test results · 2026-11-26

## Environment

Linux x86_64, kernel 6.18.57, glibc 2.41, Python 3.12.14. PyTorch 2.8.0+cpu. No NVIDIA/CUDA device and no nvidia-smi. Approximately 9.7 GiB host RAM; available memory varied during native compilation. Installed ML versions and rights metadata are in docs/DEPENDENCIES.md. No full model weights were downloaded; the official Qwen tokenizer was acquired for a random tiny export fixture.

## Final results

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
