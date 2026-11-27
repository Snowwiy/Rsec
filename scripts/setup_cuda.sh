#!/usr/bin/env bash
# Use after checking the installed host driver supports cu128.
set -euo pipefail
cd "$(dirname "$0")/.."
nvidia-smi
export HF_HOME="$PWD/.rsec-local/cache/huggingface" HF_HUB_CACHE="$PWD/.rsec-local/cache/huggingface/hub" HF_DATASETS_CACHE="$PWD/.rsec-local/cache/datasets"
export PIP_CACHE_DIR="$PWD/.rsec-local/cache/pip" TMPDIR="$PWD/.rsec-local/tmp"
mkdir -p "$TMPDIR"
venv="${RSEC_CUDA_ENV:-$PWD/.rsec-local/linux-venv}"
if [[ ! -e "$venv" ]]; then python3.12 -m venv "$venv"; fi
"$venv/bin/python" -c 'import sys; assert sys.prefix != sys.base_prefix'
"$venv/bin/python" -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
"$venv/bin/python" -c 'import torch; assert torch.version.cuda and torch.cuda.is_available(), "Installed torch cannot use CUDA"'
"$venv/bin/python" -m pip install -r requirements-train.txt -e .
"$venv/bin/python" -m pip check
