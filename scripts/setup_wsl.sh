#!/usr/bin/env bash
set -euo pipefail
if ! uname -r | grep -qi microsoft; then
  echo 'This helper is intended for a WSL2 Linux distribution.' >&2
  exit 2
fi
bash scripts/setup_linux.sh
