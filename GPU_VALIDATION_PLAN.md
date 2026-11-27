# Estado y comandos físicos · Fase 03-A

El host detectó la RTX 4070. El entorno cu128 está instalado en Ubuntu WSL2 y queda por comprobar en hardware. Cuando el operador confirme el fin de la sesión de juego y la instalación de la RTX 3060, actualizar el inventario, revisar VRAM disponible y procesos, y ejecutar `validate_gpu.sh` una vez por UUID, primero en la 4070. Ejecutar `validate_multi_gpu.sh` sólo tras revisar ambos resultados. El supervisor registra aviso a 80 °C y detiene la carga a 85 °C o ante pérdida de telemetría, error del proceso o límite de tiempo.

GPU READINESS **VALIDATION PENDING**. Se implementaron diagnóstico NVIDIA JSON/Markdown, selección por UUID y pruebas CUDA que rechazan fallback CPU. El smoke single usa una capa NF4 con LoRA y el DDP usa una capa densa sincronizada por NCCL. FSDP + QLoRA y GGUF repartido tienen procedimiento experimental. Ninguno se ejecutó en el equipo físico durante esta fase.

Los procedimientos actualizados están en [instalación local](LOCAL_GPU_SETUP.md) y [validación de dos GPU](MULTI_GPU_VALIDATION.md). La RTX 4070 y la RTX 3060 tienen 12 GB independientes. Confirma memoria, driver y topología reales antes de aumentar el tamaño del modelo. El plan de Fase 01-B queda a continuación.

---

# Rsec — plan reproducible de validación física GPU

Estado: **GPU VALIDATION PENDING**. Fecha: 2026-11-26. Este documento es un protocolo; sus comandos GPU no se ejecutaron durante la auditoría. No autoriza entrenamiento real de Rsec ni aprovisionamiento de servicios.

## Equipos y límites

Equipo comunicado: Ryzen 9 5900X, RTX 4070 12 GB, 32 GB DDR4, Windows 11, fuente MSI rotulada 1000 W. Ampliación propuesta: RTX 3060 12 GB. No se verificaron físicamente placa base, slots, reparto de líneas PCIe, refrigeración, conectores, driver, capacidad real de la fuente ni espacio SSD.

Las dos tarjetas mantienen dos asignaciones independientes de 12 GB. DDP replica el modelo y su memoria de trabajo por GPU; debe caber en cada una. FSDP reparte estados, pero all-gather, buffers, activaciones y offload pueden producir picos. 24 GB físicos distribuidos no garantizan cargar como si existiera una GPU de 24 GB. La 3060 puede limitar velocidad; peer access/NVLink no se presuponen. No se garantiza mejora con dos tarjetas.

## Compatibilidad revisada

| Combinación | Comprobación | Estado |
|---|---|---|
| Torch 2.8.0+cpu / Transformers 5.24.1 / PEFT 0.22.0 / TRL 1.19.0 / Accelerate 1.16.0 | Instalación, APIs, entrenamiento/resume/merge reales CPU y pip check | TESTED CPU |
| Torch 2.8.0 CUDA + BitsAndBytes 0.50.2 | Código NF4/double-quant y versiones directas; no kernels físicos | GPU VALIDATION PENDING; sin lock transitivo CUDA |
| Unsloth 2026.11.12 + pins Rsec | Metadata oficial del wheel contradice Transformers<=5.17.0, TRL<=1.15.0, datasets<5.0.0 | BLOCKED; no instalar sobre el stack auditado |
| FSDP1 FP16 QLoRA | Documentación PEFT exige storage FP32 para AMP FP16; mismo dtype al cargar; paged_adamw_8bit tiene fallo de checkpoint documentado | Código corregido a storage/modelo FP32 y AdamW; físico pendiente |
| Linux | Entorno preferido para validar primero NCCL y heterogeneidad | Pendiente |
| Windows 11 / WSL2 | NVIDIA soporta WSL2 con driver Windows; NVML/pinned memory/managed memory tienen límites | Pendiente; sin instalar driver Linux dentro de WSL |
| Ollama / llama-cpp-python multi-GPU | Interfaz implementada; depende del build CUDA real | Pendiente; separado del entrenamiento |

