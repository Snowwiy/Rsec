# Training guide

The validated path is Linux/Python 3.12 **CPU tiny SFT**, not CUDA training. Start with README installation and `rsec doctor`; record the JSON report with each experiment. Install PyTorch 2.8.0 for the actual CUDA/driver combination using https://pytorch.org/get-started/locally/ before installing requirements-train.txt. Common/data/dev requirements never depend on a CUDA wheel.

Candidate training dependencies are pinned at direct-version level; the fully frozen CPU stack is requirements-cpu-test.lock. A GPU run must establish its own compatible transitive lock after physical validation. Audit it, record driver/CUDA/GPU data, run a short smoke job and measure peak allocation before increasing sequence length or model size. Do not blindly install CPU wheels from the CPU-test lock on a GPU machine.

The reference model revision is immutable. The official tokenizer template supplies role/EOS semantics. Prompt-completion mode trains only the final assistant response. Assistant-only mode is opt-in and requires generation markers in the template; unsupported templates fail. Padding is right-sided for SFT, and examples exceeding the configured context fail for manual curation. No arbitrary ChatML replacement is applied.

A run gets a unique experiment directory, config/data/code hashes, hardware snapshot, local metrics and checkpoints containing optimizer/scheduler/RNG state. Checkpoint manifests verify content before resume. Own trusted checkpoints only: a matching manifest is not a cryptographic publisher signature. Resume rejects changed core training config or data. `--max-steps` can extend a run in a new experiment directory. Loading `--adapter` creates a new optimizer and must be accompanied by reviewed replay data and regression evaluation.

Optional early stopping requires equal evaluation/save cadence. Existing checkpoints are not pruned. Ctrl+C requests a save after the current optimizer step, which can take time. Hard process termination/OOM cannot guarantee an additional checkpoint; previous checkpoints remain. Experiment failures record exception type without source text or credentials.

## Windows and WSL2

Run scripts/setup_windows.ps1 for compatible CPU tools. Use Microsoft-supported WSL2 with a Linux distribution and an NVIDIA Windows driver supporting WSL CUDA. Inside WSL, verify `nvidia-smi`, then run scripts/setup_wsl.sh. Do not claim native Windows support for the GPU candidate stack. Keep the Linux venv separate from Windows Python.

## Colab / Kaggle

The notebooks clone an immutable code commit, inspect the actual device, install core and pinned candidate dependencies, prepare synthetic smoke data and provide explicit flags for training/resume/evaluation/export. Enable a GPU in the provider UI; availability is not guaranteed. Colab T4 uses FP16, not BF16. Kaggle defaults to one visible GPU; multi-device training needs explicit launcher configuration.

Notebook model downloads and GPU runs are opt-in. Optional Drive mounting persists artifacts in Colab after explicit selection. Kaggle /kaggle/working is the artifact output location; save a notebook version with outputs through the provider UI. Download checkpoints before a session expires. No notebook credentials are stored.

## RunPod and other Linux GPU machines

Provisioning/billing is a separate owner action. This repository never creates paid instances. On an already authorized machine, clone an immutable commit, create a fresh environment, verify driver/torch compatibility, install requirements-train.txt and run `rsec doctor`. Select runpod/nvidia_24gb/nvidia_48gb conservatively; these are starting points, not memory guarantees. Use a persistent volume for experiments/checkpoints and a separate export machine when RAM/storage is insufficient.

## Unsloth

BLOCKED in the audited stack. Wheel 2026.11.12 requires Transformers <=5.17.0, TRL <=1.15.0 and datasets <5.0.0, conflicting with Rsec pins 5.24.1 / 1.19.0 / 5.0.1. The backend now fails before import and the conflicting requirement is commented out. Do not force --no-deps or downgrade the audited stack. Separate integration is future work. See GPU_VALIDATION_PLAN.md and SECURITY_AUDIT.md at repository root.
