# Rsec — validación MLOps, Fase 01-B

Fecha: 2026-11-26. Evidencia estructurada: `audits/phase01b/validation.json`. La suite inicial se ejecutó sin cambios antes de ampliar los tests.

## Matriz de evidencia

| Componente | Tipo de evidencia realmente ejecutada | Estado |
|---|---|---|
| Config/CLI, releases, manifests y registro | Archivos reales y pruebas negativas locales | TESTED CPU |
| CSV y Parquet | Lectura real, contenido multilínea y round trip Arrow | TESTED CPU |
| HTTPS/HF | Dobles de transporte/streaming, rangos, hash, presupuesto y errores | Contratos TESTED; fuentes externas reales pendientes |
| SFT/LoRA | Tiny Qwen2 aleatorio, TRL y PEFT reales, optimización real | TESTED CPU |
| Máscaras/padding/pérdida | Batch real TRL multi-turn; comparación de labels y CE manual | TESTED CPU |
| Resume | Checkpoint real: optimizer step 2 → 3, scheduler/RNG presentes, tampering rechazado | TESTED CPU |
| Fusión | Safe merge real; logits adaptador/fusión comparados con atol=1e-5, rtol=1e-4 | TESTED CPU |
| Inferencia/benchmark | Generación real offline tiny y scoring; fixtures de referencia separados | TESTED CPU; sin capacidad especializada |
| GGUF | Converter y quantizer nativos, Q4_K_M, template y generación | TESTED CPU |
| Ollama y llama-cpp-python | Dobles del contrato API y validación de opciones | IMPLEMENTED; motores no ejecutados |
| QLoRA/BitsAndBytes/CUDA/DDP/FSDP/Unsloth | Inspección, configuración, documentación/metadata; guardas con dobles | GPU VALIDATION PENDING; Unsloth BLOCKED |
| Colab/Kaggle/Windows/WSL2 | Lectura de scripts/celdas y sintaxis; no sesión de proveedor | Pendiente |

## Semántica del entrenamiento

El modo por defecto convierte cada conversación a prompt + última respuesta de assistant. Solo esa respuesta final es objetivo; respuestas previas quedan en el contexto. El modo assistant-only usa máscaras de generación del template y aprende las respuestas assistant marcadas. Los tests comprueban ambos sobre varios turnos, EOS, exclusión de padding y correspondencia con entropía cruzada causal desplazada. El control de longitud cuenta la lista real de tokens y rechaza sobrelongitud antes de la tokenización TRL. Templates sin máscaras/objetivos o con prefijo incompatible fallan; no se inventa un formato ChatML.

La evidencia real usa el tokenizer tiny creado por Rsec. El tokenizer oficial Qwen se conserva y verifica en GGUF; SFT completo de Qwen 7B y compatibilidad de cualquier otro modelo requieren su propia prueba. Target modules son configurables pero no se garantiza que existan en toda arquitectura. La configuración FSDP1 limita el wrapper a Qwen2DecoderLayer.

NF4/double-quant, precisión, acumulación y checkpointing están implementados. Smoke usa CPU y acumulación=1 explícita; no demuestra consumo/máscaras CUDA de un modelo real. `warmup_steps` admite proporción en Transformers 5.24.1; se comprobó la implementación instalada y no se aplicó una corrección basada en APIs antiguas.

Reanudar valida modelo, configuración, dataset y contenido del adaptador inicial. Extender `max_steps` restaura el estado pero cambia el horizonte del scheduler; no se promete equivalencia bit a bit con un entrenamiento ininterrumpido que originalmente tuviera otro horizonte. Cargar un adaptador como inicio incremental crea un optimizador nuevo, con replay/regresión exigidos por el operador.

Errores del trainer registran tipo y bandera OOM; no garantizan un nuevo checkpoint después de OOM/kill. El registro de Experiment se crea después de carga/preparación: un fallo anterior puede no generar run.json. FSDP necesita comprobar físicamente layout del optimizador, coordinación de ranks y gather; el contrato CPU no prueba esos estados.

