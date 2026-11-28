# Roadmap

| Phase | Goal | Exit evidence |
|---|---|---|
| 01 · v0.1.0-alpha | Foundation, data lifecycle, SFT/QLoRA, evaluation, exports, CLI and MLOps | Reviewable code, CPU tests, explicit hardware pending states |
| 02 · v0.2.0-alpha | Dataset engineering infrastructure IMPLEMENTED/TESTED; corpus exit FAIL | 22-source scoped registry, 64 SFT drafts, 32 public cases, 3 reference indexes; actual expert reviews and independent gold still BLOCKED |
| 02-B · v0.2.1-alpha | Expert curation, dev security, GPU preparation and software foundations | Signed local review, independent suite scaffolds, rights-scoped software track and physical gates |
| 03-A · v0.3.0-alpha.1 | Local Windows/WSL setup, loopback inference, supervised CUDA and agent integration | CPU protocol tested; owner workstation, physical 4070 and Goose pending |
| 03-A · v0.3.0-alpha.2 | Verify the RTX 4070 and RTX 3060 under WSL2 | Both GPUs, NCCL over host shared memory, and synthetic DDP/FSDP fixtures physically exercised |
| 03-B | Adopt Inkling 2 Mini and retain Granite 3B as fallback | Pinned GGUF and NF4 packages, isolated Unsloth, supervised dual-GPU inference and QLoRA evidence, isolated Goose workflow |
| 03 · BLOCKED | First local pilot and retention baseline | Real GPU QLoRA, approved releases, both base evaluations and reproducible mixed vs single-track comparison |
| 04 | Advanced defensive and software specialization | SOC, DFIR, secure coding, general programming, frontend/backend, testing and repo-level tasks with verified isolated evaluation |
| 05 | Local RAG and repository context | Versioned local knowledge, code indexing, hybrid retrieval, citations and trust boundaries |
| 06 | Multi-GPU optimization | Physical 4070/3060 comparison, measured communication/memory and inference |
| 07 | Production readiness | Authenticated local API, monitoring, distribution and stability |
| 08 | Optional integrations | Independent SENTRA and authorized defensive tool integration |

Large-model/MoE profiles remain experimental until resource and quality tests demonstrate feasibility. No later phase is implicitly implemented by this repository structure.

Phase 02 corpus verdict: **DATASET READINESS: FAIL; TRAINING READINESS: NOT READY**. The 500–1,000 pilot target, expert approvals and independent final gold remain unmet. Infrastructure review in PR #2 does not waive them. Exact later 11-step execution order and hardware gates: [TRAINING_READINESS.md](TRAINING_READINESS.md).

Programming is a permanent release criterion. Phase 03 freezes comparable baselines on both suites and evaluates retention through replay. Phase 04 expands multilingual code, architecture, APIs, data, automation, DevSecOps, CI/CD, documentation, debugging and optimization with authorized data. The current phase's priority remains expert curation, security integration and hardware preparation. See [software architecture and replay](docs/SOFTWARE_ENGINEERING.md).
