# Changelog

## 2026-11-26 — Phase 01-B independent audit

- Fixed SFT token-length checks for the installed Transformers return type; verified real TRL target masks, padding and causal loss.
- Fixed missing predict CLI, benchmark-question leakage, subset label schemas and non-comparable regression gates.
- Hardened SafeTensors adapter/model loading, checkpoint/adapter fingerprints, metadata privacy, CSV, resource budgets and local inference options.
- Corrected experimental FSDP dtype/optimizer choices; explicitly blocked incompatible Unsloth pins. No CUDA validation claim.
- Added 58 meaningful regression/negative/integration cases: 97 total passed; coverage 75.15% → 91.34%. Core without torch: 88 passed, 9 deselected.
- Repeated native GGUF Q4_K_M generation and template preservation; hash matches original evidence.
- Added five independent audit/readiness reports and structured evidence, updated continuity/review/results and notebook pins.
- Verdict: PASS WITH CONDITIONS for foundation integration review into dev. No merge or specialized training performed.


## 0.1.0-alpha · 2026-11-26

- Add a modular local defensive AI research foundation with a CPU-safe CLI.
- Add licensed/provenanced curation, deterministic group splits and benchmark exclusion.
- Add real tiny CPU SFT/LoRA, integrity-checked optimizer resume, incremental adapter training and local tracking.
- Implement QLoRA and experimental DDP/FSDP/Unsloth paths pending hardware validation.
- Add deterministic evaluation, export/inference adapters, local registry and future RAG/SENTRA contracts.
- Add hardware profiles, notebooks, read-only CI, security controls and bilingual documentation.
- Preserve the existing MIT license; distribute no trained Rsec model.
