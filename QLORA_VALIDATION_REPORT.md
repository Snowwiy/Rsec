# Inkling 2 Mini · Fase 03-B

El backend específico prepara una copia aislada del entorno CUDA en WSL2. Carga la revisión NF4 local mediante Unsloth, conserva la precisión de los message gates y exige parámetros CUDA en ambas tarjetas. La prueba utiliza únicamente dos conversaciones de aritmética sintética, contexto máximo 512, batch por paso 1, LoRA rank 8 y acumulación configurable. La ruta técnica comprueba pasos con pérdida finita, cambios de pesos LoRA y restauración exacta desde Safetensors. [Arquitectura y versiones](INKLING_COMPATIBILITY.md)

```bash
bash scripts/setup_inkling_wsl.sh
export CUDA_DEVICE_ORDER=PCI_BUS_ID
PYTHON="$RSEC_INKLING_ENV/bin/python"
"$PYTHON" -m rsec.cli inkling "$INKLING_NF4_DIR"
UNSLOTH_MOE_DISABLE_AUTOTUNE=1 UNSLOTH_INKLING2_FLEX=0 \
  "$PYTHON" -m rsec.cli inkling "$INKLING_NF4_DIR" \
  --uuid "$RTX4070_UUID" --uuid "$RTX3060_UUID" \
  --steps 2 --accumulation 1 --smoke-output "$PRIVATE_RUN_DIR"
```

Define `RSEC_CUDA_ENV` con el entorno CUDA verificado y `RSEC_INKLING_ENV` con un directorio independiente. La segunda invocación necesita dos UUID, un destino nuevo y supervisa ambas tarjetas. Triton requiere un compilador C y las cabeceras de C y Python. Si Ubuntu 24.04 carece de ellos, `bash scripts/setup_inkling_compiler_wsl.sh` los extrae sin instalación global. Apunta `CC` y `CXX` a los ejecutables `cc` y `c++` bajo `$HOME/.local/share/rsec/inkling-compiler/bin`. Mantén la salida fuera de Git y revisa los procesos activos antes de empezar.

El protocolo utiliza un proceso con reparto de capas, activaciones con gradient checkpointing y el optimizador de 8 bits de la receta del proveedor. DDP replica pesos. La compatibilidad de FSDP, tensor parallelism o pipeline parallelism exige una demostración específica del checkpoint y del runtime. La recuperación del fixture carga tensores de adaptador, por lo cual la reanudación de un optimizador tras reiniciar el proceso tiene su propio gate.

### Primera corrida · autotuning de MoE

**Carga física TESTED. Pasos QLoRA interrumpidos.** Unsloth repartió el modelo completo en ambas GPU, con estimación de 7,26 GiB para la RTX 4070 y 6,86 GiB para la RTX 3060. La carga tomó 233,8 s. La comprobación del modelo cargado confirmó la precisión de los 144 gates. El trainer preparó 202 555 392 parámetros LoRA, incluidos expertos enrutados, y usó un proceso con dos dispositivos. El autotuning repitió fallos de memoria al intentar buffers de 256 MiB a 1,28 GiB. Se detuvo únicamente el grupo del fixture antes de completar el primer paso.

