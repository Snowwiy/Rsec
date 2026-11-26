# Rsec — auditoría independiente, Fase 01-B

Fecha: 2026-11-26. Versión: v0.1.0-alpha. Objeto: [PR #1](https://github.com/Snowwiy/Rsec/pull/1).

## Resumen ejecutivo y veredicto

**PASS WITH CONDITIONS** para integrar los fundamentos en `dev` después de revisión humana y CI del nuevo head. **No** es aprobación de un modelo especializado, de CUDA, de soporte multi-GPU ni de una publicación de pesos. La Fase 02 puede comenzar como trabajo de derechos, curación y evaluación independiente; el entrenamiento real sigue bloqueado por los controles de datos y hardware descritos abajo.

La inspección independiente reprodujo las 39 pruebas y el 75.15 % inicial. Las pruebas existentes omitían fallos reales en longitud de SFT, aislamiento de preguntas de benchmark, CLI y evaluación. Se corrigieron sin sustituir los módulos funcionales. La nueva suite ejecuta **97 pruebas**, con **91.34 % de cobertura de sentencias**; los dobles de APIs externas se distinguen de ejecución real en CPU y de pruebas físicas pendientes.

## Estado inicial comprobado

- Head: `48709e49c2650793f8af792344988552151de158`; rama `feat/rsec-foundation-v0.1.0`; base `dev` en `f42f893948cc2388d4025920d545e4dcc74cf5a9`.
- PR abierto, borrador, sin merge; 85 archivos modificados, 4,553 adiciones y 2 eliminaciones al inicio.
- Commits: `15a2326` fundamentos; `4d9c738` documentación/notebooks; `48709e4` instalación del paquete en seguridad CI.
- GitHub confirmó éxito en [ML CPU](https://github.com/Snowwiy/Rsec/actions/runs/45813465355), [calidad CPU](https://github.com/Snowwiy/Rsec/actions/runs/45813465401) y [seguridad](https://github.com/Snowwiy/Rsec/actions/runs/45813465390). Son ejecuciones del head inicial, no evidencia anticipada del nuevo head.
- La copia local coincidía con ese head y estaba limpia. No se tomó `dev` como base del trabajo. No se hizo force push ni merge.

## Archivos y arquitectura revisados

Se revisaron todos los módulos `src/rsec/*.py`: CLI, config, data, knowledge, download, train, evaluate, predict, inference, export, environment, tracking, utils, errors, interfaces e inicialización; además del nuevo control `artifacts.py`. Se inspeccionaron los tres workflows, scripts de instalación/validación/GGUF, todos los YAML de configuración/modelos/perfiles/Accelerate, ambos notebooks y los requisitos directos y lock CPU.

También: README.md, README.es.md, AGENTS.md, HANDOFF.md, TEST_RESULTS.md, IMPLEMENTATION_REPORT.md, REVIEW_BEFORE_MERGE.md, CHANGELOG.md, LICENSE, MODEL_CARD.md, ROADMAP.md; `docs/*.md` y ADR 001; suite de benchmarks, muestras sintéticas, fixtures y pruebas de unidad/integración. El diff y la lista inicial se contrastaron mediante GitHub y Git local. La lista completa final queda en `audits/phase01b/validation.json`.

La modularidad es adecuada para una alpha: dependencias ML diferidas, datos separados de entrenamiento/evaluación, errores propios sin texto privado, configuración Pydantic y registro local inmutable. Se conservan el layout `src/rsec`, MIT y los módulos existentes. No se justifica cambiar de framework ni añadir servicios MLOps externos en esta fase.

## Hallazgos confirmados y correcciones

| ID | Severidad | Evidencia al inicio | Corrección / estado |
|---|---|---|---|
| A01 | High | `train.py` medía `len(apply_chat_template(...))`; en Transformers 5.24.1 el valor por defecto es estructurado, no la lista de tokens. Un ejemplo largo no activaba el control. | `return_dict=False`, control de prefijo y objetivo; regresiones reales con TRL, sobrelongitud, varios turnos y pérdida manual. TESTED CPU. |
| A02 | High | Una pregunta idéntica al benchmark, con otra respuesta y grupo, produjo 13 aceptados y 0 rechazos frente a los 12 originales. | Exclusión por preguntas además de conversación y procedencia; unión de preguntas relacionadas entre splits; revalidación de releases. TESTED. |
| A03 | High | README documentaba `rsec predict`, pero argparse rechazaba el comando aunque existían dispatch y función. | Subcomando registrado y probado desde CLI. TESTED. |
| A04 | Medium | PEFT 0.22.0 ofrece fallback a `adapter_model.bin`; prohibir pickle en el modelo base no protegía la ruta del adaptador. | Inventario local Safetensors, rechazo de pickle/symlinks y LoRA causal antes de cada loader; salida final sin `training_args.bin`. No se afirma haber demostrado RCE. TESTED. |
| A05 | Medium | `score()` derivaba etiquetas del subconjunto. Una predicción `benign` válida frente a un único caso `vulnerable` recibía schema=0 y perdía su FP por clase. | Esquema fijo para global/dominios/idiomas; cálculo manual de precision/recall/F1/FP/FN. TESTED. |
| A06 | High | El gate de regresión exigía solo benchmark idéntico; permitía comparar distintas condiciones y no exigía esquema completo. | Sidecar con hashes de predicciones, benchmark, instrucción, plantilla/sistema y condiciones; contrato de evaluación idéntico; gate requiere esquema completo y sin ausencias. TESTED. |
| A07 | High | Metadata del wheel Unsloth 2026.11.12 contradice tres pins del stack: Transformers, TRL y datasets. | Backend BLOCKED antes de importarlo; pin incompatible retirado de instalación opcional activa. No se degradaron dependencias auditadas para forzarlo. |
| A08 | High | FSDP FP16 usaba almacenamiento FP16 y preparación que cambia capas a FP32; también elegía `paged_adamw_8bit`, cuyo guardado FSDP-QLoRA está documentado como problemático por PEFT. | FP16 AMP usa almacenamiento/modelo FP32; no se aplica el upcast de preparación de single-GPU a FSDP; AdamW en FSDP; versión FSDP1 explícita; precisión DDP coherente. GPU VALIDATION PENDING. |
| A09 | Medium | Límite de 10,000 registros y 64 MiB no acotaba el coste cuadrático de SequenceMatcher. | Presupuesto conservador acumulado de productos de longitudes; fallo explícito antes de publicar al agotarlo. No se convierte en cuarentena silenciosa. TESTED. |
| A10 | Medium | CSV se procesaba con `splitlines()`, eliminando saltos dentro de campos citados. Campos ausentes podían generar excepciones sin clasificación. | `StringIO`, rechazo de fila malformada y prueba multilínea. TESTED. |
| A11 | Medium | Ingesta knowledge no filtraba datos sensibles en procedencia; `text` no textual fallaba sin cuarentena. Revalidación SFT omitía repetir screening de metadata. | Metadatos acotados y filtrados, cuarentena sin contenido, revisión de releases y límites de registros. TESTED. |
| A12 | Medium | Firma de entrenamiento incremental vinculaba la ruta del adaptador, no sus bytes. Manifest de checkpoint no rechazaba archivos adicionales. | Huella del adaptador en firma; inventario exacto y rechazo de symlinks al reanudar. La autenticidad sigue siendo responsabilidad del operador. TESTED. |
| A13 | Low | Marcadores de procedencia permitían coerción; adquisición aceptaba valores truthy en `reviewed`. YAML no mapping fallaba de forma poco clara. | Booleanos estrictos, licencia vacía/no verificada rechazada, validación de mappings y opciones LoRA. TESTED. |
| A14 | Low | Opciones de distribución inválidas o adaptadores ignorados podían llegar al runtime; redirecciones del servicio local no estaban bloqueadas. | Validación de parámetros y compatibilidad de backend; loopback sin proxy ni redirección. TESTED como contrato con dobles, no ejecución de motores. |
| A15 | Low | Notebooks fijaban el commit previo a correcciones y descargaban una snapshot que podía contener symlinks. | Revisión inmutable auditada y descarga a `local_dir` materializado; proveedores siguen pendientes. |

No se confirmó un hallazgo Critical. A07 se resuelve deshabilitando de forma explícita la combinación incompatible; no se entrega una integración Unsloth funcional.

## Contraste de capacidades

| Área | Estado después de auditoría | Límite |
|---|---|---|
| CLI, esquema/procedencia, cuarentena, hashes, splits y screening | TESTED CPU | Heurísticas y corpus sintético; no revisión legal automática ni privacidad completa |
| JSON/JSONL/CSV/Parquet | TESTED CPU | Parquet real incluido; presupuestos pequeños, no escala web |
| HTTPS/HF externo | IMPLEMENTED; contratos TESTED | Transportes/streaming dobles; no colección real nueva validada |
| SFT, LoRA, máscaras, pérdida, resume y fusión | TESTED CPU | Tiny aleatorio; optimizador pasa de step 2 a 3; no capacidad de ciberseguridad |
| Entrenamiento incremental | IMPLEMENTED; integridad reforzada | Ruta completa CUDA y replay real no ejecutados |
| QLoRA NF4, BF16/FP16, DDP/FSDP y OOM físico | GPU VALIDATION PENDING | Ajustes de código/documentación no equivalen a lanzamiento |
| Unsloth | BLOCKED | Conflictos comprobados de dependencias |
| Evaluación determinista y regresión | TESTED | No mide alucinaciones semánticas ni éxito real de remediación |
| Safetensors/adaptador/merged e inferencia Transformers | TESTED CPU | Logits de adaptador/fusión comparados con tolerancias |
| GGUF Q4_K_M y llama.cpp nativo | TESTED CPU | Mismo hash final que la evidencia histórica, plantilla preservada y generación mínima |
| Ollama / llama-cpp-python | IMPLEMENTED, contratos TESTED | Motores no instalados ni ejecutados |
| Notebooks, Windows, WSL2 | IMPLEMENTED / inspección estática | Sin sesión de proveedor o instalación física |
| Registro local | TESTED | TESTED es una declaración del operador; no firma de un evaluador |
| RAG, SENTRA, gold corpus amplio, evaluador semántico y runner dinámico aislado | NOT IMPLEMENTED | Alcance futuro explícito |

## Pruebas y cobertura

Los comandos, resultados y límites están en TEST_RESULTS.md y MLOPS_VALIDATION.md. La suite inicial volvió a pasar completa antes de modificarla. La final se ejecutó offline, sin descargas de pesos. No se excluyeron módulos para aumentar cobertura. Los protocolos futuros permanecen en el denominador; sus líneas sin uso no se convierten en funcionalidad mediante pruebas triviales.

Cobertura anterior: 75.15 %. Posterior: 91.34 %. Datos, adquisición, knowledge, evaluación, controles de artefactos, inferencia y CLI superan el 90 % de sentencias; entrenamiento conserva ramas CUDA/distribuidas pendientes. La cobertura de contratos simulados no demuestra ejecución física. Ver porcentajes exactos en el registro de validación.

## Deuda técnica y riesgos residuales

- Deduplicación lexical cuadrática: ahora acotada, aún requiere shards y familias humanas; no detecta equivalencia semántica general. Preparar nuevas releases tras cambiar reglas; nunca modificar releases previas.
- `predict` carga el modelo por caso; coste alto para 7B. Separar sesión/modelo y batching es mejora futura medible, no requisito para afirmar calidad de esta alpha.
- Dependencia `scikit-learn` declarada en requirements-data sin uso en el código actual; añade su grafo numérico al entorno. Retirarla y regenerar un lock mínimo es deuda Low; no se altera el entorno congelado usado para comparar esta auditoría. Hay además una guarda FSDP/backend redundante en config, sin impacto funcional.
- La fusión exige un base local y comprueba tensores/NaN, pero no autentica que un base externo de formas compatibles sea exactamente el usado por un adaptador externo. Los logits se verificaron solo con el par correcto del fixture; un release real debe vincular y revisar base/revisión/tokenizer, no aceptar safe_merge como autenticación.
- Defaults relativos al checkout y configuraciones fuera del wheel: operación portable requiere checkout raíz. No se promete que instalar únicamente el wheel aporte perfiles/notebooks.
- Falta lock CUDA/Unsloth validado. Pins sin hashes de distribución no autentican la supply chain. El lock CPU sin vulnerabilidades conocidas no audita el kernel, driver ni motores opcionales.
- OOM durante inicialización, antes de crear Experiment, solo falla hacia el llamador; no garantiza un registro de experimento. Después de crear el trainer se registra el tipo de error, sin prometer checkpoint extra.
- Checkpoints con optimizador son estado local confiable. Firmas SHA-256 no autentican al remitente. FSDP puede usar layout distinto al checkpoint CPU y será rechazado si no satisface el contrato.
- El registro permite una aserción manual TESTED; aprobación humana y evidencia independiente siguen necesarias. No hay firma remota ni servicio central.
- Filtrado de PII/secretos/poisoning, egress HTTPS y servicio Ollama local mantienen los límites expuestos en SECURITY_AUDIT.md.

## Preparación de Fase 02 y recomendación de merge

Se puede comenzar revisión por fuente, curación bilingüe, revisión humana y construcción de gold externo congelado. La lista de fuentes está vacía deliberadamente; el corpus útil todavía no existe. No se inicia entrenamiento real desde esta auditoría.

Recomendación: integrar en `dev` únicamente como fundamentos alpha, tras CI del head final y revisión humana de los cambios de seguridad/datos/SFT. Mantener el PR en borrador mientras esa decisión esté pendiente. No integrar automáticamente en `main`. Antes de entrenar o publicar un modelo: completar DATASET_READINESS.md, GPU_VALIDATION_PLAN.md, comparación base/adaptador/exportado y gates de regresión por dominio/idioma. **PASS WITH CONDITIONS no elimina esos bloqueadores.**
