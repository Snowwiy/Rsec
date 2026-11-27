#!/usr/bin/env bash
# Start a project-local GPU interpreter without exporting settings to the parent.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HOME="$PWD/.rsec-local/cache/huggingface" HF_HUB_CACHE="$PWD/.rsec-local/cache/huggingface/hub" HF_DATASETS_CACHE="$PWD/.rsec-local/cache/datasets"
export TORCH_HOME="$PWD/.rsec-local/cache/torch" TMPDIR="$PWD/.rsec-local/tmp" HF_HUB_OFFLINE=1
mkdir -p "$TMPDIR"
exec "${RSEC_CUDA_PYTHON:-${RSEC_CUDA_ENV:-.rsec-local/linux-venv}/bin/python}" "$@"
