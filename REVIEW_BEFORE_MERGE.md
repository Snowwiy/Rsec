# Review before merge — Phase 01-B

## Verdict and recommendation

**PASS WITH CONDITIONS** for review as foundation alpha into `dev`. Keep PR #1 in draft pending the owner's human review. Do not merge automatically into `dev` or `main`, release specialized weights, or infer GPU/model-quality approval from passing CI.

Initial head independently reviewed: `48709e49c2650793f8af792344988552151de158`. Corrected implementation: `44084096dc231b7726ca1490c5e65f69a01956f9`, with all three hosted workflows successful. Review the checks of the latest reporting head as well.

## Review gates

- Read findings A01–A15 in INDEPENDENT_AUDIT.md and inspect target masks/token counting, benchmark prompt isolation, metric label sets, comparable-condition gates and local artifact guards.
- Confirm TEST_RESULTS.md and structured evidence: 97 tests / 91.34% statement coverage, independent baseline 39 / 75.15%, core without torch 88 passed / 9 deselected, native GGUF repeated.
- Confirm no real specialized model, external corpus approval, paid service, repository policy change or merge occurred. Existing MIT and prior work remain preserved.
- Treat Unsloth as BLOCKED. FSDP fixes address documented incompatibilities but do not certify distributed execution, memory feasibility or checkpoint layout.
- Verify the final PR head's CPU quality, offline ML and security jobs before integrating. Coverage is statement coverage; tests with fake transports/engines are contract evidence only.

## Accepted alpha limitations

No NVIDIA device was available. Physical QLoRA, mixed precision, DDP/FSDP, heterogeneous topology/NCCL/OOM and distributed recovery remain required before training. Ollama/bindings/providers/Windows/WSL2 need separate execution. GPU dependency graph is not transitively locked/audited. Training CUDA branches remain below the aspirational 90% line-coverage goal; mocking them would not establish physical support.

Data/source rights, expert labels, privacy, semantic poisoning, authenticating artifacts and benchmark breadth require review; regex/hash checks cannot certify them. Registry TESTED remains a human assertion. Dataset releases and external test families must stay frozen. Exported weights must be evaluated under comparable conditions; native tiny GGUF plumbing is not proof of quantized model quality.

## Fase 02 decision

Conditional readiness to begin rights review, curation and external benchmark construction. DATASET_READINESS.md lists release gates; GPU_VALIDATION_PLAN.md lists physical acceptance. **Not ready for real specialized training or public model release.** These conditions are compatible with merging foundation code into dev after human review; they are not waived by that merge.
