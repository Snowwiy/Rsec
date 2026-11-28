# Adquisición de Inkling 2 Mini · Fase 03-B

La adquisición aprobada incluye dos formatos con funciones diferentes. Conservar una carpeta por formato en la biblioteca privada y reutilizar los archivos verificados. El espacio libre antes de comenzar fue **343 305 854 976 bytes** en el volumen de datos.

**TESTED.** Se comprobaron los 15 archivos contra los manifiestos fijados. Los dos paquetes completos ocupan **32 842 257 615 bytes** y quedaron **255 185 674 240 bytes libres** al verificarlos. Las copias comprobadas y los manifiestos de verificación se conservan en almacenamiento privado.

| Artefacto | Revisión fijada | Bytes exactos |
|---|---|---:|
| Inkling-2-Mini-UD-Q4_K_M.gguf | `8078d149286eec7193795413b9e0643da6d11fa1` | 16 610 544 608 |
| mmproj-BF16.gguf | La misma revisión GGUF | 641 805 760 |
| Cuatro shards NF4 y nueve archivos auxiliares | `22035f8bf3fd71a588d78591f8b3ec45c0994524` | 15 589 907 247 |
| **Total autorizado** | **15 archivos** | **32 842 257 615** |

Usar HTTPS y el manifiesto de cada revisión. Escribir a un archivo parcial en el mismo destino y reanudar desde el último byte confirmado. Comparar tamaños exactos y SHA-256 de los objetos LFS. Para los auxiliares Git, reproducir el identificador Git del blob y conservar el SHA-256 local para auditoría. Publicar cada archivo localmente sólo tras verificarlo. El preflight del backend revisa aparte arquitectura, índice, número de bancos, tipos de tensor, límites y rutas relativas.

El paquete GGUF `Mainline_Support`, otros niveles de cuantización, el drafter, Granite y el checkpoint original de Thinking Machines están fuera de esta adquisición. Los aproximadamente 20 GB del original sirven de referencia para una posible fusión futura. [Revisión de inferencia](https://huggingface.co/unsloth/Inkling-2-Mini-GGUF/tree/8078d149286eec7193795413b9e0643da6d11fa1) · [Revisión NF4](https://huggingface.co/unsloth/Inkling-2-Mini-unsloth-bnb-4bit/tree/22035f8bf3fd71a588d78591f8b3ec45c0994524) · [Checkpoint del editor](https://huggingface.co/thinkingmachines/Inkling-2-Mini/tree/c9d028302cd0f035fdf8e7e91f089a4ce94d2195)

## Presupuesto posterior

| Concepto | Espacio a presupuestar |
|---|---:|
| Ambos paquetes autorizados | 32,84 GB o 30,59 GiB |
| Reserva para entorno aislado, runtime y cachés descartables | 10 GiB |
| Reserva inicial para adaptadores, recuperación y temporales del fixture | 2–5 GiB. Medir el tamaño real |
| Modelo completo fusionado en BF16 | Aproximadamente 53 GB de pesos |
| Conversión completa | La guía prevé alrededor de 150 GB libres adicionales durante el proceso |

La fusión y la exportación completa permanecen pendientes. La RAM física de 32 GB queda por debajo del tamaño de los pesos BF16. Una ruta de exportación con memoria limitada debe demostrar escritura incremental de shards, conservación del proyector, de los gates y del bucle compartido, y una comparación de salidas al volver a cargar el artefacto. Una alternativa sería infraestructura externa autorizada con memoria y almacenamiento suficientes. La exportación del adaptador Safetensors tiene una huella independiente y se prueba en el fixture QLoRA. [Guía de entrenamiento y exportación de Unsloth](https://unsloth.ai/docs/models/inkling-2-mini/fine-tuning)
