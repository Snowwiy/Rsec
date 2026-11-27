#!/usr/bin/env bash
# Use after checking the installed host driver supports cu128.
set -euo pipefail
case "${1:-}" in
  '') ;;
  --install-only) export CUDA_VISIBLE_DEVICES="" ;;
  *) echo 'Usage: setup_cuda.sh [--install-only]' >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { echo 'Usage: setup_cuda.sh [--install-only]' >&2; exit 2; }
cd "$(dirname "$0")/.."
if [[ $# == 0 ]]; then nvidia-smi; fi
export HF_HOME="$PWD/.rsec-local/cache/huggingface" HF_HUB_CACHE="$PWD/.rsec-local/cache/huggingface/hub" HF_DATASETS_CACHE="$PWD/.rsec-local/cache/datasets"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.rsec-local/cache/pip}"
export TMPDIR="${TMPDIR:-$PWD/.rsec-local/tmp}"
mkdir -p "$TMPDIR"
venv="${RSEC_CUDA_ENV:-$PWD/.rsec-local/linux-venv}"
if [[ ! -e "$venv" ]]; then python3.12 -m venv "$venv"; fi
"$venv/bin/python" -c 'import sys; assert sys.prefix != sys.base_prefix'
"$venv/bin/python" -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
"$venv/bin/python" -c 'from importlib.metadata import version; raise SystemExit(version("torch") != "2.8.0+cu128")'
"$venv/bin/python" -m pip install -r requirements-train.txt -e .
"$venv/bin/python" -m pip check
if [[ $# == 0 ]]; then
  "$venv/bin/python" -c 'import torch; assert torch.cuda.is_available(), "Installed torch cannot use CUDA"'
fi
