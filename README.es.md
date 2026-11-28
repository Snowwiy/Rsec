# Rsec AI · v0.3.0-alpha.2

La Fase 03-B selecciona **Inkling 2 Mini de Thinking Machines Lab** como candidato para Rsec-Core. Granite 3B queda como respaldo técnico. El backend de Inkling se prepara en un entorno WSL2 aislado que conserva la instalación validada en Fase 03-A. El corpus tiene cero aprobaciones humanas y la especialización sigue bloqueada. [Selección](MODEL_BASE_SELECTION.md) · [Compatibilidad y evidencia física](INKLING_COMPATIBILITY.md)

La RTX 4070 y la RTX 3060 aprobaron las fixtures supervisadas CUDA y NF4/LoRA en WSL2. NCCL usó memoria compartida del host. DDP y FSDP verificaron recuperación de checkpoints con cargas sintéticas. [Evidencia física](MULTI_GPU_BENCHMARK.md) · [Preparación para entrenamiento](TRAINING_READINESS.md)

La auditoría histórica de Fase 01-B reportó **PASS WITH CONDITIONS**, con **97 pruebas y 91,34 % de cobertura**. El stack genérico de entonces presentó conflictos con Unsloth. La evidencia del backend aislado de Inkling y los requisitos del corpus se mantienen en los informes de la Fase 03-B. [Auditoría](INDEPENDENT_AUDIT.md) · [Plan GPU](GPU_VALIDATION_PLAN.md) · [Preparación de datos](DATASET_READINESS.md)

Plataforma independiente de investigación y entrenamiento de modelos especializados en **ciberseguridad defensiva, programación e ingeniería de software**, propiedad de Snowwiy.

[English / referencia técnica completa](README.md) · [Resultados reales](TEST_RESULTS.md) · [Continuidad](HANDOFF.md)

Esta versión entrega infraestructura para especializar pesos abiertos mediante adaptadores. No distribuye un modelo Rsec entrenado ni demuestra superioridad frente al modelo base.

## Fase 02-B · estado actual

La programación es una capacidad central de Rsec. Esta versión incorpora taxonomía de software, catálogo de fuentes con derechos definidos, mezclas reproducibles de datos aprobados y Rsec-CodeBench. Las dos suites se compararán contra el modelo base. Los datos revisados y CUDA siguen en el camino crítico. Consulta [programación e ingeniería de software](docs/SOFTWARE_ENGINEERING.md) y [validación de benchmarks](BENCHMARK_VALIDATION_REPORT.md).

Hay 96 preauditorías por registro, una interfaz local con decisiones Ed25519 y scripts de comprobación física de GPU. **Corpus FAIL, GPU pendiente, entrenamiento NOT READY.** Guías de [revisión humana](DATASET_REVIEW_GUIDE.md), [instalación local](LOCAL_GPU_SETUP.md) e [integración](GITHUB_INTEGRATION_REPORT.md).

## Fase 02-A · evidencia histórica de datos