## Evaluación y comparabilidad

Las etiquetas válidas se mantienen constantes en todos los subconjuntos. Macro F1 incluye todas las etiquetas configuradas y usa cero para F1 indefinido; precision/recall por clase con denominador cero se representan como null. Micro F1 no debe confundirse con accuracy cuando faltan respuestas o hay etiquetas inválidas. Accuracy mide etiqueta, no calidad de respuesta, y se reporta separada del esquema. Duplicados/IDs desconocidos fallan; ausencias cuentan como errores.

CWE exact match compara listas ordenadas, no corrección de justificación. Unsupported-reference rate compara referencias lexicales permitidas, no todas las afirmaciones ni alucinación semántica. No existe juez LLM ni ejecución dinámica del código generado. Un modelo que siempre omita citas puede evitar referencias no permitidas sin demostrar mejor evidencia. No se presenta eso como calidad superior.

`predict` escribe `PREDICTIONS.meta.json` con hashes del benchmark/predicciones y condiciones. `evaluate --baseline` exige contratos de generación y evaluación idénticos, plantillas/sistema registrados, esquema completo y cero ausencias. Un archivo manual sin sidecar se puede puntuar pero no aprobar como regresión comparable. Los sidecars son evidencia local no firmada; un operador puede falsificarlos. El chequeo no normaliza hardware/latencia, por lo que comparar rendimiento exige además hardware y versiones iguales. Ollama no expone aquí una plantilla verificable: su evaluación sigue disponible, pero el gate queda bloqueado sin ese dato.

## Artefactos y reproducción nativa

Se repitió `scripts/validate_gguf.py` con llama.cpp `b671865c7bd44c8c2d4709b5f707bd55f7f612fd`, CPU, sin descargar pesos. El primer intento offline no encontró la cache HF; falló, sin afirmarse éxito. Se añadió `--tokenizer` para utilizar un directorio local previamente revisado y se repitió en un destino nuevo.

Resultado Q4_K_M: 60,040,704 bytes; SHA-256 `ba72a4435a6c4d03c549154aa61010fbc8acfcf53fe9f607c1bb07615e16b6d7`, idéntico al histórico. Se inspeccionó metadata GGUF: plantilla idéntica al tokenizer local, 15 tensores, sin fallback de cuantización reportado; completion nativo terminó correctamente con cuatro tokens solicitados. La comparación no mide calidad ni degradación semántica de un modelo entrenado. Modelfile generado; `ollama create/run` no ejecutados.

Adaptadores/exportaciones preservan tokenizer/template y hashes; se rechazan pickle/symlinks y cambios de inventario. Bases de Hugging Face destinadas a loaders locales deben descargarse a un `local_dir` materializado: no pasar directamente una snapshot de cache con symlinks. Los notebooks ya usan ese patrón. Fallos de exportación dejan destino parcial y nunca manifest de éxito.

## Registro y continuidad

Experiment guarda config, dataset hash, revisión Git, hardware y métricas locales JSONL/CSV/Markdown/SVG. No se añadió tracking SaaS. El registro es append-only por ID; activación/rollback revisan hashes y estado TESTED manual. No hay evaluación automática que autorice releases por sí sola.

AGENTS.md, HANDOFF.md, informes, tests y pins de notebook permiten retomar trabajo en el head publicado. Los informes anteriores se conservan como historia, con aclaraciones de auditoría. La instalación core sin torch se volvió a probar. RAG/SENTRA siguen como Protocols, sin un servicio o conocimiento fingido.

Safe merge detecta incompatibilidades de forma y valores no finitos; no certifica procedencia del base externo ni calidad de una combinación de pesos de igual forma. El operador debe usar exactamente el base/revisión/tokenizer del entrenamiento; la prueba real valida ese par correcto, no adaptadores arbitrarios.
