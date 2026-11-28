#!/usr/bin/env bash
# Local llama.cpp with explicit CUDA devices and a bounded workstation profile.
set -euo pipefail
die() { echo "$*" >&2; exit 2; }
[[ $# == 2 || $# == 3 ]] || die 'Usage: llama_wsl.sh MODEL.gguf UUID [UUID]'
model=$1
shift
[[ -f "$model" && "${model,,}" == *.gguf ]] || die 'Select a local GGUF file'
[[ -x "${RSEC_LLAMA_SERVER:-}" ]] || die 'Set RSEC_LLAMA_SERVER to the installed llama-server'
profile=${RSEC_LLAMA_PROFILE:-agent}
context=${RSEC_LLAMA_CONTEXT:-2048}
threads=${RSEC_LLAMA_THREADS:-2}
port=${RSEC_LLAMA_PORT:-8081}
[[ "$context" =~ ^[1-9][0-9]{0,4}$ && "$threads" =~ ^[1-9]$ && "$port" =~ ^[1-9][0-9]{0,4}$ ]] ||
  die 'Use decimal context, thread count and port'
(( context >= 128 && context <= 32768 && threads <= 8 && port <= 65535 )) ||
  die 'Context, threads or port outside the supported bounds'
case "$profile:$#" in
  agent:1|gaming:1|inference-dual:2) ;;
  *) die 'Use agent or gaming with one UUID and inference-dual with two UUIDs' ;;
esac
[[ $# == 1 || "$1" != "$2" ]] || die 'Select distinct GPU UUIDs'
names=()
free_mib=()
for uuid in "$@"; do
  [[ "$uuid" =~ ^GPU-[0-9a-fA-F-]{36}$ ]] || die 'Select a complete NVIDIA UUID'
  line=$(nvidia-smi -i "$uuid" --query-gpu=name,memory.free --format=csv,noheader,nounits)
  names+=("${line%%,*}")
  free=${line##*, }
  [[ "$free" =~ ^[0-9]+$ ]] || die 'GPU free memory is unavailable'
  free_mib+=("$free")
done
bytes=$(stat -c %s -- "$model")
if [[ "$profile" == gaming ]]; then
  [[ "${names[0]}" == 'NVIDIA GeForce RTX 3060' ]] || die 'Gaming profile reserves the RTX 4070'
  (( context <= 2048 && threads <= 2 && bytes <= 4 * 1024**3 )) || die 'Gaming profile requires a small model, context and thread budget'
fi
device=(--device CUDA0 --split-mode none --main-gpu 0)
if [[ "$profile" == inference-dual ]]; then
  split=${RSEC_LLAMA_SPLIT:-2,1}
  [[ "$split" =~ ^([1-9][0-9]{0,2}),([1-9][0-9]{0,2})$ ]] || die 'Specify two positive split weights from 1 to 999'
  a=${BASH_REMATCH[1]}
  b=${BASH_REMATCH[2]}
  (( free_mib[0] * 1024**2 >= bytes * a / (a+b) + 1024**3 &&
     free_mib[1] * 1024**2 >= bytes * b / (a+b) + 1024**3 )) || die 'Insufficient free VRAM for weights and buffers'
  mode=${RSEC_LLAMA_SPLIT_MODE:-layer}
  main=${RSEC_LLAMA_MAIN_GPU:-0}
  [[ "$mode" == layer || "$mode" == row ]] || die 'Use layer or row splitting'
  [[ "$main" == 0 || "$main" == 1 ]] || die 'Main GPU must be CUDA index 0 or 1'
  device=(--device CUDA0,CUDA1 --split-mode "$mode" --tensor-split "$split")
  if [[ "$mode" == row ]]; then device+=(--main-gpu "$main"); fi
else
  (( free_mib[0] * 1024**2 >= bytes + 768 * 1024**2 )) || die 'Insufficient free VRAM for weights and buffers'
fi
export CUDA_VISIBLE_DEVICES="$(IFS=,; echo "$*")"
inventory=$("$RSEC_LLAMA_SERVER" --list-devices 2>&1)
mapfile -t available < <(sed -nE 's/^[[:space:]]*CUDA[0-9]+:[[:space:]]*(.+) \(.*/\1/p' <<< "$inventory")
[[ "${available[*]}" == "${names[*]}" ]] || die 'llama.cpp CUDA inventory differs from the selected devices'
extra=()
if [[ "${RSEC_LLAMA_VERBOSE:-0}" == 1 ]]; then extra+=(--verbose); fi
if [[ "${RSEC_LLAMA_MMAP:-1}" == 0 ]]; then extra+=(--load-mode none); fi
exec "$RSEC_LLAMA_SERVER" -m "$model" --alias local-baseline --host 127.0.0.1 --port "$port" \
  -c "$context" -np 1 -t "$threads" -tb "$threads" --threads-http 2 -ngl 99 --offline --no-ui --fit off \
  --reasoning-budget 0 "${device[@]}" "${extra[@]}"
