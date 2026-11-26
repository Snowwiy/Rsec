# Roadmap

| Phase | Goal | Exit evidence |
|---|---|---|
| 01 · v0.1.0-alpha | Foundation, data lifecycle, SFT/QLoRA, evaluation, exports, CLI and MLOps | Reviewable code, CPU tests, explicit hardware pending states |
| 02 · v0.2.0-alpha | Dataset engineering infrastructure IMPLEMENTED/TESTED; corpus exit FAIL | 22-source scoped registry, 64 SFT drafts, 32 public cases, 3 reference indexes; actual expert reviews and independent gold still BLOCKED |
| 03 · BLOCKED | First specialization | Base evaluation, real GPU QLoRA, reproducible adapter and measured comparison |
| 04 | Advanced cybersecurity | SOC/DFIR/code/hardening specialization, reduced false positives and hallucinations |
| 05 | Local RAG | Versioned local knowledge, hybrid retrieval, citations and injection defenses |
| 06 | Multi-GPU optimization | Physical 4070/3060 comparison, measured communication/memory and inference |
| 07 | Production readiness | Authenticated local API, monitoring, distribution and stability |
| 08 | Optional integrations | Independent SENTRA and authorized defensive tool integration |

Large-model/MoE profiles remain experimental until resource and quality tests demonstrate feasibility. No later phase is implicitly implemented by this repository structure.

Phase 02 corpus verdict: **DATASET READINESS: FAIL; TRAINING READINESS: NOT READY**. The 500–1,000 pilot target, expert approvals and independent final gold remain unmet. Infrastructure review in PR #2 does not waive them. Exact later 11-step execution order and hardware gates: [TRAINING_READINESS.md](TRAINING_READINESS.md).
