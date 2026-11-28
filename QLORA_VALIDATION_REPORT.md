# NF4 y LoRA · v0.3.0-alpha.2

Ruta de prueba: `rsec.gpu.validate_single` con una capa BitsAndBytes Linear4bit NF4, doble cuantización y cómputo FP16; PEFT restringe las actualizaciones al adaptador. Verifica pérdida finita, avance efectivo, inferencia idéntica tras restaurar los tensores Safetensors y paso 2 del optimizador tras cargar su estado con weights_only. El fixture utiliza la misma base diminuta en memoria. Un checkpoint completo de un Transformer en otro proceso requiere otra prueba.

**VALIDATED para la fixture técnica en ambas tarjetas.** Se usó la misma semilla 923, capa de 64 × 64, cuatro vectores sintéticos y LoRA de rango 4 con alpha 8. NF4 y la doble cuantización se materializaron en CUDA. Ambas tarjetas ejecutaron forward y backward, actualizaron el adaptador, verificaron la integridad y reprodujeron la salida de inferencia tras restaurar el adaptador. Un paso adicional confirmó la recuperación del optimizador.

FSDP 1 también ejecutó NF4 con almacenamiento y cómputo BF16 y verificó checkpoints y exportación de adaptador en dos procesos. La fixture valida el mecanismo. La carga de un Transformer generativo, TRL sobre un corpus aprobado y Unsloth permanecen fuera de esta evidencia. [Pruebas distribuidas](MULTI_GPU_VALIDATION.md) · [Gate de entrenamiento](TRAINING_READINESS.md)
