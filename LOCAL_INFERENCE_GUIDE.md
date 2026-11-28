# Inferencia local y comprobación del backend

## Perfiles de la estación dual · v0.3.0-alpha.2

| Perfil | Ruta |
|---|---|
| GAMING | llama.cpp en WSL2 sobre la RTX 3060 por UUID. Hasta dos hilos de cálculo, contexto 2048 y GGUF de 4 GiB como máximo |
| AGENT | Un UUID explícito para el servidor y Goose conectado por loopback con su perfil aislado |
| TRAINING SINGLE-GPU | Perfiles `local_rtx4070` y `local_rtx3060` para elegir una GPU. Supervisar la fixture por UUID |
| TRAINING DUAL-GPU | Perfil DDP y supervisor con dos UUID. FSDP sólo para el caso físico y las capas verificadas |
| INFERENCE DUAL-GPU | llama.cpp WSL2 por UUID, modo `layer` con reparto configurable y margen previo de VRAM |

El llama.cpp Windows de la estación sólo expuso la 4070. El lanzador PowerShell comprueba qué adaptadores reporta el runtime antes de cargar pesos y rechaza resultados incompletos. En WSL2 se usó el binario compatible de la misma revisión y las bibliotecas CUDA ya instaladas.

```bash
# Preparar RSEC_LLAMA_SERVER y las bibliotecas del runtime en la distro.
RSEC_LLAMA_PROFILE=gaming RSEC_LLAMA_MMAP=0 bash scripts/llama_wsl.sh '<modelo.gguf>' "$GPU_3060"
RSEC_LLAMA_PROFILE=inference-dual RSEC_LLAMA_SPLIT=2,1 RSEC_LLAMA_MMAP=0 \
  bash scripts/llama_wsl.sh '<modelo.gguf>' "$GPU_4070" "$GPU_3060"
```

En reparto por capas, el orden de UUID controla la asociación de cada peso de reparto con cada GPU. El índice principal sólo se aplica a `row` o a la selección de un dispositivo. Los ensayos de esta fase usan `layer`. La memoria libre se comprueba antes del arranque. En esta revisión, el modo de lectura directa usa `--load-mode none`.

[Referencia de llama-server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) · [Mediciones](MULTI_GPU_BENCHMARK.md)

Desde el checkout en PowerShell, usar llama-server desde PATH o indicar su ejecutable con `-LlamaServerExe`. En una consola ejecutar `& .\scripts\workstation.ps1 inference -Model "RUTA AL ARCHIVO.gguf" -Port 8081 -Context 2048 -Threads 1`. El perfil predeterminado ejecuta en CPU. Añadir `-GpuUuid UUID_REAL` sólo después de validar la compilación CUDA. El servidor se mantiene en primer plano y escucha en 127.0.0.1. Ante un puerto ocupado, inspeccionar el servicio existente.

En otra consola ejecutar `& .\scripts\workstation.ps1 probe -Port 8081`. Comprueba el alias local-baseline en el catálogo y solicita como máximo ocho tokens con temperatura 0 y top-p 1. Registra tokens y latencia de extremo a extremo sin guardar el texto. Repetir con contexto y presupuestos idénticos para comparar backends. El cliente usa HTTP directo a loopback, sin proxy ni redirecciones.

Prueba ejecutada en Linux CPU: llama.cpp b671865c, GGUF Q4_K_M diminuto ya existente, dos hilos, contexto 512. Una respuesta de ocho tokens en 31.5 ms (~254 tokens/s de extremo a extremo). Es una comprobación del protocolo con pesos técnicos; no mide rendimiento de la estación, competencia del modelo ni carga sostenida. El servidor se detuvo al terminar. Para uso de CLI sin servidor se conserva `rsec infer --help`. Véase la [referencia oficial de llama-server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
