# Handoff · Fase 03-B · 2026-11-28

La rama de adopción deriva de `e67a961`, la cabeza del PR #7 al inicio de esta fase. El borrador de Fase 03-B usa esa rama como base. El candidato principal es Inkling 2 Mini y Granite 3B queda como respaldo. La ruta de inferencia usa un llama.cpp aislado. La ruta de ajuste técnico tiene su propio entorno Unsloth y descargas fijadas. [PR #7](https://github.com/Snowwiy/Rsec/pull/7) · [PR #8](https://github.com/Snowwiy/Rsec/pull/8) · [Plan de adquisición](MODEL_ACQUISITION_PLAN.md)

Consulta los pasos y el estado físico en [compatibilidad](INKLING_COMPATIBILITY.md), [dual-GPU](MULTI_GPU_VALIDATION.md), [QLoRA](QLORA_VALIDATION_REPORT.md) y [Goose](GOOSE_INTEGRATION.md). Los registros crudos, identificadores de hardware, configuración personal y artefactos se mantienen en almacenamiento privado. El [gate de datos](TRAINING_READINESS.md) sigue bloqueando la especialización.

La estación verificó inferencia en cuatro contextos hasta 32K y el ciclo de reparación con Goose. QLoRA pasó con atención eager y heurísticas MoE en su proceso. El adaptador técnico se guardó y restauró con comprobación de integridad. El punto de partida para una evaluación de capacidad es el modelo base congelado y los benchmarks independientes adjudicados.

---

# Handoff · v0.3.0-alpha.2

## Estación dual · 2026-11-27

