# Fase 03-A · instalación local

## Continuidad de v0.3.0-alpha.2 · 2026-11-27

La fase dual reutilizó los entornos aislados de Windows y WSL2 con el mismo PyTorch cu128, NCCL y dependencias ML. Windows y WSL2 enumeraron la RTX 4070 y la RTX 3060. Mantener el VHDX, los modelos y los artefactos privados en la unidad de datos. [Hardware](HARDWARE_VALIDATION_REPORT.md) · [Pruebas](TEST_RESULTS.md)

El runtime nativo Windows de llama.cpp sólo enumeró la 4070. Para la 3060 y el reparto se añadió el binario oficial Linux b11552 CUDA 12.8 al VHDX. El archivo de 164 MiB se verificó contra el SHA-256 de la publicación. Se reutilizaron las bibliotecas CUDA del venv y se instaló libgomp1 en la distro dedicada para resolver el enlace faltante. [Publicación de llama.cpp](https://github.com/ggml-org/llama.cpp/releases/tag/b11552) · [Integración](LOCAL_INFERENCE_GUIDE.md)

## Instalación previa · v0.3.0-alpha.1

**TESTED.** Checkout nuevo en la unidad de datos, origin oficial y rama `feat/rsec-physical-validation-v0.3.0` del [PR #7](https://github.com/Snowwiy/Rsec/pull/7). La unidad tenía 333.1 GiB libres antes de clonar. Windows usa Python 3.12.16 portable y un venv separado en `.rsec-local/windows-venv`. La CLI, dependencias core y herramientas de desarrollo quedaron instaladas.

**TESTED.** Ubuntu 24.04 LTS se registró como WSL2 en un VHDX de la unidad de datos, con usuario Linux sin privilegios. Usa Python 3.12.3 con un venv en ext4 y PyTorch 2.8.0+cu128, Transformers 5.24.1, PEFT 0.22.0, TRL 1.19.0, BitsAndBytes 0.50.2, Accelerate 1.16.0, Safetensors 0.8.0 y Datasets 5.0.1. `pip check` pasó en ambos entornos. El runtime NCCL 2.27.3 forma parte de la instalación WSL2. Unsloth sigue opcional.

**GPU VALIDATION PENDING.** Windows detectó la RTX 4070 y WSL expuso `/dev/dxg`. Durante la instalación se mantuvo CUDA oculta en el entorno ML. La validación física queda sujeta a la confirmación del operador.

**TESTED.** La vista de revisión respondió por HTTP en loopback. El baseline local de llama.cpp respondió en CPU y se comprobó el chat desde Goose mediante su perfil aislado. Consulta [resultados](TEST_RESULTS.md).

## Reproducción y uso

1. Ejecutar `scripts/checkout_local.ps1 -Destination <checkout> -Branch feat/rsec-physical-validation-v0.3.0`. Admite un destino ausente o vacío. En un checkout verifica raíz y origin, actualiza la referencia de la rama y conserva las modificaciones locales.
2. Desde la raíz, `scripts/setup_windows.ps1 -PythonExe <python312>` crea el venv a partir de un Python 3.12 existente o portable. `scripts/workstation.ps1 inventory -Library <biblioteca>` guarda un inventario privado. `scripts/workstation.ps1 review` prepara el piloto de revisión y abre un servidor de loopback en primer plano.
3. Para instalar Ubuntu 24.04 LTS en la unidad de datos, usar `wsl.exe --install Ubuntu-24.04 --web-download --no-launch --location <directorio-vhdx> --name <distro>`. En esta estación se creó el usuario `rsec` dentro de la distro y se designó como predeterminado. Consultar [los comandos oficiales de WSL](https://learn.microsoft.com/windows/wsl/basic-commands).
4. Desde el checkout montado en WSL2, usar un `RSEC_CUDA_ENV` en ext4. Los lanzadores comparten esa ruta o aceptan `RSEC_CUDA_PYTHON` para seleccionar un intérprete explícito.

   ```bash
   export RSEC_CUDA_ENV="$HOME/.local/share/rsec/cuda-venv"
   export PIP_CACHE_DIR="$HOME/.cache/rsec/pip"
   export TMPDIR="$HOME/.cache/rsec/tmp"
   bash scripts/setup_cuda.sh --install-only
   ```

5. Seguir [el plan físico](GPU_VALIDATION_PLAN.md) y [la secuencia distribuida](MULTI_GPU_VALIDATION.md). El launcher Windows de CUDA requiere un venv CUDA propio o el intérprete indicado en `-PythonExe`.

Los servidores de revisión e inferencia escuchan en loopback y se ejecutan en primer plano. Un puerto ocupado cancela el lanzamiento. Guardar inventarios, rutas de ejecutables, UUID, logs y configuraciones locales en `.rsec-local/`. Consultar [la guía de firmas](REVIEWER_SECURITY.md) para promover revisiones reales.
