# NF4 y LoRA · sin ejecución física

Ruta de prueba: `rsec.gpu.validate_single` con una capa BitsAndBytes Linear4bit NF4, doble cuantización y cómputo FP16; PEFT restringe las actualizaciones al adaptador. Verifica pérdida finita, avance efectivo, inferencia idéntica tras restaurar los tensores Safetensors y paso 2 del optimizador tras cargar su estado con weights_only. El fixture utiliza la misma base diminuta en memoria. Un checkpoint completo de un Transformer en otro proceso requiere otra prueba.

Aceptar el smoke únicamente tras revisar el resultado físico con el stack CUDA fijado y el informe térmico de esa ejecución. La suite CPU sí conserva regresiones del trainer y del ciclo de artefactos. Unsloth continúa experimental fuera del entorno principal. No se inició especialización.
