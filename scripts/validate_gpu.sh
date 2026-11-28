#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: validate_gpu.sh UUID NEW_DIRECTORY' >&2; exit 2; }
cd "$(dirname "$0")/.."
exec bash scripts/workstation_wsl.sh -m rsec.thermal --uuid "$1" --output "$2"
