# Inventario privado de modelos

El inventario de la carpeta de modelos en Windows reconoció 13 cabeceras GGUF y dos grupos Safetensors. Identificó candidatos para programación, razonamiento y embeddings. No apareció un adaptador LoRA ni un paquete generativo Transformers completo en esa carpeta. La carpeta de embeddings contiene configuración y tokenizer. Los requisitos de licencia, integridad y compatibilidad siguen sujetos a cada modelo. El inventario detallado se guarda fuera de Git.

El escáner lee cabeceras GGUF y metadatos escalares iniciales acotados, agrupa shards Safetensors y reconoce marcadores LoRA, configuración y archivos de tokenizer/licencia. Omite enlaces y reparse points. Los pesos enlazados de un caché de Hugging Face pueden requerir inspección manual. Los blobs Ollama sin extensión requieren el inventario del runtime local.

Ejecutar `workstation.ps1 inventory` y consultar el JSON privado en la ruta anunciada. Para cada candidato confirmar revisión, tamaño/arquitectura, cuantización, integridad de shards, template, licencia, RAM/VRAM y tarea con una prueba local. Un indicador de tamaño de GGUF no acredita parámetros exactos. Revisar la tarjeta para distinguir embeddings, razonamiento y generación de código. Mantener pesos, identificadores y rutas en la estación. Usar GGUF para inferencia; seleccionar pesos Transformers completos y compatibles para QLoRA.