Fuentes oficiales consultadas el 2026-11-26: [PEFT FSDP](https://huggingface.co/docs/peft/accelerate/fsdp), [BitsAndBytes FSDP-QLoRA](https://huggingface.co/docs/bitsandbytes/fsdp_qlora), [TRL SFT](https://huggingface.co/docs/trl/sft_trainer), [CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/), [metadata del proyecto Unsloth](https://github.com/unslothai/unsloth/blob/main/pyproject.toml). La evidencia específica de versión de Unsloth es el wheel, no inferencia a partir de `main`.

## Paso 1 — congelar entorno y hardware

Usar un checkout nuevo del commit de código auditado indicado en HANDOFF.md. Mantener intacto el entorno CPU. Crear venv Linux/WSL2 separado, Python 3.12. Instalar la variante CUDA oficial de Torch 2.8.0 compatible con el driver mediante [selector PyTorch](https://pytorch.org/get-started/locally/); no instalar el lock CPU en ese venv. Después:

```bash
python -m pip install -r requirements-train.txt -e .
python -m pip check
python -m pip freeze > /local/private-validation/gpu-environment.lock
pip-audit --disable-pip -r /local/private-validation/gpu-environment.lock
nvidia-smi
nvidia-smi topo -m
rsec doctor --output /local/private-validation/doctor-all.json
```

Registrar driver, CUDA runtime de torch, versiones, nombre/UUID/capability por GPU, BF16 observado, memoria libre/total, peer matrix, PCIe link generation/width y RAM/SSD disponibles. En Linux revisar topología con herramientas de la placa/sistema; no inventar slots a partir de Ryzen. En WSL algunos comandos NVML pueden no estar disponibles: registrar null/no soportado y comprobar selección mediante torch. La limitación de Docker `--gpus all` descrita por NVIDIA no significa que CUDA_VISIBLE_DEVICES necesariamente deje de funcionar para procesos; verificar la enumeración real.

En Windows ejecutar `wsl --version` y registrar versión de kernel/distribución. Instalar el driver NVIDIA Windows compatible con WSL; no instalar driver de pantalla Linux dentro de WSL. Mantener venvs y paths Linux separados de Windows. Si P2P/NCCL no funcionan, registrar el fallo; cualquier fallback NCCL debe ser explícito y comparado, no un éxito simulado.

## Paso 2 — smoke de kernels y selección

Con cada GPU visible de forma individual, comprobar cuda.is_available, nombre lógico, matmul FP16/BF16 y un forward/backward BitsAndBytes NF4 sobre un modelo pequeño revisado. Registrar `CUDA_VISIBLE_DEVICES` y UUID físicos: el índice lógico 0 cambia al filtrar. `rsec train --smoke` siempre prueba CPU y **no sirve como smoke CUDA**.

No usar el dataset completo de Rsec. El primer trabajo físico será un ensayo de infraestructura autorizado con datos sintéticos y pocas iteraciones. Verificar previamente derechos/cache de un base pequeño y su tokenizer; nunca activar trust_remote_code. Si se pretende usar un base distinto de Qwen2, revisar módulos LoRA y wrapper FSDP.

## Paso 3 — ensayos comparables

Crear fuera de Git un YAML derivado de `rsec config`, con dataset release inmutable, output nuevo, max_steps=20, save_steps=5 y eval_steps=5. Usar contexto 512 antes de 1024/2048, batch=1 y rank=16. Elegir precisión soportada; no extrapolar capacidad del ensayo pequeño a 7B.

| Ensayo | Procesos / precisión | Acumulación para batch efectivo 16 | Medición requerida |
|---|---|---|---|
| 4070 sola | 1 / FP16, después BF16 si observado | 16 | baseline de VRAM, tiempo, pérdida |
| 3060 sola | 1 / misma precisión comparable | 16 | mismo modelo/dataset/steps/seed |
| DDP ambas | 2 / FP16 del launcher y perfil | 8 | réplica cabe en cada GPU; NCCL y rank binding |
| FSDP1 ambas | 2 / FP16, storage FP32, AdamW, offload | 8 | picos all-gather, RAM host, checkpoints y export |

El perfil DDP versionado usa acumulación=16, lo que produciría batch efectivo 32 con dos procesos. Para esta comparación usar el YAML experimental con acumulación=8. No comparar throughput/calidad fingiendo batch igual. No modificar los benchmarks ni muestras entre ensayos.

Ejemplos de lanzamiento, después de configurar explícitamente los YAML externos:

```bash
CUDA_VISIBLE_DEVICES=0 rsec train --config /local/private-validation/single.yaml
CUDA_VISIBLE_DEVICES=0,1 accelerate launch --config_file configs/accelerate/multi_gpu_ddp.yaml \
  -m rsec.train --config /local/private-validation/ddp.yaml --allow-experimental
CUDA_VISIBLE_DEVICES=0,1 accelerate launch --config_file configs/accelerate/multi_gpu_fsdp.yaml \
  -m rsec.train --config /local/private-validation/fsdp.yaml --allow-experimental
```

No ejecutar automáticamente estos ejemplos. Descargar el base fijado solo cuando se autorice y después repetir sin red. En equipos heterogéneos revisar que no haya otros consumidores de VRAM y que cada proceso use su rank local; nunca usar device_map=auto como sustituto de DDP.

## Paso 4 — recuperación y errores

Reanudar desde step 10 con la misma configuración/total de pasos y release, en output nuevo. Verificar step del optimizador, scheduler, RNG, continuidad de pérdida y pesos finales frente al ensayo ininterrumpido bajo iguales condiciones. Cambiar dataset/base/adaptador/config relevante debe rechazarse. Extender max_steps es otro experimento de scheduler.

Comprobar parada suave, proceso interrumpido, checksum alterado y ausencia de archivos de estado. En FSDP inspeccionar primero el layout real: no renombrar ni fabricar optimizer.pt para pasar `verify_checkpoint`. Si no coincide, marcar resume BLOCKED y diseñar una corrección con evidencia física. Validar que todos los ranks participan en save/gather y que no quedan colgados ante fallo de un rank.

Probar OOM de forma acotada y supervisada en el ensayo sintético; no estresar todo el sistema ni prometer recuperación automática. Registrar error, preservación de checkpoints previos y salida no exitosa. No aumentar contexto indefinidamente para forzar fallo. Con 32 GB host RAM, offload/merge pueden ser el límite antes que VRAM.

## Paso 5 — exportación y criterios de aprobación

Exportar adaptador, recargarlo en proceso nuevo, fusionar en base local no cuantizado, comparar logits/predicciones y tokenizer/template. Convertir GGUF Q4_K_M en máquina con RAM/disco medidos y comprobar inferencia llama.cpp. Validar Ollama/bindings por separado y medir tensor_split real; Transformers selecciona una GPU mediante CUDA_VISIBLE_DEVICES, no reparte inferencia aquí.

Registrar por GPU: pico VRAM, RAM host, tiempo al primer paso, tokens/s estable, latencia, utilización/potencia/temperatura cuando observables y pérdida held-out. Registrar también fallos, parámetros de software/build y hashes de salidas. No inventar cifras ni sumar VRAM como capacidad utilizable.

Un perfil pasa solo con carga/kernels reales, pérdida finita, datos aislados, checkpoints íntegros, resume coherente y exportación funcional. Si DDP/FSDP no aporta mejora o no cabe, mantener single-GPU como ruta preferida comprobada. Después de estos ensayos se podrá proponer entrenamiento real; esta auditoría no lo inicia.