**DATASET READINESS: FAIL** para liberar un corpus SFT aprobado. **TRAINING READINESS: NOT READY.** La infraestructura de Fase 02-A se integró en la rama de fundamentos mediante el [PR #2](https://github.com/Snowwiy/Rsec/pull/2). No se inició entrenamiento especializado. Validación actual: **200 pruebas / 94.02 % de cobertura**; entorno core sin Torch: **189 aprobadas**.

Se verificó la existencia de **20 fuentes externas**, además de 2 fuentes internas. El registro distingue acceso público, descarga, entrenamiento y redistribución. Solo se adquirieron tres documentos CVE fijados para índices de referencia; ninguna fuente externa está aprobada para SFT. Hay **64 borradores SFT sintéticos**, **32 casos públicos de desarrollo/regresión**, **cero ejemplos o gold aprobados por expertos** y cero rechazos/cuarentenas reales. Quedan pendientes 96 conversaciones y tres interpretaciones de referencias. La meta condicionada de 500–1,000 ejemplos no se alcanzó; no se añadió volumen artificial.

```bash
rsec data sources
rsec data download --registered
rsec data curate --input data/pilot/candidates.jsonl --output data/processed/piloto-revision --version pilot-0.2.0
rsec data validate data/processed/piloto-revision
rsec data quality data/processed/piloto-revision
rsec data review data/processed/piloto-revision --output reports/revision-piloto.json
rsec benchmark validate
rsec benchmark contamination-check --input data/pilot/candidates.jsonl
```

El paquete de revisión no aprueba registros. `data split` bloquea el piloto sin expertos y no existe release train/eval/test. `data stats DIRECTORIO --tokenizer /tokenizer/local/revisado` mide tokens con la plantilla real; sin tokenizer solo informa unidades de espacios. Medición Qwen local: 16,114 tokens conversacionales, máximo414 y tokens elegibles/época0; no demuestra viabilidad en12 GB.

[Arquitectura de datos](docs/DATASET_ARCHITECTURE.md) · [Fuentes](docs/DATASET_SOURCES.md) · [Licencias](docs/LICENSE_MATRIX.md) · [Taxonomía](docs/DATASET_TAXONOMY.md) · [Revisión humana](docs/DATASET_REVIEW_GUIDE.md) · [Informe](DATASET_ENGINEERING_REPORT.md) · [Ficha](DATASET_CARD.md) · [Benchmark](BENCHMARK_REPORT.md) · [Gates de entrenamiento](TRAINING_READINESS.md).

## Estado

| Componente | Estado | Límite |
|---|---|---|
| CLI, configuraciones y preparación reproducible de datos | TESTED | Pruebas CPU y fixtures; sin aprobación experta del corpus |
| SFT/LoRA diminuto, checkpoints, reanudación, fusión e inferencia | TESTED | Ejecución real en CPU; no prueba la calidad en ciberseguridad |
| QLoRA con RTX 4070/T4 y demás perfiles | GPU VALIDATION PENDING | Sin GPU en el entorno de desarrollo |
| DDP/FSDP con GPU heterogéneas | GPU VALIDATION PENDING | Modo experimental explícito |
| Backend Unsloth | BLOCKED | Conflictos comprobados con Transformers, TRL y datasets |
| Evaluación determinista y registro local | TESTED | Las referencias de prueba no son salidas de un modelo |
| GGUF Q4_K_M y generación nativa llama.cpp | TESTED | Modelo diminuto aleatorio en CPU; Ollama y bindings pendientes |
| RAG completo, API local y SENTRA | NOT IMPLEMENTED | Contratos y arquitectura futura únicamente |

## Inicio rápido sin CUDA

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt -e .
rsec doctor
rsec data prepare --input data/samples/defensive.jsonl --output data/processed/demo
rsec data validate data/processed/demo
pytest -m 'not ml'
```

Los archivos se crean con rechazo de sobrescritura por defecto. El camino legacy de fixtures genera train/eval/test, manifiesto SHA-256, informe de calidad y rechazos sin contenido sensible. La separación usa familias y similitud; los benchmarks se reservan. Las heurísticas de secretos, información personal, anonimización y envenenamiento requieren revisión humana.

La adquisición externa exige licencia revisada y hashes. La lista legacy sigue vacía; `--registered` solo habilita las tres referencias CVE fijadas. El catálogo tiene22 fuentes con permisos separados, sin aprobación SFT externa. Los documentos Markdown/texto se procesan como conocimiento o futuro RAG mediante `rsec data ingest --help`; no se convierten automáticamente en conversaciones supervisadas. Los datos históricos se pueden combinar con `--replay` antes de validar y volver a separar.

## Verificación real del entrenamiento en CPU

```bash
python -m pip install torch==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-cpu-test.lock
HF_HUB_OFFLINE=1 pytest -m ml
rsec train --smoke
```

El modo smoke crea un modelo diminuto aleatorio y un tokenizer de prueba local, ejecuta optimización real y conserva checkpoints. Sus pérdidas no representan capacidad de ciberseguridad. Las versiones transitivas del entorno Linux/Python 3.12 comprobado están fijadas en el lock CPU.

## Entrenamiento con GPU: procedimiento futuro sujeto a gates

Para instalar el entorno y preparar la estación en CPU, consulta la [guía de Windows y WSL2](LOCAL_INSTALLATION_REPORT.md). Sigue por separado el [plan de validación física supervisada](GPU_VALIDATION_PLAN.md).

Estos comandos corresponden a una fase posterior tras cumplir TRAINING_READINESS.md. El modelo preliminar es `Qwen/Qwen2.5-Coder-7B-Instruct`, con revisión SHA fijada y licencia Apache-2.0. La licencia MIT existente del código se conserva. Instala primero una rueda CUDA de PyTorch 2.8.0 compatible con tu controlador; después instala `requirements-train.txt`.

```bash
rsec train --profile local_rtx4070 --allow-network
rsec train --resume experiments/RUN/checkpoints/checkpoint-100
rsec train --adapter experiments/ANTERIOR/adapter --output experiments/incremental
```

`--allow-network` permite adquirir la revisión pública inicial. Con los archivos en caché se puede omitir para ejecutar offline. Reanudar restaura el optimizador; cargar un adaptador inicia otro experimento. Solo se deben reanudar checkpoints propios confiables. Ctrl+C solicita guardar al terminar el siguiente paso. Un error de memoria conserva los checkpoints anteriores.

La RTX 4070 de 12 GB y la futura RTX 3060 de 12 GB tienen memorias separadas. DDP replica el modelo por tarjeta; FSDP fragmenta estados y requiere validación del stack. No se promete entrenar modelos grandes sumando ambas VRAM. Consulta [MULTI_GPU.md](docs/MULTI_GPU.md) y [TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md) para Accelerate, WSL2, Linux, Colab, Kaggle y RunPod. No se contratan servicios de pago automáticamente.

## Evaluar, exportar y ejecutar localmente

```bash
rsec predict --model /modelo/local --output reports/predicciones.jsonl
rsec evaluate --benchmark benchmarks/suite.jsonl --predictions reports/predicciones.jsonl \
  --model-id modelo-local --output reports/evaluacion.json
rsec export --source /adaptador/local --output exports/adaptador-v1 --format adapter
rsec export --source /adaptador/local --base /base/local --output exports/fusion-v1 --format merged
rsec export --source exports/fusion-v1 --output exports/gguf-v1 --format gguf \
  --llama-cpp /llama.cpp/revisado --quantization Q4_K_M
ollama create rsec -f exports/gguf-v1/Modelfile
ollama run rsec
rsec infer --backend ollama --model rsec --prompt 'Distingue evidencia e hipótesis en esta alerta.'
```

Las evaluaciones comparan modelo base, adaptadores y exportaciones con la misma suite independiente. Incluyen precisión, recall, F1, falsos positivos/negativos, coincidencia CWE y conformidad del esquema. La tasa de referencias no respaldadas es una medida limitada; no equivale a medir todas las alucinaciones. No se ejecuta código generado en el host.

La exportación comprueba memoria, espacio e integridad, conserva tokenizer y plantilla, y rechaza destinos existentes. La fusión de modelos grandes puede requerir otra máquina con más RAM. Ollama y llama.cpp necesitan instalación y pruebas propias. No hay dependencias obligatorias de APIs comerciales.

El registro local conserva versiones inmutables, hashes y metadatos. `rsec models activate ID` verifica integridad y estado TESTED, y permite volver a una versión anterior. La autorización de una publicación exige evaluación independiente y pruebas de regresión. El seguimiento local genera JSON, CSV, Markdown y una curva SVG a partir de pérdidas observadas; TensorBoard es opcional.

## Seguridad y continuidad

Solo defensa, análisis autorizado, detección y remediación. Los filtros no sustituyen la revisión humana. Safetensors y `trust_remote_code=False` son las opciones obligatorias por defecto. Los datos, credenciales, logs privados, checkpoints y modelos pesados no se publican en Git.

Consulta [arquitectura](docs/ARCHITECTURE.md), [política de datos](docs/DATASET_POLICY.md), [seguridad](docs/SECURITY.md), [roadmap](ROADMAP.md), [modelo](MODEL_CARD.md), [informe de implementación](IMPLEMENTATION_REPORT.md) y [entrega al siguiente agente](HANDOFF.md).
