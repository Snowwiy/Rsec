# Dependency and compatibility record

Reviewed 2026-11-26. Direct pins live in requirements files; the fully frozen Linux/Python 3.12 CPU environment is requirements-cpu-test.lock. Metadata below comes from the installed distributions and must not be interpreted as relicensing third-party artifacts.

| Distribution | CPU-tested version | Publisher license metadata |
|---|---|---|
| pydantic | 2.14.4 | MIT |
| PyYAML | 6.0.4 | MIT |
| torch | 2.8.0+cpu | BSD-3-Clause |
| transformers | 5.24.1 | Apache 2.0 License |
| trl | 1.19.0 | Apache-2.0 |
| peft | 0.22.0 | Apache |
| accelerate | 1.16.0 | Apache |
| datasets | 5.0.1 | Apache 2.0 |
| pyarrow | 23.0.1 | Apache-2.0 |
| safetensors | 0.8.0 | not declared |
| numpy | 2.5.5 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| scikit-learn | 1.7.2 | BSD-3-Clause |
| pytest | 9.2.0 | MIT |
| ruff | 0.15.4 | not declared |

The initial historical stack was rejected after pip-audit findings. Final frozen CPU requirements were audited without known findings on the recorded date; this does not guarantee absence of vulnerabilities. Current installed signatures and real tiny SFT/resume/merge/inference tests verified API integration. Model quality and CUDA compatibility were not inferred from dependency installation.

PyTorch is installed separately by device. A core/dev/data install must not pull CUDA packages. The CPU lock pins torch==2.8.0+cpu; install that wheel from https://download.pytorch.org/whl/cpu before the lock. GPU training uses a separately selected PyTorch 2.8.0 CUDA build with requirements-train.txt; bitsandbytes 0.50.2 and Unsloth 2026.11.12 are unvalidated optional/GPU candidates. Do not describe their transitive environment as locked or tested.

Native GGUF validation used llama.cpp b671865c7bd44c8c2d4709b5f707bd55f7f612fd, CPU CMake build, gguf 0.19.0, sentencepiece 0.2.1 and cmake 4.2.3. Only the Qwen2 converter subset was exercised with PyTorch 2.8.0; upstream converter requirements recommend other versions for some architectures. Review/install the actual pinned checkout requirements before using another architecture.

Ollama and llama-cpp-python were not installed or executed. The native llama.cpp conversion/quantization and completion test are separate from those bindings. No paid GPU/service was provisioned.

Primary compatibility references are listed in docs/adr/001-base-model.md. Action tags were resolved with git ls-remote and pinned to immutable SHAs. Gitleaks release 8.24.3 was checked against its publisher SHA-256 before local use; CI builds its pinned source commit instead.
