# Preparación local y diagnóstico de GPU

Esta guía parte de Windows 11 y WSL2/Linux. El entorno de desarrollo reportó PyTorch 2.8.0+cpu y ningún dispositivo CUDA. La instalación física y validación dependen del equipo del propietario. GPU READINESS se mantiene en VALIDATION PENDING.

## Checkout y entorno CPU

```bash
git clone https://github.com/Snowwiy/Rsec.git
cd Rsec
git switch feat/rsec-expert-curation-v0.2.1
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt -e .
rsec doctor --output reports/doctor-local.json --markdown reports/doctor-local.md
```

En PowerShell, usa `py -3.12 -m venv .venv`, después `& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -e .` y `& .\.venv\Scripts\rsec.exe gpu diagnose --output reports\doctor-win.json --markdown reports\doctor-win.md`. Desde WSL2 valida primero la visibilidad del driver del host con `nvidia-smi`.

## CUDA y selección inequívoca

Usa otro entorno virtual si el actual contiene el lock CPU. Instala la rueda CUDA 2.8.0 compatible con el driver mediante el índice oficial. El comando candidato abajo aplica cuando el driver soporta CUDA 12.8. Verifica esa condición en el equipo antes de instalar. Consulta [versiones oficiales de PyTorch](https://pytorch.org/get-started/previous-versions/).

```bash
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements-train.txt -e .
python -m pip check
python -m pip freeze > reports/cuda-stack.txt
rsec gpu list
rsec gpu diagnose --output reports/gpu-local.json --markdown reports/gpu-local.md
```

Core y dev usan `requirements.txt` y `requirements-dev.txt`. CPU ML usa `requirements-cpu-test.lock` más la rueda CPU. CUDA y multi-GPU comparten el stack `requirements-train.txt` y las configuraciones Accelerate. Los runtimes nativos opcionales van en un entorno separado siguiendo `docs/DEPENDENCIES.md`. La similitud por vectores exportados no requiere dependencias adicionales de embeddings en core. Unsloth sigue bloqueado por incompatibilidad con los pins vigentes.

Selecciona UUID de `rsec gpu list` para cada tarjeta y copia los valores reales a estas variables. El índice CUDA 0 identifica la GPU visible dentro de cada proceso. No presupongas orden entre NVML y CUDA ni equivalencia con el índice de Windows.

```bash
GPU_4070=GPU-REEMPLAZAR_UUID_4070
GPU_3060=GPU-REEMPLAZAR_UUID_3060
bash scripts/validate_gpu.sh "$GPU_4070" reports/4070-smoke
bash scripts/validate_gpu.sh "$GPU_3060" reports/3060-smoke
CUDA_VISIBLE_DEVICES="$GPU_4070" rsec gpu benchmark --device 0 --steps 20 --output reports/4070-matmul.json
CUDA_VISIBLE_DEVICES="$GPU_3060" rsec gpu benchmark --device 0 --steps 20 --output reports/3060-matmul.json
```

En PowerShell con CUDA compatible usa `& .\scripts\validate_gpu.ps1 -GpuUuid 'GPU-UUID_REAL' -OutputDirectory 'reports\single-smoke'` por tarjeta. El script restaura la variable del proceso. Los smoke tests requieren CUDA real y prueban FP16, BF16 nativo cuando está disponible, NF4, LoRA, actualización, persistencia, recuperación de optimizador e inferencia sobre una capa diminuta. No instalan drivers ni cambian configuraciones globales. Compara valores medidos con el reporte de topología y perfila modelos completos únicamente tras estos pasos.
