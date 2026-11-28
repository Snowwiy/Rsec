# Comparación física RTX 4070 y RTX 3060 · v0.3.0-alpha.2

Mediciones de la estación el 2026-11-27. PyTorch 2.8.0+cu128 sobre WSL2, driver 621.40. La configuración se seleccionó por UUID. Se midió cada carga antes de definir el perfil recomendado. Las cifras de las fixtures no predicen el rendimiento de entrenamiento de un LLM.

## CUDA individual · NF4 y LoRA

| GPU | FP16 / BF16 | NF4 doble / LoRA | Paso en frío | Pico Torch | Guardado / recuperación | Núcleo máximo |
|---|---|---|---:|---:|---:|---:|
| RTX 4070 | VALIDATED | VALIDATED | 621 ms | 16.3 MiB | 60.5 / 16.8 ms | 44.2 °C |
| RTX 3060 | VALIDATED | VALIDATED | 245 ms | 16.3 MiB | 40.9 / 19.5 ms | 56.5 °C |

Cuatro vectores, misma capa, semilla y estado inicial. Pérdida inicial 0.38484 y pérdida tras reanudar 0.36392 en ambas GPU. Se verificaron los hashes de los artefactos, la inferencia recuperada y el segundo paso del optimizador. El paso en frío incluye inicialización y su variación impide usarlo para ordenar las tarjetas.

## A/B/C/E · mismo trabajo denso

Embeddings y una proyección diminuta en FP32. Semilla 923, batch global 8, secuencia 128, ocho pasos de calentamiento y 64 medidos. Cada trabajo procesó 65,536 posiciones sintéticas. DDP repartió las ocho secuencias en dos ranks y se usó el tiempo del rank más lento para el throughput.

El supervisor usa `--mode compare` con un UUID para A/B, `--mode ddp` con dos UUID para C y `--mode independent` con dos para E. Usar directorios privados nuevos y observar ambas GPU también durante las pruebas individuales.

| Configuración | Posiciones/s | Paso medio | Ventana medida | Pico Torch por GPU | Pico RSS por trabajador | Checkpoint / recuperación |
|---|---:|---:|---:|---:|---:|---:|
| A · RTX 4070 | 1,019,602 | 1.00 ms | 64.3 ms | 38.3 MiB | 1.05 GiB | 163 / 70 ms |
| B · RTX 3060 | 1,090,975 | 0.94 ms | 60.1 ms | 38.3 MiB | 1.05 GiB | 158 / 77 ms |
| C · DDP en dos GPU | 374,023 | 2.74 ms | 175.2 ms | 32.8 / 32.8 MiB | 1.38 / 1.36 GiB | 200 / 90 ms¹ |
| E · independiente en 4070 | 1,028,199 | 1.00 ms | 63.7 ms | 38.3 MiB | 1.15 GiB | 172 / 72 ms |
| E · independiente en 3060 | 938,596 | 1.09 ms | 69.8 ms | 38.3 MiB | 1.14 GiB | 174 / 77 ms |

¹ Máximo entre ranks. Los valores de RAM son por trabajador. Las ventanas de dos procesos independientes se reportan por separado. La prueba conserva un trabajo completo por GPU en E.

NCCL 2.27.3 usó SHM para datos. Para ocho all-reduce calientes, la media observada por rank fue de 90–91 μs con 4 KiB y 2.81–2.90 ms con 4 MiB. La barrera posterior a la ventana DDP fue de 0.56 y 9.17 ms por rank e incluye espera de llegada. El host de esta prueba mostró una penalización clara de DDP para el trabajo diminuto. Esta medición no permite atribuir la espera a una sola tarjeta ni inferir cuál ganaría en un entrenamiento real.

## D · FSDP 1 + QLoRA

Fixture diferente de A/B/C/E, con NF4 doble y almacenamiento/cómputo BF16. FSDP redujo los 1,536 elementos empaquetados a 768 por rank. Paso medio de 5.45 ms en la 4070 y 5.43 ms en la 3060, con 16.3 MiB de pico Torch en cada una. Una repetición registró picos RSS de 1.74 y 1.75 GiB por rank. El checkpoint completo tardó hasta 68.7 ms y su restauración 32.8 ms. Los dos archivos del checkpoint distribuido se verificaron por SHA-256 y reprodujeron la salida tras recuperarse, con 313 ms para guardar y 67 ms para restaurar. El adaptador se exportó en Safetensors. La ventana de ocho pasos equivale aproximadamente a 1,468 vectores sintéticos/s entre ambos ranks.

## F · llama.cpp CUDA en WSL2

Build b11552 CUDA 12.8, dos hilos de cálculo, una sola solicitud activa, lectura directa y un calentamiento por configuración. Se midieron dos solicitudes de 32 tokens con el mismo prompt por modelo. La variante menor usó contexto 2048 y el 14B, contexto 512.

