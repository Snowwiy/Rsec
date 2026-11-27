#!/usr/bin/env bash
set -euo pipefail
[[ $# == 3 ]] || { echo 'Usage: validate_multi_gpu.sh UUID_4070 UUID_3060 NEW_DIRECTORY' >&2; exit 2; }
cd "$(dirname "$0")/.."
exec "${RSEC_CUDA_PYTHON:-.rsec-local/linux-venv/bin/python}" -m rsec.thermal --uuid "$1" --uuid "$2" --output "$3"
