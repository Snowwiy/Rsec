# Multi-GPU plan and physical validation protocol

All distributed training is **GPU VALIDATION PENDING**. DDP creates a full base replica on each device: the model and per-device working memory must fit each 12 GB GPU. FSDP shards parameters/optimizer states and may CPU-offload, but communication and gather peaks can dominate. Heterogeneous cards are limited by the slower participant; VRAM is not pooled as one contiguous allocation.

Launch exactly two visible devices with the checked Accelerate configs in README. Each process binds to its local rank; training never uses device_map="auto" as a distributed substitute. FSDP1 uses floating 4-bit storage matching the model loading dtype; FP16 AMP uses FP32 storage/model dtype while computation remains FP16. The single-GPU k-bit preparation upcast is skipped for FSDP. AdamW replaces paged_adamw_8bit because PEFT documents checkpoint-save errors for that FSDP-QLoRA combination. PEFT wrapping, full-state adapter gathering and CPU offload remain experimental. These paths require version/hardware validation, including optimizer checkpoint layout and reload. There is no tested guarantee for large 14B/24B/32B/MoE models.

Before launch, measure PCIe topology, peer access and free memory using doctor/nvidia-smi. The owner should compare 4070 alone, 3060 alone, DDP together and FSDP/offloading with identical immutable dataset, sequence length, effective batch, steps and seed. Use CUDA_VISIBLE_DEVICES externally for explicit selection, and verify logical rank names in the diagnostic report.

Save per-run metrics, time-to-first-step, steady-state tokens/second, peak VRAM, host RAM, power/utilization where observable, and final held-out loss. Report actual differences; no physical comparison has been performed here. Validate save/resume and adapter export on both cards. Review NCCL failures, driver mismatch, out-of-memory and gather/offload peaks before recommending a profile.

GGUF inference layer distribution uses llama.cpp bindings and tensor_split. It is a separate runtime feature, not a training strategy. Measure it independently.

The physical acceptance protocol and effective-batch matching are in [GPU_VALIDATION_PLAN.md](../GPU_VALIDATION_PLAN.md). No storage/optimizer correction here is a physical validation claim.
