# Implementation report · Rsec v0.1.0-alpha

Phase 01-B update: [INDEPENDENT_AUDIT.md](INDEPENDENT_AUDIT.md) supersedes initial capability assertions where findings A01–A15 apply. Corrected code: `44084096dc231b7726ca1490c5e65f69a01956f9`. Final audit: 97 tests, 91.34% statement coverage; CUDA remains pending and Unsloth is BLOCKED.

Date: 2026-11-26. Phase: 01 — Foundation & MLOps. Repository: Snowwiy/Rsec. Base inspected: f42f893948cc2388d4025920d545e4dcc74cf5a9 (initial commit). Existing MIT license preserved. No pretrained Rsec cybersecurity weights, paid infrastructure or SENTRA changes are included.

## Delivered architecture

The installed src/rsec package implements a CPU-safe CLI, typed configurations, reviewed HTTPS/HF acquisition, separate knowledge/SFT processing, privacy/secret/poison heuristics, provenance-aware curation, deterministic grouped train/eval/test releases, integrity manifests, TRL/PEFT training, experiment tracking, deterministic evaluation, local registry, export and local runtime adapters. See docs/ARCHITECTURE.md for module responsibilities and future contracts.

## Feature status

| Capability | State | Evidence / boundary |
|---|---|---|
| Packaging, CLI, strict configuration, diagnostics | TESTED | CPU CLI/config tests and wheel/sdist builds |
| JSON/JSONL/CSV curation, deduplication, quarantine, split/benchmark isolation | TESTED | Synthetic CPU tests; content-free rejected records |
| Knowledge ingestion and heuristic domain/language classification | TESTED | Independent knowledge records, never implicit SFT |
| Parquet and Hugging Face source ingestion | IMPLEMENTED | Bounded code paths; external-source acquisition not end-to-end tested |
| Resumable HTTPS acquisition and cache integrity | TESTED | Unit test uses a fake HTTP transport; not live publisher validation |
| Tiny CPU SFT/LoRA, checkpoint optimizer resume, adapter export, merge and offline inference | TESTED | Actual optimization and local model execution |
| Local benchmark generation and scoring | TESTED | Real random-model generation plus deterministic reference fixture tests |
| QLoRA NF4 and conservative single-GPU profiles | GPU VALIDATION PENDING | No CUDA device; no complete 7B training attempted |
| DDP/FSDP with heterogeneous GPUs | GPU VALIDATION PENDING | Strict launch guards, parsed Accelerate configs; no physical validation |
| Unsloth backend | BLOCKED | Phase 01-B confirmed incompatible Transformers/TRL/datasets requirements |
| Local model registry, activation/rollback and experiment reports | TESTED | Immutable registration/hash checks, local JSON/CSV/Markdown/SVG |
| GGUF conversion, Q4_K_M and native llama.cpp completion | TESTED | Random tiny Qwen2 weights with official tokenizer; no quality claim |
| Ollama / llama-cpp-python runtime adapters | IMPLEMENTED | Engines/bindings not executed here |
| Notebook workflows | IMPLEMENTED | Code cells parsed and linted; Colab/Kaggle provider execution unverified |
| CI/security configuration | IMPLEMENTED | Pinned read-only workflows; local audit/scanner evidence in TEST_RESULTS.md |
| Full RAG, production API, SENTRA integration | NOT IMPLEMENTED | Intentionally future phases; protocol interfaces documented |
| Broad gold cybersecurity corpus and isolated dynamic remediation testing | NOT IMPLEMENTED | Subsequent data/evaluation work |

## Decisions and dependencies

Preliminary base: Qwen/Qwen2.5-Coder-7B-Instruct at c03e6d358207e414f1eca0bb1891e29f1db0e242. Its license and alternatives were checked against primary publisher material. No independently measured model quality or Spanish/English superiority is claimed. The standard src/rsec layout deliberately replaces the requested flat src layout. Empty artifact directories are not committed as simulated functionality.

Existing MIT code rights were preserved rather than silently replaced by the proposed Apache license. Third-party data/models/adapters require separate rights review. Core installation does not include torch/CUDA. CPU dependencies have exact transitive pins; GPU/optional profiles do not claim a validated transitive lock. Initial vulnerable dependency versions were replaced and APIs retested. See docs/DEPENDENCIES.md and ADR 001.

## Files

Created: src/rsec modules; tests/unit, tests/integration and synthetic fixtures; configs/models, profiles and Accelerate configs; data/samples; independent benchmark suite; prompts; requirements groups and CPU lock; scripts; three GitHub workflows and PR template; Colab/Kaggle notebooks; architecture/data/training/multi-GPU/evaluation/security/inference/registry/dependency docs; ADR, roadmap, model card, changelog and continuity reports. Modified: the original README, expanded with an aligned Spanish version. LICENSE content is unchanged. No existing application code was overwritten.

## Limits and residual risks

Heuristic privacy/poison filtering is not comprehensive. Unsigned hashes cannot establish source authenticity. The quadratic deduplication baseline requires curated bounded shards and explicit provenance families. GPU memory/topology, heterogeneous throughput and distributed checkpoint/export semantics remain unmeasured. Native conversion proves an artifact path, not 7B behavior. Ollama service policy and optional native bindings remain operator trust boundaries. Checkpoints containing optimizer state must be trusted local outputs. Optional Unsloth/GPU dependency environments need independent resolution, audit and tests.

No configuration changes to repository visibility/security, force pushes or automatic merges are authorized or performed. The delivery is reviewable foundation code; it is not a release of a validated specialized model.
