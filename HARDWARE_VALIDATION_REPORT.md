# Hardware · evidencia pública

| Recurso | Estado de evidencia |
|---|---|
| Windows 11, Ryzen 9 5900X, 32 GB DDR4 | Configuración de la estación. Windows reportó 31.9 GiB de memoria visible y 12.4 GiB libres en una lectura |
| RTX 4070, driver NVIDIA 621.40 | Detectada mediante `nvidia-smi` y el inventario de dispositivos conectados. 12,282 MiB totales. Una lectura de preparación registró 4,238 MiB libres y 39.07 °C |
| SSD/NVMe, fuente MSI 1000 W, nueve ventiladores | Inventario declarado. Temperaturas y potencia pendientes |
| CUDA y WSL2 | El controlador reportó CUDA UMD 13.5. Ubuntu 24.04 quedó registrado como WSL2 y expuso `/dev/dxg`. El runtime instalado de Torch es cu128 |
| RTX 3060 | Pendiente de instalación. El inventario de Windows detectó una sola GPU |
| Pruebas bajo carga | GPU VALIDATION PENDING. La lectura puntual no mide picos, potencia sostenida ni estabilidad |

Conservar UUID, rutas de ejecutables, listeners y topología sólo en las salidas privadas. Registrar también fecha, versión de driver, memoria libre al inicio y pico por proceso antes de publicar únicamente el resumen aprobado. Véase [instalación](LOCAL_INSTALLATION_REPORT.md).