El [PR #7](https://github.com/Snowwiy/Rsec/pull/7) conserva la rama `feat/rsec-physical-validation-v0.3.0`. Se reutilizó la estación instalada. Ambas GPU quedaron verificadas individualmente por UUID. NCCL usó memoria compartida del host. DDP y FSDP validaron recuperación en fixtures técnicas. Las mediciones diferencian CUDA en WSL2, el runtime Windows de llama.cpp y Goose. [Resultados](TEST_RESULTS.md) · [Benchmark](MULTI_GPU_BENCHMARK.md) · [Inferencia](LOCAL_INFERENCE_GUIDE.md)

**TRAINING READINESS BLOCKED.** El corpus permanece con cero aprobaciones humanas. Conservar los informes crudos bajo `.rsec-local/`. Los próximos ensayos de capacidad requieren un base generativo con derechos y manifiesto verificados, y supervisión cuando haya una carga existente. [Gate de entrenamiento](TRAINING_READINESS.md)

---

# Handoff histórico · v0.3.0-alpha.1

## Reanudación en la estación Windows · 2026-11-27

El [PR #7](https://github.com/Snowwiy/Rsec/pull/7) continúa en `feat/rsec-physical-validation-v0.3.0`, con base dev `63d14f7`. Se clonó el checkout oficial en la unidad de datos y se instalaron los entornos separados de Windows y Ubuntu 24.04 WSL2. Consulta [instalación](LOCAL_INSTALLATION_REPORT.md), [pruebas](TEST_RESULTS.md) e [integración con Goose](GOOSE_INTEGRATION.md).

**GPU VALIDATION PENDING.** La RTX 4070 es la única GPU detectada. Tras la confirmación del operador de que terminó de jugar e instaló la RTX 3060, volver a enumerar por UUID y validar la 4070 primero. Validar la 3060 individualmente antes de NCCL/DDP. Aplicar aviso a 80 °C y parada a 85 °C o ante inestabilidad. Conservar la evidencia cruda fuera de Git.

**TRAINING READINESS NOT READY.** El piloto de revisión contiene 64 candidatos y cero aprobaciones. Se mantienen los gates de derechos, revisión humana y evaluación independiente. Las secciones siguientes corresponden al historial.

---

# Handoff · v0.2.1-alpha · Phase 02-B

Review [hotfix #4](https://github.com/Snowwiy/Rsec/pull/4) first, then [Phase 02-B #5](https://github.com/Snowwiy/Rsec/pull/5) into dev. PR #1 reached dev and PR #2 reached the foundation branch. The main PR preserves that ancestry and includes the hotfix. PR #3 is the later dev-to-main review. See [integration evidence](GITHUB_INTEGRATION_REPORT.md).

**Repository security PASS WITH CONDITIONS** while the hotfix awaits dev integration. **Dataset readiness FAIL**, **GPU readiness VALIDATION PENDING**, **training readiness NOT READY**. Preaudited 64 SFT and 32 CyberBench candidates, zero human approvals. There are 12 CodeBench development cases, 54 default reserved cases and no private final gold. In the software catalog, one pinned SQLite file has scoped local SFT source permission and contributes zero approved rows. Candidate outputs remain separate from acquired references.

Start with [human review](DATASET_REVIEW_GUIDE.md) and [reviewer authority](REVIEWER_SECURITY.md). Prioritize the conditional SQL finding and the generic CyberBench rationales. Physical procedure begins with [local GPU setup](LOCAL_GPU_SETUP.md), then [multi-GPU validation](MULTI_GPU_VALIDATION.md). Phase 02 uses the existing PyTorch/Transformers/PEFT/TRL/BitsAndBytes/Accelerate path and keeps Unsloth blocked.

The companion [software track](docs/SOFTWARE_ENGINEERING.md) is now fundamental to Rsec. Retain CodeBench and CyberBench as distinct reservations, validate rights before adding data, and compare against the same local base before choosing replay quotas. The materialized replay release has validation in the existing trainer entry point. Progress to advanced programming in Phase 04 after the mixed pilot and retention gate in Phase 03.

The previous Phase 02-A handoff below records its historical state.

---

# Handoff — Rsec v0.2.0-alpha, Phase 02

**DATASET READINESS: FAIL** for an approved SFT release. **TRAINING READINESS: NOT READY.** Infrastructure implemented/tested and available for review; zero expert-approved SFT and zero independent expert gold. No specialized model, paid services or merge.

## Authoritative state and publication

[Draft dependent PR #2](https://github.com/Snowwiy/Rsec/pull/2), branch `feat/rsec-dataset-engineering-v0.2.0`, based exactly on PR #1 audited head `758896318f106a3c48f3f73860bf329881d264ec`. PR #1 remains open/draft toward dev; main/dev remain at `f42f893948cc2388d4025920d545e4dcc74cf5a9` at inspection. Feature code `849f0053bf3443b8d270945da9bdcaac6665667a`, tree `5470aefa8422c971c842c702ee7629c44b1d0f5b`. Scanner correction `cb3d2d639ed99a0c8f16291353553fe734f224cb`, tree `81a032f9ae7052ffe1a6d3e56f5e973f9fc3e94c`. Cloud commits use expected-head, non-force updates and equality against the locally tested Git tree; local verification commit IDs can differ by author/time.

All three corrected code head workflows passed: [CPU45908654504](https://github.com/Snowwiy/Rsec/actions/runs/45908654504), [offline ML45908654526](https://github.com/Snowwiy/Rsec/actions/runs/45908654526), [security45908654641](https://github.com/Snowwiy/Rsec/actions/runs/45908654641). Inspect final reporting-head CI as well. Initial security CI failed on public tokenizer hashes; narrow path AND exact-hash exceptions fixed it, and a synthetic negative scanner control still rejects another value in the same file.

First read AGENTS.md, DATASET_ENGINEERING_REPORT.md, DATASET_CARD.md, DATASET_QUALITY_REPORT.md, BENCHMARK_REPORT.md, TRAINING_READINESS.md, TEST_RESULTS.md and REVIEW_BEFORE_MERGE.md. Historical Phase 01-B audit/GPU reports remain applicable; their old dataset counts are historical. Notebook pins intentionally remain on audited Phase 01 CPU/GPU infrastructure; Phase 02 data commands are documented in the checkout, not silently added to unexecuted provider notebooks.

## What exists and what does not

Registry 22 = 20 verified external locations + 2 internal fixture sources. Policy APPROVED 3/REVIEW REQUIRED 18/RESTRICTED 1/REJECTED 0. External SFT approved 0. Three pinned official CVE documents, 66,108 bytes, fetched through the authorized GitHub connector, matched to official blob IDs and frozen SHA-256. Native direct DNS failed; subsequent registry cache verification passed without DNS. Raw payloads and 3 reference indexes remain ignored, not redistributed. Their hashes/source identity are public sanitized evidence.

Pilot 64 = 32 controlled scenarios × EN/ES, 8 per domain, 32 EN/32 ES, 32 fundamental/32 intermediate. Benchmark 32 = 15 families, 4 per domain, 16 EN/16 ES, 22 development/10 regression, labels 10 vulnerable/10 benign/12 insufficient. All 96 conversations await real expert review. Reference interpretation pending 3; total 99 unique processed/99 pending, 0 approved/0 rejected/0 quarantined. No private gold. No train/eval/test SFT files. The 500–1,000 quality-conditional target is unmet, not padded.

Candidate schema/quality, source rights/references, metadata-only quarantine, immutable policy snapshots, complete inventory validation, explicit human ledger, group/code/translation leakage guards, reviewed-only SFT bridge, actual tokenizer stats, CLI and public rubric scaffolding are implemented. Legacy prepare supports existing fixtures; it is not Phase 02 expert promotion. `rubric-score` reviews cases, not output-bound comparative model ratings. No semantic truth detector or dynamic remediation runner exists.

## Reproduction

Use Python 3.12 and `requirements-dev.txt -e .` for core. Run `pytest -m 'not ml'`, Ruff, repository validation and build. Real tiny CPU ML additionally requires the official `torch==2.8.0+cpu` wheel and `requirements-cpu-test.lock`; run `HF_HUB_OFFLINE=1 pytest --cov=rsec`. Actual final 200 passed/94.02%; no-Torch core 189 passed/11 deselected. No prior tests removed. Detailed commands/evidence in TEST_RESULTS.md and audits/phase02/validation.json.

```bash
rsec data sources
rsec data download --registered
rsec data curate --input data/pilot/candidates.jsonl --output data/processed/new-pilot --version pilot-0.2.0
rsec data validate data/processed/new-pilot
rsec data review data/processed/new-pilot --output reports/new-review.json
rsec benchmark validate
rsec benchmark contamination-check --input data/pilot/candidates.jsonl
```

Choose new output paths. Split correctly blocks without actual decisions. The pilot generator reproduces input bytes; two fresh pilot bundles had manifest SHA-256 `764a04ba9506a660ef8b254941ad93280c5f737bff6272dd050a1c04951973af`. Existing reviewed local tokenizer measured 16,114 conversation tokens, mean 251.78/max 414, eligible tokens/epoch 0. Local tokenizer files/weights are not committed; a fresh checkout can inspect recorded identities or supply its own reviewed materialized tokenizer. Whitespace counts are not tokenizer counts.

## Next agent / integration

Obtain actual qualified bilingual review, externally authorized SFT sources and independent expert-authored/adjudicated gold. Do not invent reviewer identities or copy temporary pytest attestations. Keep final evaluator content and private review records outside Git. Add prediction/model hash binding before using human rubric scores for comparative model approval. Add deliberate source adapters and semantic/cross-shard checks before scale. Follow the 11 Phase 03 steps in TRAINING_READINESS.md only after data gates and separate authorization.

Keep the primary audited PyTorch/Transformers/PEFT/TRL/BitsAndBytes/Accelerate path. Unsloth 2026.11.12 remains BLOCKED by Transformers/TRL/datasets conflicts; pins/training code unchanged. Physical NF4/QLoRA 4070,3060, DDP/FSDP, FP16/BF16, OOM/resume, WSL2/Linux and provider sessions remain pending. Two 12 GB cards are separate allocations, not a contiguous 24 GB pool. Historical tiny CPU GGUF success does not establish future specialization quality.

Integrate only after human review: merge PR #1 into dev, verify audited ancestry/content, retarget PR #2 to dev and rerun checks. If #1 is squashed/rebased, compare content and resolve with a normal merge commit where needed; do not force push/discard work. PR #2 currently targets the foundation branch to avoid duplicating Phase 01 differences. No automatic merge is authorized.
