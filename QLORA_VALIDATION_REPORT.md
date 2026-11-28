# Inkling 2 Mini · Fase 03-B

El backend específico prepara una copia aislada del entorno CUDA en WSL2. Carga la revisión NF4 local mediante Unsloth, conserva la precisión de los message gates y exige parámetros CUDA en ambas tarjetas. La prueba utiliza únicamente dos conversaciones de aritmética sintética, contexto máximo 512, batch por paso 1, LoRA rank 8 y acumulación configurable. La ruta técnica comprueba pasos con pérdida finita, cambios de pesos LoRA y restauración exacta desde Safetensors. [Arquitectura y versiones](INKLING_COMPATIBILITY.md)

```bash
bash scripts/setup_inkling_wsl.sh
export CUDA_DEVICE_ORDER=PCI_BUS_ID
PYTHON="$RSEC_INKLING_ENV/bin/python"
"$PYTHON" -m rsec.cli inkling "$INKLING_NF4_DIR"
"$PYTHON" -m rsec.cli inkling "$INKLING_NF4_DIR" \
  --uuid "$RTX4070_UUID" --uuid "$RTX3060_UUID" \
  --steps 2 --accumulation 1 --smoke-output "$PRIVATE_RUN_DIR"
```

Define `RSEC_CUDA_ENV` con el entorno CUDA verificado y `RSEC_INKLING_ENV` con un directorio independiente. La segunda invocación necesita dos UUID, un destino nuevo y supervisa ambas tarjetas. Triton requiere un compilador C y las cabeceras de C y Python. Si Ubuntu 24.04 carece de ellos, `bash scripts/setup_inkling_compiler_wsl.sh` los extrae sin instalación global. Apunta `CC` y `CXX` a los ejecutables `cc` y `c++` bajo `$HOME/.local/share/rsec/inkling-compiler/bin`. Mantén la salida fuera de Git y revisa los procesos activos antes de empezar.

El protocolo utiliza un proceso con reparto de capas, activaciones con gradient checkpointing y el optimizador de 8 bits de la receta del proveedor. DDP replica pesos. La compatibilidad de FSDP, tensor parallelism o pipeline parallelism exige una demostración específica del checkpoint y del runtime. La recuperación del fixture carga tensores de adaptador, por lo cual la reanudación de un optimizador tras reiniciar el proceso tiene su propio gate.

### Primera corrida · autotuning de MoE

**Carga física TESTED. Pasos QLoRA interrumpidos.** Unsloth repartió el modelo completo en ambas GPU, con estimación de 7,26 GiB para la RTX 4070 y 6,86 GiB para la RTX 3060. La carga tomó 233,8 s. La comprobación del modelo cargado confirmó la precisión de los 144 gates. El trainer preparó 202 555 392 parámetros LoRA, incluidos expertos enrutados, y usó un proceso con dos dispositivos. El autotuning repitió fallos de memoria al intentar buffers de 256 MiB a 1,28 GiB. Se detuvo únicamente el grupo del fixture antes de completar el primer paso.

El pico de VRAM total fue 11 958 MiB en la RTX 4070 y 11 974 MiB en la RTX 3060. Las temperaturas máximas fueron 51,3 y 78,9 °C, respectivamente. El siguiente perfil usa `UNSLOTH_MOE_DISABLE_AUTOTUNE=1` para aplicar los parámetros heurísticos de la misma versión del kernel, con alcance limitado al proceso del fixture. [Selector de configuraciones de Unsloth](https://github.com/unslothai/unsloth/blob/7421333ab85d1542211aa20408e094ec690c93c0/unsloth/kernels/moe/autotune_cache.py)

---

# NF4 y LoRA · v0.3.0-alpha.2

Ruta de prueba: `rsec.gpu.validate_single` con una capa BitsAndBytes Linear4bit NF4, doble cuantización y cómputo FP16; PEFT restringe las actualizaciones al adaptador. Verifica pérdida finita, avance efectivo, inferencia idéntica tras restaurar los tensores Safetensors y paso 2 del optimizador tras cargar su estado con weights_only. El fixture utiliza la misma base diminuta en memoria. Un checkpoint completo de un Transformer en otro proceso requiere otra prueba.

**VALIDATED para la fixture técnica en ambas tarjetas.** Se usó la misma semilla 923, capa de 64 × 64, cuatro vectores sintéticos y LoRA de rango 4 con alpha 8. NF4 y la doble cuantización se materializaron en CUDA. Ambas tarjetas ejecutaron forward y backward, actualizaron el adaptador, verificaron la integridad y reprodujeron la salida de inferencia tras restaurar el adaptador. Un paso adicional confirmó la recuperación del optimizador.

FSDP 1 también ejecutó NF4 con almacenamiento y cómputo BF16 y verificó checkpoints y exportación de adaptador en dos procesos. La fixture valida el mecanismo. La carga de un Transformer generativo, TRL sobre un corpus aprobado y Unsloth permanecen fuera de esta evidencia. [Pruebas distribuidas](MULTI_GPU_VALIDATION.md) · [Gate de entrenamiento](TRAINING_READINESS.md)
