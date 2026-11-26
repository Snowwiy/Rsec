# Rsec AI · v0.1.0-alpha

Plataforma independiente de investigación y entrenamiento de modelos especializados en **ciberseguridad defensiva**, propiedad de Snowwiy.

[English / referencia técnica completa](README.md) · [Resultados reales](TEST_RESULTS.md) · [Continuidad](HANDOFF.md)

Esta versión entrega infraestructura para especializar pesos abiertos mediante adaptadores. No distribuye un modelo Rsec entrenado ni demuestra superioridad frente al modelo base.

## Estado

| Componente | Estado | Límite |
|---|---|---|
| CLI, configuraciones y preparación reproducible de datos | TESTED | Pruebas CPU y ejemplos sintéticos revisados |
| SFT/LoRA diminuto, checkpoints, reanudación, fusión e inferencia | TESTED | Ejecución real en CPU; no prueba la calidad en ciberseguridad |
| QLoRA con RTX 4070/T4 y demás perfiles | GPU VALIDATION PENDING | Sin GPU en el entorno de desarrollo |
| DDP/FSDP con GPU heterogéneas | GPU VALIDATION PENDING | Modo experimental explícito |
| Backend Unsloth | IMPLEMENTED | Dependencias opcionales aisladas, sin validación física |
| Evaluación determinista y registro local | TESTED | Las referencias de prueba no son salidas de un modelo |
| GGUF y motores externos | IMPLEMENTED | Consulta TEST_RESULTS.md para validación efectivamente realizada |
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

Los archivos se crean con rechazo de sobrescritura por defecto. Cada publicación de datos genera train/eval/test, manifiesto SHA-256, informe de calidad y rechazos sin contenido sensible. La separación usa familias y similitud; los benchmarks se reservan. Las heurísticas de secretos, información personal, anonimización y envenenamiento requieren revisión humana.

La adquisición externa exige licencia revisada y hashes. La lista de fuentes está vacía intencionalmente. Los documentos Markdown/texto se procesan como conocimiento o futuro RAG mediante `rsec data ingest --help`; no se convierten automáticamente en conversaciones supervisadas. Los datos históricos se pueden combinar con `--replay` antes de validar y volver a separar.

## Verificación real del entrenamiento en CPU

```bash
python -m pip install torch==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-cpu-test.lock
HF_HUB_OFFLINE=1 pytest -m ml
rsec train --smoke
```

El modo smoke crea un modelo diminuto aleatorio y un tokenizer de prueba local, ejecuta optimización real y conserva checkpoints. Sus pérdidas no representan capacidad de ciberseguridad. Las versiones transitivas del entorno Linux/Python 3.12 comprobado están fijadas en el lock CPU.

## Entrenamiento con GPU

El modelo preliminar es `Qwen/Qwen2.5-Coder-7B-Instruct`, con revisión SHA fijada y licencia Apache-2.0. La licencia MIT existente del código se conserva. Instala primero una rueda CUDA de PyTorch 2.8.0 compatible con tu controlador; después instala `requirements-train.txt`.

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
