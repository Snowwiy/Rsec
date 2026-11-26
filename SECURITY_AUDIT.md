# Rsec — auditoría defensiva de seguridad, Fase 01-B

Fecha: 2026-11-26. Alcance: código e historial del PR #1, dependencias CPU, datos, artefactos y CI. No se ejecutaron exploits, documentos, código generado ni checkpoints de terceros. No se contrataron servicios.

## Resultado

No se detectaron credenciales mediante Gitleaks ni vulnerabilidades conocidas en el lock CPU mediante pip-audit en esta ejecución. Esto no certifica ausencia de secretos, PII o vulnerabilidades. Los hallazgos A04, A09, A11–A14 y las correcciones se detallan en INDEPENDENT_AUDIT.md.

| Superficie | Comprobación y control | Riesgo residual |
|---|---|---|
| Modelos remotos | `trust_remote_code=False`, revisión completa fijada, base Safetensors | Librerías/tokenizer/nativo aún procesan formatos no confiables; no se deben instalar repositorios arbitrarios |
| Adaptadores | Rechazo de `.bin/.pt/.pth/.pkl/.pickle`, symlinks e inventario inapropiado antes de PEFT | No equivale a certificar pesos benignos; SafeTensors no elimina poisoning |
| Optimizer resume | Firma modelo/datos/config/adaptador, inventario exacto, hashes y rutas confinadas | Estado `.pt` solo de origen local confiable; reemplazar manifest y archivos vence hashes no firmados |
| Exportaciones | Validación de tensores, no-clobber, RAM/disco, manifiestos de tamaño/hash revalidados | Header GGUF no prueba semántica ni calidad; converter local revisado sigue siendo código ejecutable confiado |
| Rutas | IDs restringidos, manifiestos confinados, symlinks rechazados, escritura atómica | No es sandbox frente a un atacante local concurrente con permisos equivalentes; existen límites TOCTOU |
| HTTPS | Host allowlist, HTTPS sin credenciales, direcciones globales, redirects revisados, proxy ambiental desactivado | DNS rebinding no completamente resuelto; usar restricciones de egress y editores revisados |
| Datos | Esquema, revisión/licencia estricta, NFKC, heurísticas, cuarentena de hashes, metadatos filtrados | Regex no anonimiza toda identidad ni detecta todos los secretos, idiomas, codificaciones o inyecciones indirectas |
| Documentos no confiables | Knowledge separado de SFT; no eval/exec/shell de documentos; `trusted=False` | Inyección semántica/poisoning requiere revisión experta; no se implementó RAG que garantice defensa en runtime |
| Disponibilidad | 64 MiB, límites de filas y presupuesto de comparación; detección de Parquet decodificado | Metadatos/nested allocations y parsers nativos no constituyen límites de RAM/proceso del sistema operativo |
| Inferencia | Paths locales, safetensors; Ollama loopback sin proxy ni redirects; límites de respuesta y parámetros | Un servicio local puede reenviar datos si su operador lo permite; el nombre sin `cloud` no prueba aislamiento de red |
| Logs | Cuarentena sin contenido; errores de terceros se suprimen en CLI; métricas sin prompts | Diagnósticos de librerías/hardware y scripts pueden incluir rutas; revisar antes de publicar logs; stdout de librerías no está aislado globalmente |
| Registro | Entradas inmutables, artefactos reales con hashes, activación exige TESTED | La afirmación TESTED es manual; no sustituye revisión externa ni autorización de release |

## Supply chain

Se ejecutó `pip-audit --disable-pip --no-deps -r requirements-cpu-test.lock`: **sin vulnerabilidades conocidas**. `pip check`: **sin requisitos rotos** en el entorno CPU instalado. El lock no se generó de nuevo ni se degradó para conseguir compatibilidad opcional.

El wheel oficial `unsloth-2026.11.12-py3-none-any.whl`, descargado sin instalación/ejecución, tiene SHA-256 `96b409b63a1a39f34d78cd3747977b3f54767b2ab73c50b15ce309b1cb1f0ecc`. Su metadata requiere `transformers<=5.17.0`, `trl<=1.15.0` y `datasets<5.0.0`; Rsec fija 5.24.1, 1.19.0 y 5.0.1. Es una incompatibilidad real de resolución; el backend queda BLOCKED. No se fuerza `--no-deps` para ejecutarlo.

GPU, BitsAndBytes, driver/CUDA, Ollama y bindings llama-cpp-python no disponen de auditoría transitiva física completa en esta entrega. La comprobación nativa utiliza un checkout limpio e inmutable de llama.cpp; dependencias de conversión se registran aparte.

Los pins CPU sin `--require-hashes` protegen versiones, no la autenticidad de cada wheel. Instalar desde índices oficiales y registrar los hashes/lock de cada entorno de validación sigue siendo necesario. No se afirma SBOM completa ni atestación SLSA.

## GitHub Actions y repositorio público

Los tres workflows usan `contents: read`, actions por SHA completo, checkout sin credenciales persistentes y runners hospedados con timeout. No usan `pull_request_target`, secretos, permisos de escritura ni GPU pagada. El scanner se compila desde revisión fija; el grafo Go/compilador e imágenes `ubuntu-latest` siguen siendo dependencias no fijadas por digest. No se cambiaron visibilidad, reglas de ramas o configuración del repositorio. No se auditó configuración administrativa inaccesible mediante estos endpoints.

Se escaneó el historial con Gitleaks 8.24.3 y los cambios preparados con redacción habilitada. El análisis de archivos versionados no encontró pesos, checkpoints, datasets privados, credenciales o logs sensibles; samples/benchmark/predicciones de referencia son fixtures sintéticos declarados. El historial contiene metadata habitual de autor de Git, incluida dirección de correo; por ello no se afirma ausencia literal de toda información personal. No se reproduce aquí esa dirección ni se reescribe el historial.

Los reportes crudos y pesos diminutos permanecen excluidos de Git. La evidencia versionada en `audits/phase01b/validation.json` contiene solo resultados y hashes sin prompts privados.

## Pruebas adversariales controladas

Se probaron paths `../` y symlinks; cambios de hashes e inventarios; adaptador con pickle sin deserializarlo; CSV incompleto/multilínea; tipos y marcadores inválidos; contenido secreto sintético construido en prueba, PII de ejemplo y frases de inyección; metadatos sensibles; preguntas de benchmark con respuestas/grupos modificados; agotamiento de presupuesto; respuestas JSON inválidas; parámetros nativos negativos/NaN; oversized response; descargas con hash/rango incorrecto, reintentos agotados y DNS privado. Los fallos no se contabilizan como datos aprobados ni resultados correctos. No se usaron secretos reales.

La protección contra poisoning semántico y la revisión de licencias/personas siguen siendo controles humanos de entrada a la Fase 02.