El pico de VRAM total fue 11 958 MiB en la RTX 4070 y 11 974 MiB en la RTX 3060. Las temperaturas máximas fueron 51,3 y 78,9 °C, respectivamente. El siguiente perfil usa `UNSLOTH_MOE_DISABLE_AUTOTUNE=1` para aplicar los parámetros heurísticos de la misma versión del kernel, con alcance limitado al proceso del fixture. [Selector de configuraciones de Unsloth](https://github.com/unslothai/unsloth/blob/7421333ab85d1542211aa20408e094ec690c93c0/unsloth/kernels/moe/autotune_cache.py)

### Segunda corrida · heurísticas MoE y FlexAttention

La compilación del backward falló en TorchInductor y Triton 3.4 con `PassManager::run failed`. La traza pasó por la función de recuperación de activaciones de Unsloth y la compilación de Triton. Se habían completado la carga, la preparación LoRA y el forward inicial. No hubo un paso de optimizador validado. El pico total fue 11 505 / 10 205 MiB de VRAM y 46,4 / 72,3 °C en RTX 4070 / RTX 3060. Se probó después la opción del proveedor `UNSLOTH_INKLING2_FLEX=0`, que conserva la atención eager nativa. [Selección de FlexAttention](https://github.com/unslothai/unsloth/blob/7421333ab85d1542211aa20408e094ec690c93c0/unsloth/models/inkling2_flex.py)

### Tercera corrida · heurísticas MoE y atención eager

**PASS WITH CONDITIONS.** Se completaron el forward, backward y dos pasos de optimizador con la RTX 4070 y la RTX 3060. La pérdida media fue finita (7,0168) y se observaron cambios en las muestras de 336 tensores LoRA. La prueba usó dos ejemplos sintéticos, contexto máximo 512, batch 1, acumulación 1, rank 8 y LoRA en las capas de atención y los expertos enrutados. El gradient checkpointing de Unsloth quedó configurado.

| Medición | Resultado |
|---|---:|
| Carga de pesos | 246,02 s |
| Fixture con dos pasos y sincronización | 19,08 s |
| Guardado y hash del adaptador | 62,36 s |
| Recuperación y comprobación | 7,72 s |
| Adaptador Safetensors | 810 274 296 bytes |
| Pico de memoria asignada por PyTorch en RTX 4070 / RTX 3060 | 10,537 / 10,001 GiB |
| Pico de VRAM total en RTX 4070 / RTX 3060 | 11 887 / 10 837 MiB |
| Temperatura máxima en RTX 4070 / RTX 3060 | 44,4 / 70,8 °C |
| Potencia media y máxima en RTX 4070 | 46,85 / 90,25 W |
| Potencia media y máxima en RTX 3060 | 44,77 / 89,36 W |

Las muestras de telemetría quedaron por debajo de 80 °C. Los parámetros medidos estaban repartidos entre CUDA0 y CUDA1. El adaptador se guardó en Safetensors, se pusieron a cero sus parámetros en la base en memoria y se recuperaron con coincidencia exacta de tensores. La huella del archivo coincidió en la recuperación y en una segunda lectura independiente. La reanudación del optimizador en un proceso nuevo y la exportación fusionada siguen pendientes.

La combinación que pasó fue `UNSLOTH_MOE_DISABLE_AUTOTUNE=1` y `UNSLOTH_INKLING2_FLEX=0`, con la convolución causal de referencia de PyTorch. Los límites declarados de Transformers de los dos paquetes Unsloth siguen apareciendo en `pip check`. El resultado aplica al fixture y a este entorno aislado. FSDP, tensor parallelism y pipeline parallelism siguen pendientes para el checkpoint completo.

---

# NF4 y LoRA · v0.3.0-alpha.2

Ruta de prueba: `rsec.gpu.validate_single` con una capa BitsAndBytes Linear4bit NF4, doble cuantización y cómputo FP16; PEFT restringe las actualizaciones al adaptador. Verifica pérdida finita, avance efectivo, inferencia idéntica tras restaurar los tensores Safetensors y paso 2 del optimizador tras cargar su estado con weights_only. El fixture utiliza la misma base diminuta en memoria. Un checkpoint completo de un Transformer en otro proceso requiere otra prueba.

**VALIDATED para la fixture técnica en ambas tarjetas.** Se usó la misma semilla 923, capa de 64 × 64, cuatro vectores sintéticos y LoRA de rango 4 con alpha 8. NF4 y la doble cuantización se materializaron en CUDA. Ambas tarjetas ejecutaron forward y backward, actualizaron el adaptador, verificaron la integridad y reprodujeron la salida de inferencia tras restaurar el adaptador. Un paso adicional confirmó la recuperación del optimizador.

FSDP 1 también ejecutó NF4 con almacenamiento y cómputo BF16 y verificó checkpoints y exportación de adaptador en dos procesos. La fixture valida el mecanismo. La carga de un Transformer generativo, TRL sobre un corpus aprobado y Unsloth permanecen fuera de esta evidencia. [Pruebas distribuidas](MULTI_GPU_VALIDATION.md) · [Gate de entrenamiento](TRAINING_READINESS.md)
