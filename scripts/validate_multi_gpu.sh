#!/usr/bin/env bash
set -euo pipefail
[[ $# == 3 || $# == 4 ]] || { echo 'Usage: validate_multi_gpu.sh UUID_4070 UUID_3060 NEW_DIRECTORY [nccl|ddp|fsdp|independent]' >&2; exit 2; }
cd "$(dirname "$0")/.."
exec bash scripts/workstation_wsl.sh -m rsec.thermal --uuid "$1" --uuid "$2" --output "$3" --mode "${4:-ddp}"