El cliente llamó a `/completion` con temperatura 0, `cache_prompt=false`, `ignore_eos=true` y el prompt “Give a concise, beginner-friendly description of what a Python list is and how to append a value.” Se solicitó un calentamiento de cuatro tokens y luego 32 tokens por medición. [Lanzadores de inferencia](LOCAL_INFERENCE_GUIDE.md)

| Modelo / perfil | Generación, tokens/s observados | Latencia HTTP por 32 tokens | Carga / sesión total | Buffers de pesos 4070 / 3060 | Pico RSS del servidor |
|---|---:|---:|---:|---:|---:|
| GGUF pequeño · 4070 | 124.05 / 35.40 | 277 / 900 ms | 14.4 / 16.0 s | 1,842 / — MiB | 0.64 GiB |
| GGUF pequeño · 3060 | 98.05 / 56.88 | 356 / 583 ms | 25.7 / 29.4 s | — / 1,842 MiB | 0.64 GiB |
| GGUF 14B Q4 · 4070 | 42.27 / 42.44 | 772 / 778 ms | 42.0 / 44.0 s | 8,148 / — MiB | 0.86 GiB |
| GGUF 14B Q4 · 2:1 por capas | 35.17 / 35.69 | 927 / 922 ms | 41.5 / 43.9 s | 5,155 / 2,993 MiB | 1.05 GiB |
| GGUF 14B Q4 · 1:1 por capas | 33.56 / 32.78 | 975 / 1,015 ms | 42.0 / 44.6 s | 3,917 / 4,231 MiB | 1.05 GiB |

La media del 14B en la 4070 fue 42.35 tokens/s. El reparto 2:1 alcanzó 35.43 tokens/s, frente a 33.17 en 1:1. 2:1 redujo unos 2.9 GiB de buffers de la 4070 y rindió cerca de 16 % menos que la 4070 exclusiva. La primera carga del 14B se interrumpió por el límite de disponibilidad a los 145 s mientras transfería pesos. Las repeticiones no controlaron el estado de la caché de archivos. Los dos ensayos pequeños variaron demasiado para ordenar las tarjetas con precisión.

La 3060 exclusiva también respondió a Goose. El servidor registró dos solicitudes breves de chat de unos 147 y 121 ms entre prefill y generación. Esos tiempos excluyen el arranque de Goose y el cruce de loopback. [Integración](GOOSE_INTEGRATION.md)

## Potencia, VRAM y límites

| Ejecución | RTX 4070, °C / W medios / W pico / MiB pico | RTX 3060, °C / W medios / W pico / MiB pico |
|---|---|---|
| A · RTX 4070 | 44.3 / 57.6 / 62.1 / 1,922 | 57.8 / 45.0 / 45.3 / 682 |
| B · RTX 3060 | 44.2 / 55.9 / 56.1 / 1,646 | 58.5 / 46.1 / 50.1 / 903 |
| C · DDP | 44.9 / 59.1 / 68.7 / 2,027 | 58.6 / 45.5 / 47.3 / 961 |
| D · FSDP | 45.1 / 57.8 / 68.5 / 1,984 | 59.3 / 45.7 / 46.6 / 951 |
| E · independiente | 44.2 / 56.3 / 57.9 / 1,922 | 59.4 / 46.1 / 50.1 / 903 |
| F · pequeño 4070 | 46.8 / 57.9 / 91.9 / 3,791 | 53.6 / 43.9 / 44.4 / 682 |
| F · pequeño 3060 y Goose | 44.9 / 56.2 / 56.6 / 1,684 | 66.8 / 48.7 / 103.8 / 2,777 |
| F · 14B 4070 | 54.3 / 59.7 / 190.2 / 10,269 | 55.4 / 43.9 / 45.3 / 682 |
| F · 14B 2:1 | 50.1 / 61.0 / 155.0 / 7,320 | 66.2 / 46.1 / 97.4 / 3,981 |
| F · 14B 1:1 | 49.2 / 59.8 / 112.8 / 6,073 | 64.3 / 48.0 / 113.1 / 5,237 |

NVIDIA mide el dispositivo completo e incluye procesos residentes, inicialización y recuperación. La ventana de cálculo es más corta que el intervalo de muestreo, así que dividir posiciones/s por la potencia media no daría una eficiencia fiable. No se alteraron parámetros eléctricos ni térmicos. [Detalle térmico](THERMAL_VALIDATION_REPORT.md)

## Elección operativa

Para el 14B medido, preferir la 4070 cuando haya VRAM disponible. Usar el reparto 2:1 cuando se necesite liberar espacio en la 4070 y el costo en latencia sea aceptable. Reservar la 4070 para el juego y usar el perfil GAMING de la 3060 para Goose con el baseline pequeño. La prueba concurrente con un juego real queda pendiente. Para dos trabajos independientes, asignar un UUID a cada uno. Medir una carga representativa antes de elegir DDP por velocidad o FSDP por capacidad.
