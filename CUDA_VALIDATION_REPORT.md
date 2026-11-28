# CUDA · v0.3.0-alpha.2

**VALIDATED en WSL2.** PyTorch 2.8.0+cu128 enumeró dos dispositivos. Por UUID, cada ejecución individual vio una sola GPU como índice lógico 0. Las operaciones matriciales verificaron valores, dtype y dispositivo para FP16 y BF16 nativo en ambas tarjetas.

| GPU | PyTorch CUDA | FP16 | BF16 nativo | Compute capability |
|---|---|---|---|---|
| RTX 4070 | VALIDATED | VALIDATED | VALIDATED | 8.9 |
| RTX 3060 | VALIDATED | VALIDATED | VALIDATED | 8.6 |

La prueba supervisada consulta ambas tarjetas durante la validación individual. El proceso de cálculo sólo recibe el UUID elegido. El pico asignado por Torch se informa aparte del uso global observado por NVIDIA. Los resultados de inferencia de Windows dependen del binario nativo. [Hardware y PCIe](HARDWARE_VALIDATION_REPORT.md) · [Comparación](MULTI_GPU_BENCHMARK.md)
