# Entrenamiento · Fase 03-B

**DATASET READINESS BLOCKED. TRAINING READINESS BLOCKED.** Inkling 2 Mini es el candidato de Rsec-Core. El corpus conserva 64 borradores SFT y cero aprobaciones humanas. Hay cero casos gold independientes aprobados. No se ha iniciado entrenamiento especializado.

Antes del piloto, congela la evaluación del Inkling base en CodeBench, CyberBench, visión y uso de herramientas. Aplica la misma procedencia, separación de familias, revisión de derechos y aprobación al release mixto y a las fuentes de replay. Compara el adaptador y sus exportaciones con la base en condiciones equivalentes, incluyendo regresiones multimodales tras ajuste textual. El modelo de respaldo Granite 3B requiere su propia línea base. [Selección](MODEL_BASE_SELECTION.md) · [Validación técnica de Inkling](QLORA_VALIDATION_REPORT.md)

---

# Entrenamiento · Fase 03-A

## Estado de la estación · v0.3.0-alpha.2

**DATASET READINESS BLOCKED. TRAINING READINESS BLOCKED.** Persisten cero aprobaciones humanas, cero gold independiente y ningún paquete base local generativo completo identificado. Los smokes físicos CUDA, NF4 y LoRA pasaron en ambas tarjetas. NCCL y DDP fueron validados con fixtures. FSDP cumplió el ciclo técnico de una capa cuantizada y requiere una prueba posterior con el Transformer seleccionado. El entrenamiento mixto, el replay y las suites independientes conservan sus gates. [Selección del modelo](MODEL_BASE_SELECTION.md) · [Evidencia dual-GPU](MULTI_GPU_VALIDATION.md)

El primer piloto requiere derechos verificados, ejemplos aprobados y benchmarks independientes antes de especializar. Los artefactos de las fixtures técnicas permanecen fuera de Git.

---

# Gates vigentes · Fase 02-B

**TRAINING READINESS NOT READY.** La verificación de CUDA y NF4/QLoRA, la recuperación física y los recursos del perfil siguen pendientes. La primera especialización requiere releases SFT autorizados y firmados por personas competentes y benchmarks adjudicados independientes.

1. Ejecuta el diagnóstico y las pruebas individuales por UUID, después la sincronización de dos ranks y el protocolo experimental de FSDP.
2. Congela evaluaciones base para CyberBench y CodeBench, adjudica gold sin usarlo para seleccionar hiperparámetros, y acuerda tolerancias de regresión.
3. Promueve los dos releases y valida un plan de replay con presupuesto de tokens reproducible. Ejecuta el piloto mixto y su control bajo condiciones equivalentes.
4. Compara ambas capacidades con el modelo base y documenta regresiones. Repite la evaluación sobre artefactos fusionados y GGUF antes de promocionarlos.

Consulta [GPU local](LOCAL_GPU_SETUP.md), [multi-GPU](MULTI_GPU_VALIDATION.md), [replay y retención](docs/SOFTWARE_ENGINEERING.md) y [validación de benchmarks](BENCHMARK_VALIDATION_REPORT.md). El protocolo anterior se conserva abajo como referencia histórica.

---

# Training readiness · v0.2.0-alpha

**DATASET READINESS: FAIL. TRAINING READINESS: NOT READY.** The verdict concerns release of a technically approved corpus, not whether the data-engineering code can be reviewed. Infrastructure is implemented and CPU-tested; actual expert-approved SFT 0, expert gold 0, final hidden cases 0. No Rsec specialization was started and no trained Rsec weights exist.

## Blocking evidence and data scale

64 bilingual SFT drafts and 32 development/regression drafts await human review. Three pinned CVE reference indexes are not SFT. Source existence inventory covers 20 external locations; none is approved for SFT. Controlled original template rights do not certify technical correctness. Pilot size 64 is below the quality-conditional 500–1,000 target. Advanced/expert corpus coverage and independently authored/adjudicated gold are absent. Do not fill these gaps with generated approvals or duplicated templates.

Measured official local Qwen chat-template sequence lengths: 16,114 total conversation tokens, mean 251.78, median 261.5, p90 279, p95 291.2, p99 381.87, max 414. Context profiles 1024/2048/4096/8192 each contain all 64 drafts, with 0 overflow. Eligible tokens/epoch are **0**; total conversation tokens are not response-loss tokens. Full JSONL storage is 155,760 bytes. These are actual local tokenizer/byte measurements, not GPU memory, throughput or training-time estimates.

