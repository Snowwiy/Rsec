# Compatibilidad de Inkling 2 Mini · Fase 03-B

## Arquitectura

Inkling 2 Mini combina un codificador de imágenes y un decodificador autoregresivo de texto. Tiene 26,4 B parámetros totales, 3,4 B activos en una pasada base y aproximadamente 5,4 B activos efectivos con repetición. Las 24 capas del decodificador incluyen un tramo medio compartido de 12 capas que se ejecuta tres veces y resulta en 48 aplicaciones de capas por token. Cada capa MoE activa hasta ocho de 128 expertos según el enrutador. El decodificador combina atención local y global. El contexto de hasta un millón de tokens es una especificación del editor y requiere medición local independiente. [Tarjeta oficial](https://thinkingmachines.ai/model-card/inkling-2-mini/)

La cifra de 26,4 B procede de Thinking Machines Lab y de la guía de ajuste de Unsloth. La ficha de la conversión GGUF en Hugging Face todavía muestra 26,2 B en el texto. Las validaciones locales identifican los archivos por sus revisiones y tamaños exactos. [Guía de ajuste](https://unsloth.ai/docs/models/inkling-2-mini/fine-tuning) · [Ficha GGUF](https://huggingface.co/unsloth/Inkling-2-Mini-GGUF)

Transformers registra `inkling2_loop` como `Inkling2LoopForConditionalGeneration` con procesador de texto e imagen. El paquete fija el tokenizer, el procesador, la plantilla Jinja y los tokens de turno `<|message_user|>` y `<|message_model|>`. Conserva su formato al preparar mensajes y al enmascarar el ejemplo de respuesta. Tool calling y JSON Schema dependen del servidor, de la plantilla y del cliente. La simple respuesta de texto no prueba el uso de herramientas. [Transformers · Inkling2Loop](https://huggingface.co/docs/transformers/model_doc/inkling2_loop) · [Checkpoint NF4](https://huggingface.co/unsloth/Inkling-2-Mini-unsloth-bnb-4bit)

Los 48 bancos de expertos empaquetados usan NF4 con doble cuantización. La configuración excluye los routers, el codificador de imágenes, la cabeza y las proyecciones de los `message gates` de las pasadas. Los 144 tensores de gate se publican como `controllers`, con 48 proyecciones BF16 y 96 FP32. Transformers los renombra al cargar y exige FP32 para las proyecciones de actualización y olvido. El preflight comprueba los bancos, los tipos de todos los gates y las referencias a shards. Una receta genérica que sustituye solo los `Linear` puede omitir bancos tensoriales de expertos y alterar los gates. [Configuración del paquete](https://huggingface.co/unsloth/Inkling-2-Mini-unsloth-bnb-4bit/blob/22035f8bf3fd71a588d78591f8b3ec45c0994524/config.json) · [Receta de fine-tuning](https://unsloth.ai/docs/models/inkling-2-mini/fine-tuning)

## Runtimes

| Componente | Entorno aislado | Evidencia y límite |
|---|---|---|
| PyTorch / torchvision / xformers | 2.8.0+cu128 / 0.23.0+cu128 / 0.0.32.post2 | Conserva el build CUDA existente en otro entorno |
| Unsloth / Unsloth Zoo | `7421333ab85d1542211aa20408e094ec690c93c0` / `8f55ef9b49c9da040e8869bbbe9c750ed17bfe02` | Referencias de Git fijadas |
| Transformers / PEFT / TRL | 5.24.0 / 0.22.0 / 1.15.0 | La sobreinstalación de Transformers sigue la receta de Inkling. La declaración de dependencias de Unsloth sigue limitando Transformers |
| BitsAndBytes / Accelerate / TorchAO | 0.50.2 / 1.16.0 / 0.16.0 | El import y la ejecución física determinan compatibilidad con este Torch |
| llama.cpp | Runtime CUDA 12 de Unsloth `b12649-mix-c7059d6` | Validado por el SHA-256 publicado y comprobado con `--version`. El runtime previo `b11552` carece de esta arquitectura |

Versiones de paquetes inspeccionadas al preparar la fase incluyen Unsloth y Zoo 2026.11.12, Transformers 5.24.1, PEFT 0.22.0, TRL 1.19.0, BitsAndBytes 0.50.2, Accelerate 1.16.0 y PyTorch 2.15.0. La instalación conserva un entorno separado y registra `pip freeze` y `pip check`. La disponibilidad de una versión posterior no acredita que su combinación funcione en WSL2. [Notebook del proveedor](https://github.com/unslothai/notebooks/blob/main/nb/Kaggle-Inkling_2_Mini_(26B)-Conversational.ipynb) · [Build de llama.cpp](https://github.com/unslothai/llama.cpp/releases/tag/b12649-mix-c7059d6) · [Guía de inferencia](https://unsloth.ai/docs/models/inkling-2-mini)

**TESTED.** El runtime PyTorch 2.8.0 de la copia aislada importó `FastModel`, la clase nativa de Transformers y el `SFTTrainer` parcheado, y enumeró ambas GPU. Triton 3.4 inicialmente falló por ausencia de compilador y cabeceras. GCC 13 y cabeceras oficiales extraídas con `scripts/setup_inkling_compiler_wsl.sh` permitieron identificar el objetivo CUDA. El runtime llama.cpp requirió las bibliotecas `libcudart.so.12`, `libcublas.so.12` y `libcublasLt.so.12` del entorno cu128 existente. No se instaló un driver dentro de WSL2.

## Hardware y evidencia

Las dos tarjetas tienen 12 GB cada una. Fase 03-A verificó PCIe 4.0 x16 para la RTX 4070 y PCIe 3.0 x4 para la RTX 3060 bajo carga. WSL2 carece de P2P directo para este par. NCCL SHM y los smokes de DDP/FSDP con fixtures pequeñas pertenecen a Fase 03-A. La prueba Inkling usa reparto de capas y comprueba colocación por dispositivo. El soporte de tensor parallelism, pipeline parallelism y FSDP para este checkpoint sigue pendiente de evidencia específica. [Validación dual](MULTI_GPU_VALIDATION.md) · [QLoRA](QLORA_VALIDATION_REPORT.md) · [Goose](GOOSE_INTEGRATION.md)

Las pruebas físicas deben usar los UUID de forma privada, verificar que ambas GPU están libres, avisar a 80 °C y detenerse a 85 °C o ante inestabilidad. El resultado de una entrada sintética mide el funcionamiento de la ruta probada y no mide desempeño de CodeBench o CyberBench. Los identificadores de equipo, registros crudos y artefactos se conservan fuera de Git.
