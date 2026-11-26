# Rsec — preparación de datos para Fase 02

Fecha: 2026-11-26. **Preparado condicionalmente para comenzar curación; NO preparado para entrenamiento especializado.** La lista de fuentes externas sigue vacía. Solo existen 12 conversaciones sintéticas y 10 fixtures de benchmark, no un corpus de ciberseguridad validado.

## Lo comprobado

Esquema estricto de conversaciones alternas y metadatos, normalización NFKC, booleanos de revisión/synthetic estrictos, deduplicación lexical, familias por procedencia/preguntas/contenido, splits no vacíos y separación train/eval/test. El filtro excluye preguntas del benchmark incluso si cambia la respuesta o se declara otra familia. La validación repite aislamiento, propósito, contenido y screening de metadata después de verificar hashes.

Se probaron JSON, JSONL, CSV multilínea y Parquet real; entradas inválidas se rechazan o van a cuarentena de hashes y motivos. Fallos globales de formato/presupuesto abortan sin aprobar una release. Los manifests registran inputs/benchmarks/hashes/seed y ficheros resultantes. Para inputs ordenados y seed iguales, los bytes de cada split se repiten; timestamps/manifests completos de dos ejecuciones no son idénticos por definición.

Secretos y PII reconocidos no entran en cuarentena textual ni logs propios. Anonimización solo sustituye patrones de email/IP/teléfono en contenido; metadata sensible se rechaza. Knowledge/RAG se mantiene separado, `trusted=False`; documentos no se convierten automáticamente en ejemplos SFT ni se ejecutan.

## Gates antes de aceptar un corpus real

| Gate | Evidencia exigida | Estado actual |
|---|---|---|
| Derechos por fuente | Licencia/versión, URL oficial, fecha, condiciones de uso/redistribución y decisión humana | BLOCKED para corpus real; no hay fuente aprobada |
| Procedencia y autenticidad | Snapshot/hash independiente, propietario/origen y familias documento/repositorio/CVE | Infraestructura TESTED; revisión real pendiente |
| Privacidad | Revisión humana, minimización de datos, política de retención y exclusión de material privado | Heurísticas TESTED; revisión corpus pendiente |
| Correctitud | Respuestas verificadas por expertos, referencias y incertidumbre, distinción de hipótesis | No existe gold amplio |
| Español/inglés y dominios | Distribuciones y revisión humana por idioma/appsec/SOC/DFIR/hardening | Solo fixtures sintéticos |
| Dedupe/escalabilidad | Shards bajo presupuesto, grupos de origen revisados y análisis semántico adicional | Baseline lexical acotado; semántico pendiente |
| Independencia de benchmark | Listado completo reservado, hashes, grupos externos y preguntas protegidas | Suite sintética aislada; suites externas pendientes |
| Liberación reproducible | IDs inmutables, inputs ordenados, seed/config/tool versions, revisión de reportes | Mecanismo TESTED; release real pendiente |
| Incremental/replay | Fuentes antiguas por el mismo pipeline, benchmark congelado y regresión por dominio | Implementado, no probado con corpus real |

No declarar `reviewed=true` únicamente porque el pipeline no encontró un patrón. Los identificadores de licencia no son un validador jurídico; una URL no prueba origen. La MIT de Rsec no relicencia publicaciones, modelos o datos de terceros.

## Procedimiento de Fase 02

1. Seleccionar pocas fuentes oficiales y revisar derechos antes de configurar adquisición; no instalar scripts de datasets ni abrir archivos como ejecutables.
2. Congelar un benchmark externo y gold revisado por personas antes de seleccionar ejemplos SFT. Mantener familias completas y versiones fuera de entrenamiento/replay.
3. Guardar material privado y registros de revisión fuera del repositorio público. Adaptar esquemas externos explícitamente a Record; no añadir licencias o etiquetas sintéticas por inferencia silenciosa.
4. Curar shards pequeños. La deduplicación mantiene coste cuadrático y puede abortar por presupuesto aun por debajo de 64 MiB o 10,000 registros. Un tamaño permitido no implica capacidad de cómputo suficiente.
5. Preparar una release nueva, incluyendo todas las suites reservadas. El default reservado solo se aplica a CLI; quienes llamen `prepare()` deben pasar sus benchmarks explícitamente.
6. Revisar dataset_quality_report, motivos de rechazo, distribuciones, grupos y contenido aprobado; verificar hashes y no-leakage mediante `rsec data validate`.
7. Mantener test congelado. Volver a dividir una mezcla de replay con fuentes nuevas puede mover familias; no usar la nueva división como sustituto del mismo test externo para comparación longitudinal.
8. Obtener revisión humana de privacidad, derechos y correctitud antes de entregar el corpus al plan GPU. No iniciar entrenamiento en esta fase.

## Límites que impiden interpretar fixtures como conocimiento

Las muestras y predicciones de referencia son authored synthetic fixtures y llevan su procedencia explícita. Puntuarlas contra sus etiquetas solo verifica el scorer. Ninguna prueba demuestra comprensión de vulnerabilidades, recuperación de evidencias, seguridad adversarial de un modelo ni superioridad sobre un base.

La detección de inyección indirecta es heurística y no cubre ataques multilingües/parafraseados/codificados. Hashes, filtros regex y límites de esquema no resuelven data poisoning ni garantizan anonimato. No existe un validador semántico automático que convierta esos límites en PASS.
