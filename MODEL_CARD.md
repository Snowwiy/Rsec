# Rsec model card — infrastructure stage

Infrastructure version: v0.3.0-alpha.1. Owner: Snowwiy. Languages intended: Spanish/English. Intended uses include defensive security, authorized analysis, programming and software engineering on local hardware.

**Rsec is at the infrastructure stage.** CPU smoke tests use random tiny weights solely to validate training infrastructure. No benchmark performance or superiority claim is made. Rsec-7B/14B/32B/Coder/SOC/DFIR are future naming possibilities.

The Phase 03-B candidate for Rsec-Core is Thinking Machines Lab Inkling 2 Mini, an Apache-2.0 text-and-image model with 26.4B total parameters and shared layers in its looped decoder. Granite 3B Code Instruct 128K is the technical fallback. The existing Qwen configuration remains available for reproducibility of the generic backend. The Rsec software is MIT. Review provenance, rights and intended use for each future adapter, merged checkpoint and dataset. [Model selection](MODEL_BASE_SELECTION.md) · [Publisher card](https://thinkingmachines.ai/model-card/inkling-2-mini/)

Training method implemented: PEFT LoRA/QLoRA via TRL SFT, configurable response masks and independent test data. Hardware training validation: pending. Dataset:64 controlled bilingual SFT drafts, 32 public development/regression candidates and3 reference indexes; expert-approved SFT0, expert gold0. This is not a released training corpus. DATASET READINESS: FAIL; TRAINING READINESS: NOT READY. See DATASET_CARD.md and TRAINING_READINESS.md. Evaluation: deterministic task scoring, reference fixture tests, no trained model results.

Risks: inaccurate security advice, unsupported references, false positives/negatives, language imbalance, poisoned sources, private-data exposure and catastrophic forgetting. Human review and independent task evaluation are required. Do not use an unvalidated future model as an autonomous incident authority or attack agent.

The frozen Inkling checkpoint provides the Phase 03-B reference for programming and multimodal retention. The software taxonomy covers code generation, debugging, refactoring, architecture, frontend, backend, desktop applications, databases, testing, automation and secure coding. Separate CodeBench and CyberBench suites must remain independent of training and replay. Matched multimodal and tool-use fixtures are required before judging retention after textual adaptation or quantization. No specialized Rsec adapter or measured retention gain exists. [Software track](docs/SOFTWARE_ENGINEERING.md)
