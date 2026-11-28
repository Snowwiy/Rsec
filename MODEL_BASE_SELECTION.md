# Modelo base · evaluación de candidatos · v0.3.0-alpha.2

**MODEL BASE READINESS BLOCKED.** Los dos grupos locales Safetensors pasaron comprobación de cabeceras, rangos de datos y lectura completa para obtener SHA-256. Los hashes privados no tienen un manifiesto del editor contra el cual autenticar la copia.

- El grupo de embeddings contiene un paquete Transformers de arquitectura de embeddings, con config, tokenizer y 1,376 tensores BF16. Carece de manifest de shards, adaptador y archivo local de licencia. La arquitectura y el propósito descartan su uso como base causal del trainer de Rsec.
- El grupo de imagen contiene dos componentes separados, un VAE BF16 y un bloque de texto con tensores BF16, F32 e INT8/UINT8. Carece de config generativo, tokenizer, índice de shards, manifiesto de adaptador y licencia local. La integridad de cabecera por archivo no demuestra que el grupo sea un paquete generativo completo y utilizable mediante LoRA/QLoRA.

| Candidato | Evidencia del editor | Decisión |
|---|---|---|
| Granite 3B Code Instruct 128K | Apache-2.0, Safetensors, Transformers, modelo de código | Primera evaluación por tamaño y propósito. Medir debugging, código y español en el mismo protocolo. [IBM Granite](https://huggingface.co/ibm-granite/granite-3b-code-instruct-128k) |
| Qwen3-4B-Instruct-2507 | Apache-2.0, Safetensors, qwen3, texto conversacional | Control de razonamiento, multilingüe y herramientas. Verificar plantilla y salida estructurada. [Qwen](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) |
| Qwen2.5-Coder-7B-Instruct | Apache-2.0, Safetensors, qwen2, orientación a código | Mantener la referencia fijada en configuración. Evaluar después de medir memoria y retención con el candidato pequeño. [Revisión fijada](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct/tree/c03e6d358207e414f1eca0bb1891e29f1db0e242) |
| Qwen3.5-4B | Apache-2.0, Safetensors, arquitectura multimodal qwen3_5 | Alternativa de investigación. El trainer causal de Rsec requiere validar la ruta de texto y exportación por separado. [Qwen](https://huggingface.co/Qwen/Qwen3.5-4B) |

Los archivos de configuración de los editores declaran LlamaForCausalLM para Granite, Qwen3ForCausalLM y Qwen2ForCausalLM para los Qwen de texto, y Qwen3_5ForConditionalGeneration para el multimodal. Las cuatro clases aparecen en el registro del conversor de llama.cpp b11552. Es evidencia de soporte en código. La conversión de los pesos concretos requiere su propio ensayo. [Conversor Llama](https://github.com/ggml-org/llama.cpp/blob/b11552/conversion/llama.py) · [Conversor Qwen](https://github.com/ggml-org/llama.cpp/blob/b11552/conversion/qwen.py)

Antes de aprobar un candidato, fijar revisión, licencia y manifiesto de artefactos. Confirmar tokenizer, plantilla y módulos objetivo de PEFT. Comparar salidas de Transformers y GGUF sobre ejemplos bilingües de código, defensivos y de herramientas. Las fixtures CUDA no aportan evidencia para entrenar un 12B–14B. La inferencia de un GGUF 14B pertenece a otra ruta. Quedan pendientes la obtención de pesos y la evaluación del paquete generativo.
