#!/usr/bin/env bash
# Prepare the isolated Inkling environment from the already validated CUDA stack.
set -euo pipefail
base=${RSEC_CUDA_ENV:?Set RSEC_CUDA_ENV to the validated CUDA venv}
env_dir=${RSEC_INKLING_ENV:-$HOME/.local/share/rsec/inkling-venv}
base=$(realpath "$base")
env_dir=$(realpath -m "$env_dir")
[[ "$env_dir" != "$base" && "$env_dir" != "$base/"* && "$base" != "$env_dir/"* ]] ||
  { echo 'Use separate environment roots' >&2; exit 2; }
[[ -x "$base/bin/python" ]] || { echo 'Validated CUDA Python missing' >&2; exit 2; }
export CUDA_VISIBLE_DEVICES="" PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_PROGRESS_BAR=off
export PIP_CACHE_DIR=${RSEC_INKLING_PIP_CACHE:-$HOME/.cache/rsec/inkling-pip}
python="$env_dir/bin/python"
if [[ ! -e "$env_dir" ]]; then
  "$base/bin/python" -m venv "$env_dir"
  base_packages=$("$base/bin/python" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
  private_packages=$("$python" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
  cp -a --reflink=auto "$base_packages/." "$private_packages/"
fi
[[ -x "$python" ]] || { echo 'Inspect incomplete isolated environment' >&2; exit 2; }
"$python" -c 'from importlib.metadata import version; raise SystemExit(version("torch") != "2.8.0+cu128")'
constraints="$env_dir/inkling-constraints.txt"
cat > "$constraints" <<'EOF'
torch==2.8.0+cu128
torchvision==0.23.0+cu128
xformers==0.0.32.post2
bitsandbytes==0.50.2
peft==0.22.0
accelerate==1.16.0
torchao==0.16.0
datasets>=4.7,<5
EOF
"$python" -m pip install --no-deps --index-url https://download.pytorch.org/whl/cu128 \
  torchvision==0.23.0+cu128 xformers==0.0.32.post2
"$python" -m pip install -c "$constraints" unsloth==2026.11.12
# The upstream Inkling notebook explicitly overlays these versions on its
# resolved environment. Keep this workaround out of the project CUDA venv.
"$python" -m pip install --no-deps transformers==5.24.0 trl==1.15.0 torchao==0.16.0
"$python" -m pip install --no-deps \
  'unsloth @ git+https://github.com/unslothai/unsloth.git@7421333ab85d1542211aa20408e094ec690c93c0' \
  'unsloth-zoo @ git+https://github.com/unslothai/unsloth-zoo.git@8f55ef9b49c9da040e8869bbbe9c750ed17bfe02'
"$python" -m pip check > "$env_dir/pip-check.txt" || cat "$env_dir/pip-check.txt"
"$python" -m pip freeze > "$env_dir/requirements-resolved.txt"
"$python" -c 'from importlib.metadata import version; print({p: version(p) for p in ("unsloth","unsloth-zoo","transformers","peft","trl","bitsandbytes","torch","datasets","torchvision","xformers","torchao")})'