The main training stack remains PyTorch/Transformers/PEFT/TRL/BitsAndBytes/Accelerate. CPU tested pins remain unchanged: PyTorch 2.8.0+cpu, Transformers 5.24.1, TRL 1.19.0, datasets 5.0.1 (full pins in requirements files). Existing Unsloth 2026.11.12 wheel constraints conflict with Transformers <=5.17, TRL <=1.15 and datasets <5, so it remains optional, experimental and **BLOCKED**. No forced installation or downgrade was attempted. CPU lock pip-audit skips the non-PyPI torch+cpu entry; no full CUDA/optional transitive security certification follows.

## Exact Phase 03 sequence — not performed

1. **Validate RTX 4070 physically.** On Linux/WSL2 capture `nvidia-smi`, driver/OS/device UUID, 12 GB free/peak memory, PCIe topology, RAM/disk; run `rsec doctor --output reports/4070-doctor.json`. Follow GPU_VALIDATION_PLAN.md. Current environment has no NVIDIA device.
2. **Check the CUDA stack.** Use an isolated environment, compatible official CUDA PyTorch wheel and unchanged Rsec training requirements. Capture `pip freeze`, `pip check`, Torch CUDA/BF16/device probes and BitsAndBytes NF4 capability. CPU wheel is not a GPU lock. Resolve actual constraints before claiming support.
3. **Run a real QLoRA smoke.** First inspect NF4/double-quantized modules, trainable LoRA targets, dtype, masks and finite losses; use a reviewed tiny GPU fixture and `rsec train --profile local_rtx4070 --config /local/reviewed-smoke.yaml --max-steps 2 --output experiments/4070-nf4-smoke`. The config must use a pinned authorized base and an approved small v2 SFT release. `--smoke` instead creates CPU random weights and cannot validate CUDA. Check optimizer/adapter/checkpoint resume in a separate new run, memory and controlled OOM behavior.
4. **Benchmark the pinned base before tuning.** Obtain expert-adjudicated public development labels and evaluator-held final gold first. Export development cases; run `rsec predict --benchmark reports/cyberbench-cases.jsonl --model /local/base --output reports/base.jsonl`, then `rsec evaluate --benchmark reports/cyberbench-cases.jsonl --predictions reports/base.jsonl --model-id base --output reports/base.json`. Preserve sidecars and frozen final tests.
5. **Train a reviewed pilot.** Submit actual human decisions, produce/validate a new v2 SFT release, record inputs/config/template/seed and checkpoint IDs, then launch a short GPU pilot using a separately reviewed config. Do not substitute the current draft pilot or legacy fixtures.
6. **Evaluate comparably.** Predict with base+adapter on identical frozen cases/settings; use `rsec evaluate --baseline reports/base.json ...` with matching condition sidecars. Add independent human rubric evaluation bound to immutable outputs; current case-rating aggregation alone cannot certify model quality.
7. **Tune hyperparameters.** Use train/eval and public development only; compare sequence1024/2048 first at microbatch1 with measured memory, then test4096/8192 only if feasible. Record rank/accumulation/precision/learning-rate/seed changes. Do not inspect hidden final labels for tuning.
8. **Specialize only after gates pass.** Approve source rights, technical examples, independent gold, CUDA/NF4, resume/export and regression conditions, then run the separately authorized specialization. Register no model as TESTED without evidence.
9. **Export GGUF.** Preserve a trusted base and adapter; merge/export Safetensors then GGUF Q4_K_M using reviewed llama.cpp and new destinations. Validate tokenizer/template/tensor inventory/hashes and compare against unquantized outputs. The old tiny CPU GGUF test is infrastructure history only.
10. **Infer locally.** Validate Transformers and actual native llama.cpp first; validate Ollama/Modelfile separately. Check local offline loads, GPU selection and memory. Heterogeneous 4070/3060 requires its own physical test: separate 12 GB allocations, topology/P2P/NCCL checks and DDP/FSDP layouts, not one contiguous 24 GB pool.
11. **Evaluate regressions.** Compare base, adapter, merged, quantized and previous versions on the same frozen suites and reviewer protocol; record false positives/negatives, uncertainty, bilingual performance and semantic hallucination assessments. Hold release on regressions or incomparable conditions.

No steps above are physical completion claims. Do not provision RunPod or paid APIs without explicit authorization. Existing Colab/Kaggle/notebook and GPU profiles are candidate procedures, not executed sessions. Full plan: [GPU_VALIDATION_PLAN.md](GPU_VALIDATION_PLAN.md); data review: [DATASET_REVIEW_GUIDE.md](docs/DATASET_REVIEW_GUIDE.md).
