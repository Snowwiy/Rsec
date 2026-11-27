# Decisión del modelo base · diferida

La prioridad es reutilizar un modelo local con pesos y derechos verificables. Falta el inventario de la estación. La referencia provisional del repositorio sigue siendo Qwen2.5-Coder-7B-Instruct, revisión c03e6d358207e414f1eca0bb1891e29f1db0e242. La publicación oficial identifica qwen2, Safetensors y Apache-2.0. Su orientación a código permite medir retención en CodeBench junto a tareas defensivas en CyberBench. El español, razonamiento técnico, uso de herramientas y calidad de remediación requieren comparación real contra otros candidatos locales.

Verificar tokenizer, chat template, shards completos y hashes de la copia disponible. Un 7B necesita aproximadamente 3.5 GB sólo para 7 mil millones de parámetros a cuatro bits; sumar escalas, adaptadores, activaciones, contexto y runtime. Medir antes de aceptar 12 GB de VRAM. Si no cabe, considerar un modelo local de 3–4B con revisión y licencia confirmadas. Reservar 12–32B para ensayos posteriores de inferencia/offload con medidas de RAM y almacenamiento. No se adquirieron pesos ni se eligió un modelo definitivo.

[Revisión oficial de Qwen](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct/tree/c03e6d358207e414f1eca0bb1891e29f1db0e242)
