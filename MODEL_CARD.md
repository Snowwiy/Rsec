# Rsec model card — infrastructure stage

Version: v0.1.0-alpha. Owner: Snowwiy. Languages intended: Spanish/English. Use: defensive security, authorized analysis, detection and remediation.

**No trained Rsec cybersecurity weights are released.** CPU smoke tests use random tiny weights solely to validate training infrastructure. No benchmark performance or superiority claim is made. Rsec-7B/14B/32B/Coder/SOC/DFIR are future naming possibilities.

Preliminary base: Qwen/Qwen2.5-Coder-7B-Instruct at the revision pinned in configuration; Apache-2.0 for that base. Existing Rsec software is MIT. Future adapters, merged weights and datasets require their own provenance, rights, intended-use and limitation review.

Training method implemented: PEFT LoRA/QLoRA via TRL SFT, configurable response masks and independent test data. Hardware training validation: pending. Dataset: authored synthetic plumbing examples only; not a cybersecurity corpus. Evaluation: deterministic task scoring, reference fixture tests, no trained model results.

Risks: inaccurate security advice, unsupported references, false positives/negatives, language imbalance, poisoned sources, private-data exposure and catastrophic forgetting. Human review and independent task evaluation are required. Do not use an unvalidated future model as an autonomous incident authority or attack agent.
