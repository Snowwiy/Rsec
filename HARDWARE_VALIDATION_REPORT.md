# Hardware · v0.3.0-alpha.2 · 2026-11-27

Windows 11 y Ubuntu 24.04 WSL2 detectaron las dos GPU con el controlador Windows 621.40. PyTorch 2.8.0+cu128 comprobó la identidad por UUID, asignando el índice lógico 0 a la GPU elegida en cada prueba individual.

| Medida | RTX 4070 | RTX 3060 |
|---|---:|---:|
| Compute capability | 8.9 | 8.6 |
| VRAM total | 12,282 MiB | 12,288 MiB |
| VRAM libre Windows al iniciar | 10,319 MiB | 11,633 MiB |
| Núcleo al iniciar | 45.48 °C | 60.88 °C |
| Potencia inicial | 56.40 W | 45.72 W |
| Límite efectivo / predeterminado | 215 / 215 W | 187 / 170 W |
| PCIe máximo de la GPU | 4.0 ×16 | 4.0 ×16 |
| PCIe negociado observado | 4.0 ×16 | 3.0 ×4 |
| FP16 y BF16 nativo | VALIDATED | VALIDATED |
| CUDA peer access hacia la otra GPU | No | No |

Windows reportó una ruta PXB a través de varios puentes PCIe y acceso P2P de lectura y escritura no soportado. La 3060 quedó en Gen 3 ×4 en esta configuración. Es una limitación observada del enlace de la estación. La razón exacta del slot requiere documentación de la placa. WSL2 admite la consulta de enlaces por dispositivo y devuelve que `nvidia-smi topo` no está soportado. NCCL usó memoria compartida del host para la comunicación de datos.

El propietario declaró un Ryzen 9 5900X, 32 GB DDR4 a 3333 MT/s, fuente MSI de 1000 W y seis ventiladores de entrada con tres de extracción. Las dos asignaciones de VRAM son independientes. Los procesos gráficos residentes incluían servicios de escritorio y Steam. El inventario previo a las pruebas carecía de juego, OBS o servidor de inferencia activo.

[Mediciones bajo carga](MULTI_GPU_BENCHMARK.md) · [Supervisión térmica](THERMAL_VALIDATION_REPORT.md)
