# Rsec model card — infrastructure stage

Infrastructure version: v0.3.0-alpha.1. Owner: Snowwiy. Languages intended: Spanish/English. Intended uses include defensive security, authorized analysis, programming and software engineering on local hardware.

**Rsec is at the infrastructure stage.** CPU smoke tests use random tiny weights solely to validate training infrastructure. No benchmark performance or superiority claim is made. Rsec-7B/14B/32B/Coder/SOC/DFIR are future naming possibilities.

Preliminary base: Qwen/Qwen2.5-Coder-7B-Instruct at the revision pinned in configuration; Apache-2.0 for that base. Existing Rsec software is MIT. Future adapters, merged weights and datasets require their own provenance, rights, intended-use and limitation review.

Training method implemented: PEFT LoRA/QLoRA via TRL SFT, configurable response masks and independent test data. Hardware training validation: pending. Dataset:64 controlled bilingual SFT drafts, 32 public development/regression candidates and3 reference indexes; expert-approved SFT0, expert gold0. This is not a released training corpus. DATASET READINESS: FAIL; TRAINING READINESS: NOT READY. See DATASET_CARD.md and TRAINING_READINESS.md. Evaluation: deterministic task scoring, reference fixture tests, no trained model results.

Risks: inaccurate security advice, unsupported references, false positives/negatives, language imbalance, poisoned sources, private-data exposure and catastrophic forgetting. Human review and independent task evaluation are required. Do not use an unvalidated future model as an autonomous incident authority or attack agent.

The Qwen coder base provides the reference for retaining programming ability. The software taxonomy covers generation, debugging, refactoring, design, frontend and backend, APIs, automation, defensive tools, databases, testing, DevSecOps, CI/CD, repository analysis, optimization, secure coding and documentation. Advanced specialization remains planned. Release gates require separate CodeBench and CyberBench comparisons on matched conditions before and after adaptation or quantization. A validated mixed replay release can preserve held-out sets and log training quotas. No released Rsec adapter or measured retention gain exists. See [software track](docs/SOFTWARE_ENGINEERING.md).
