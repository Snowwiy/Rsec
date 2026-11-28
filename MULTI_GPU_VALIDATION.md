# Fase 03-A · validación dual-GPU

## Evidencia de la estación · v0.3.0-alpha.2

**NCCL VALIDATED.** Dos procesos y dos dispositivos con identidad por UUID comprobada. All-reduce, broadcast, envío/recepción y barrera pasaron. La selección automática de NCCL 2.27.3 usó SHM para datos y socket para el inicio. CUDA reportó P2P no disponible en ambos sentidos. La ejecución conservó la configuración por defecto de P2P.

**DDP VALIDATED.** Datos sintéticos distintos por rank, mismo batch global que el ensayo individual, actualización sincronizada, checkpoint verificado por SHA-256, restauración en un modelo nuevo y parámetros idénticos tras continuar. Cada rank conserva una réplica.

**FSDP PASS WITH CONDITIONS.** La fixture NF4 de FSDP 1/PEFT se fragmentó en dos partes, ejecutó forward y backward, actualizó LoRA, restauró modelo y optimizador y exportó Safetensors. BF16 se usó para almacenamiento y cómputo. También se recuperó un checkpoint distribuido con dos archivos verificados. Falta validar la ruta de un Transformer completo con su política de wrapping y el trainer del proyecto. [Guía de BitsAndBytes](https://huggingface.co/docs/bitsandbytes/fsdp_qlora) · [Guía de PEFT](https://huggingface.co/docs/peft/accelerate/fsdp)

Ejecutar los modos `nccl`, `ddp`, `fsdp` o `independent` con el mismo entorno mediante `bash scripts/validate_multi_gpu.sh "$GPU_4070" "$GPU_3060" <directorio-nuevo> <modo>`. El supervisor exige dos UUID distintos, un máximo de 180 segundos y detiene la carga si pierde telemetría. [Comparación medida](MULTI_GPU_BENCHMARK.md)

---

# Procedimiento histórico de validación

La configuración objetivo contiene dos GPU con 12 GB cada una. Registra UUID, slots, ancho y generación PCIe efectivos, RAM, unidad, driver, versión CUDA de la rueda, NCCL, matriz P2P, potencia y temperatura. Las dos memorias físicas son asignaciones separadas. La instalación y el enlace real siguen pendientes de verificación local.

## A. Procesos independientes

Valida cada GPU por UUID con LOCAL_GPU_SETUP.md. Ejecuta una carga por proceso y mide cada tarjeta sola y simultáneamente. Una GPU puede servir inferencia o embeddings mientras la otra entrena una vez cumplidos los gates. Comprueba contención de RAM, disco, PCIe y fuente.

## B. DDP

Desde Linux/WSL2, establece ambas variables de UUID como en LOCAL_GPU_SETUP.md. El smoke usa NCCL, dos ranks, un modelo lineal por GPU, sincronización de gradientes y comprobación de pesos.

```bash
CUDA_VISIBLE_DEVICES="$GPU_4070,$GPU_3060" torchrun --standalone --nproc-per-node=2 \
  --module rsec.cli gpu validate --mode ddp --output reports/ddp-smoke.json
```

DDP replica el modelo. Cada GPU debe tener espacio suficiente. Sólo después prueba el perfil `local_rtx4070_rtx3060` con un modelo diminuto previamente revisado. Compara throughput y tiempos por rank. El rank más lento y la comunicación pueden limitar el progreso.

## C. FSDP1 + QLoRA

Valida primero NF4 por tarjeta y NCCL. Prepara `/local/reviewed-fsdp-smoke.yaml` con un Qwen2 local pequeño compatible, revisión fijada, contexto reducido, dataset sintético autorizado con release validado y salida nueva. Usa el perfil existente `local_fsdp`. El runtime conserva la estrategia FSDP explícita. Prueba guardado, reanudación y exportación desde otra invocación antes de escalar. Sigue las condiciones documentadas por [PEFT](https://huggingface.co/docs/peft/accelerate/fsdp).

```bash
rsec config --config /local/reviewed-fsdp-smoke.yaml --profile local_fsdp
CUDA_VISIBLE_DEVICES="$GPU_4070,$GPU_3060" accelerate launch \
  --config_file configs/accelerate/multi_gpu_fsdp.yaml -m rsec.train \
  --config /local/reviewed-fsdp-smoke.yaml --profile local_fsdp --max-steps 2 \
  --output experiments/fsdp-nf4-smoke --allow-experimental
```

El comando es un procedimiento de ejecución posterior. Se deben comprobar almacenamiento cuantizado, dtype, host RAM/offload y compatibilidad de checkpoints. No uses `device_map=auto` como sustituto de FSDP. CUDA y QLoRA de FSDP siguen pendientes.

## D. Inferencia distribuida

Con llama.cpp limpio y GGUF de confianza, ejecuta el mismo prompt y contexto con GPU individual y luego ambas, manteniendo configuración y semilla. Selecciona GPUs por UUID y ajusta capas y tensor split a memoria medida. Ejemplo futuro con la interfaz existente:

```bash
CUDA_VISIBLE_DEVICES="$GPU_4070,$GPU_3060" rsec infer --backend llama-cpp \
  --model /local/modelo-Q4_K_M.gguf --gpu-layers 10 --tensor-split 1 1 \
  --prompt "Explica la diferencia entre evidencia e hipótesis."
```

Registra tokens/s, inicialización, tiempo por paso, VRAM pico por dispositivo, RAM, utilización, temperatura, potencia disponible, errores OOM, comunicación, estabilidad, guardado y recuperación. Los resultados tienen que provenir de la sesión local y separar pruebas densas, NF4/LoRA y modelos completos. El matmul de diagnóstico no estima tokens/s.
