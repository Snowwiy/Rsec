# Revisión · Fase 03-A · v0.3.0-alpha.2

Revisar los resultados locales y cada workflow del encabezado del [PR #7](https://github.com/Snowwiy/Rsec/pull/7). Verificar escaneo histórico de Gitleaks, selección por UUID, detención del propio proceso y privacidad de informes. Los resultados técnicamente aprobados corresponden a las cargas publicadas en el informe. Un Transformer completo bajo FSDP, el soporte de agente y la especialización conservan sus condiciones. La aprobación de infraestructura es independiente de los gates de modelo y corpus. [Evidencia de pruebas](TEST_RESULTS.md)

| Veredicto | Estado | Alcance |
|---|---|---|
| RTX 4070 VALIDATION | VALIDATED | CUDA, BF16/FP16 y fixture individual |
| RTX 3060 VALIDATION | VALIDATED | CUDA, BF16/FP16 y fixture individual en WSL2 |
| CUDA READINESS | VALIDATED | PyTorch cu128 en la distro |
| NF4 READINESS | VALIDATED | NF4 doble en ambas tarjetas |
| QLORA READINESS | PASS WITH CONDITIONS | Capa técnica, actualización y recuperación probadas |
| NCCL READINESS | VALIDATED | Comunicación de datos SHM. P2P directo no soportado |
| DDP READINESS | VALIDATED | Fixture con dos ranks y recuperación, sin ventaja de velocidad medida |
| FSDP READINESS | PASS WITH CONDITIONS | FSDP 1 con NF4/BF16, recuperación y exportación. Transformer completo pendiente |
| DUAL-GPU INFERENCE | VALIDATED | WSL2, GGUF 14B, reparto de capas 2:1 y 1:1 |
| THERMAL STABILITY | PASS WITH CONDITIONS | Cargas breves observadas. Juego concurrente pendiente |
| GOOSE GPU INTEGRATION | PASS WITH CONDITIONS | Texto en la 3060 y contrato de herramientas del endpoint. Uso de herramientas reales por Goose pendiente |
| MODEL BASE READINESS | BLOCKED | Falta un paquete causal local completo con licencia y revisión verificadas |
| DATASET READINESS | BLOCKED | Cero aprobaciones humanas y cero gold independiente |
| TRAINING READINESS | BLOCKED | Siguen vigentes los gates de modelo, corpus y evaluación |

La ruta llama.cpp nativa Windows para la 3060 quedó **FAILED** por visibilidad del runtime. La ruta WSL2 se validó sin alterar el controlador. [Benchmark físico](MULTI_GPU_BENCHMARK.md)

---

# Revisión de integración · Fase 02-B

Revisa [PR #4](https://github.com/Snowwiy/Rsec/pull/4) primero para corregir dev. Verifica que Gitleaks siga escaneando todo el historial con el mismo detector, salida y redacción. La excepción exacta se probó contra otro valor en la misma ruta y con las coincidencias conocidas en otra ruta.

Revisa [PR #5](https://github.com/Snowwiy/Rsec/pull/5) después. Comprueba que contiene la historia auditada de Fase 02-A, el código nuevo y el mismo hotfix como ancestro. Mantén 64 candidatos SFT y 32 de CyberBench sin ninguna promoción automática. Revisa los controles de autoridad local y las limitaciones de rúbricas y GPU. Verifica los tres checks del commit que se vaya a integrar.

La programación y la ciberseguridad conservan suites y permisos propios. Los datos de entrenamiento requieren autorización y revisión experta en ambos tracks. Evalúa CodeBench y CyberBench contra el mismo modelo base antes de cualquier promoción. Los planes de GPU, modelo y corpus siguen sujetos a sus gates. No se ha iniciado entrenamiento especializado.

Revisión histórica de Fase 02-A a continuación.

---

# Review before merge — Phase 02 dependent PR

[PR #2](https://github.com/Snowwiy/Rsec/pull/2) is a **draft infrastructure review** based on audited PR #1. **DATASET READINESS: FAIL; TRAINING READINESS: NOT READY.** Do not interpret code integration as corpus/model/hardware approval. No merge or specialized training was performed.

## Integration gates

- Review the22 source policies, separate permissions and three scoped CVE snapshots. No external SFT source or raw payload redistribution is enabled; MIT does not relicense upstream assets.
- Review actual counts99 processed/0 expert-approved/0 rejected/0 quarantined/99 pending, distinguishing64 SFT, 32 public dev/regression and3 reference indexes. No500–1,000 approved pilot or independent expert/private gold exists.
- Inspect Candidate roles, JSON target consistency, metadata exclusion from tokens, review hash/policy bindings, partial-review safe failure, inventory/symlink checks and source/code/translation/reservation isolation. Review the legacy-path boundary; it remains for foundation fixtures, not expert promotion.
- Inspect tests:200 passed,94.02% statementcoverage, core 189 passed/11 MLdeselected. Real CPU TRL/tokenizer checks are distinct from hypothetical review/transport controls. No original tests removed or new coverage exclusions added.
- Inspect scanner configuration: every default rule retained; only two exact verified public tokenizer hashes in two paths are exempted using AND. Initial CI failed on 4 false positives; corrected history scan and synthetic negative control pass. Review CPU dependency audit's torch+cpu skip and unresolved GPU graph.
- Verify **all three final-head** CPU quality/offline ML/security workflows. Corrected code head runs passed; they cannot substitute for checks on later reporting heads.
- Read residual limits in BENCHMARK_REPORT.md and TRAINING_READINESS.md: case ratings lack prediction/model binding, no real expert gold, semantic metrics or dynamic remediation, lexical/privacy/poison heuristics and unsigned/operator trust roots.

First review/integrate PR #1 into dev with its Phase 01-B conditions, then verify audited ancestry/content, retarget PR #2 to dev and rerun CI. Current target is `feat/rsec-foundation-v0.1.0` so Phase01 changes are not duplicated. Preserve history; after squash/rebase use content comparison and a normal conflict-resolution merge where needed, never force push or delete prior work. No automatic merge to dev/main.

## Gates before real training

Actual bilingual qualified review and source-specific rights; independently authored/adjudicated frozen gold outside the tuning loop; reviewed pilot with meaningful depth/diversity; physical RTX4070/CUDA/NF4, memory, optimizer resume/export and regression evidence. Advanced/expert need two reviewers. Preserve separate 12 GBallocations for4070/3060. Unsloth remains BLOCKED; audited main stack and training code/pins unchanged. Read GPU_VALIDATION_PLAN.md and the exact 11later steps in TRAINING_READINESS.md.

Historical foundation verdict remains **PASS WITH CONDITIONS** for PR #1; it does not override the current Phase 02 corpus FAIL. The missing expert/private benchmark is a confirmed exit gap, not something passing CI can waive.
