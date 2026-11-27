#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: validate_gpu.sh UUID NEW_DIRECTORY' >&2; exit 2; }
cd "$(dirname "$0")/.."
python="${RSEC_CUDA_PYTHON:-.rsec-local/linux-venv/bin/python}"
if [[ ! -x "$python" && -z "${RSEC_CUDA_PYTHON:-}" ]]; then python=.venv/bin/python; fi
exec "$python" -m rsec.thermal --uuid "$1" --output "$2"
