#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 2 || -z "$1" ]]; then
  echo 'Uso: bash scripts/validate_gpu.sh GPU-UUID DIRECTORIO_INFORME' >&2
  exit 2
fi
export CUDA_VISIBLE_DEVICES="$1"
.venv/bin/rsec gpu validate --device 0 --output "$2"
