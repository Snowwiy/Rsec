"""Physical FSDP1/NF4 validation with an offline synthetic linear fixture."""

import json
import time
from pathlib import Path

from rsec.errors import RsecError
from rsec.gpu_distributed import nccl_worker
from rsec.utils import sha256, write_json


def validate_fsdp(output):
    from resource import RUSAGE_SELF, getrusage

    import bitsandbytes as bnb
    from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
    from peft.utils.other import fsdp_auto_wrap_policy
    from safetensors.torch import load_file, save_file
    from torch.distributed.checkpoint import load as load_shards
    from torch.distributed.checkpoint import save as save_shards
    from torch.distributed.checkpoint.state_dict import get_state_dict, set_state_dict
    from torch.distributed.fsdp import (
        FullOptimStateDictConfig,
        FullStateDictConfig,
        StateDictType,
    )
    from torch.distributed.fsdp import (
        FullyShardedDataParallel as FSDP,
    )

    output = Path(output)
    with nccl_worker() as (torch, device, dist, rank):
        dtype = torch.bfloat16
        torch.manual_seed(923)

        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.proj = bnb.nn.Linear4bit(
                    64,
                    64,
                    bias=False,
                    quant_type="nf4",
                    compress_statistics=True,
                    compute_dtype=dtype,
                    quant_storage=dtype,
                )

            def forward(self, inputs):
                return self.proj(inputs)

        def create_model():
            torch.manual_seed(923)
            raw = Tiny().to(dtype=dtype).to(device)
            weight = raw.proj.weight
            if (
                weight.dtype != dtype
                or weight.quant_state.quant_type != "nf4"
                or not weight.quant_state.nested
            ):
                raise RsecError("Expected BF16-packed NF4 with compressed statistics")
            model = get_peft_model(
                raw,
                LoraConfig(r=4, lora_alpha=8, target_modules=["proj"]),
                autocast_adapter_dtype=False,
            )
            full_size = sum(p.numel() for p in model.parameters())
            wrapped = FSDP(
                model,
                device_id=device,
                use_orig_params=False,
                auto_wrap_policy=fsdp_auto_wrap_policy(model),
            )
            shard_size = sum(p.numel() for p in wrapped.parameters())
            if not 0 < shard_size < full_size:
                raise RsecError("FSDP did not reduce the local parameter storage")
            return model, wrapped, full_size, shard_size

        generator = torch.Generator(device=device).manual_seed(923 + rank)
        inputs = torch.randn((4, 64), generator=generator, device=device, dtype=dtype)

        def step(model, optimizer):
            optimizer.zero_grad(set_to_none=True)
            value = model(inputs)
            if value.device != device:
                raise RsecError("FSDP fixture did not execute on CUDA")
            loss = value.float().square().mean()
            loss.backward()
            optimizer.step()
            return loss

        peft_model, model, full_size, shard_size = create_model()
        optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=0.01)
        before = [p.detach().clone() for p in model.parameters() if p.requires_grad]
        for _ in range(2):
            step(model, optimizer)
        torch.cuda.reset_peak_memory_stats(device)
        dist.barrier()
        torch.cuda.synchronize(device)
        start = time.perf_counter()
        for _ in range(8):
            loss = step(model, optimizer)
        torch.cuda.synchronize(device)
        elapsed = time.perf_counter() - start
        updated = [p for p in model.parameters() if p.requires_grad]
        if not torch.isfinite(loss).item() or not any(
            not torch.equal(a, b) for a, b in zip(before, updated, strict=True)
        ):
            raise RsecError("FSDP LoRA parameters did not update with finite loss")
        with torch.no_grad():
            expected = model(inputs).detach()
        peak = torch.cuda.max_memory_allocated(device)
        weights = output.with_suffix(".pt")
        adapter = output.with_suffix(".safetensors")
        manifest = output.with_suffix(".sha256.json")
        full = FullStateDictConfig(offload_to_cpu=False, rank0_only=False)
        full_opt = FullOptimStateDictConfig(offload_to_cpu=False, rank0_only=False)
        start = time.perf_counter()
        with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT, full, full_opt):
            state = model.state_dict()
            optimizer_state = FSDP.optim_state_dict(model, optimizer)
            if rank == 0:
                with weights.open("xb") as handle:
                    torch.save({"model": state, "optimizer": optimizer_state}, handle)
                exported = get_peft_model_state_dict(peft_model, state_dict=state)
                if not exported:
                    raise RsecError("FSDP adapter export was empty")
                save_file(
                    {k: v.detach().cpu().contiguous() for k, v in exported.items()}, str(adapter)
                )
                write_json(manifest, {"weights": sha256(weights), "adapter": sha256(adapter)})
        dist.barrier()
        save_seconds = time.perf_counter() - start
        start = time.perf_counter()
        expected_hashes = json.loads(manifest.read_text(encoding="utf-8"))
        if expected_hashes != {
            "weights": sha256(weights),
            "adapter": sha256(adapter),
        } or not load_file(str(adapter)):
            raise RsecError("FSDP checkpoint or adapter failed integrity verification")
        state = torch.load(weights, map_location=device, weights_only=True)
        _, restored, _, _ = create_model()
        restored_opt = torch.optim.AdamW(
            (p for p in restored.parameters() if p.requires_grad), lr=0.01
        )
        with FSDP.state_dict_type(restored, StateDictType.FULL_STATE_DICT, full, full_opt):
            restored.load_state_dict(state["model"])
            restored_opt.load_state_dict(
                FSDP.optim_state_dict_to_load(restored, restored_opt, state["optimizer"])
            )
        with torch.no_grad():
            if not torch.equal(restored(inputs), expected):
                raise RsecError("Restored FSDP checkpoint did not reproduce CUDA inference")
        restore_seconds = time.perf_counter() - start
        step(restored, restored_opt)
        if not all(s["step"].item() == 11 for s in restored_opt.state.values()):
            raise RsecError("FSDP optimizer did not resume at the expected step")
        with torch.no_grad():
            expected_shards = restored(inputs).detach()
        shards = output.with_name(output.stem + "-shards")
        start = time.perf_counter()
        model_shards, optimizer_shards = get_state_dict(restored, restored_opt)
        save_shards({"model": model_shards, "optimizer": optimizer_shards}, checkpoint_id=shards)
        if rank == 0:
            payload_files = sorted(shards.glob("*.distcp"))
            if len(payload_files) != 2:
                raise RsecError("Expected two rank payloads in the distributed checkpoint")
            write_json(
                shards / "sha256.json",
                {path.name: sha256(path) for path in [*payload_files, shards / ".metadata"]},
            )
        dist.barrier()
        shard_save_seconds = time.perf_counter() - start
        start = time.perf_counter()
        hashes = json.loads((shards / "sha256.json").read_text(encoding="utf-8"))
        if any(sha256(shards / name) != value for name, value in hashes.items()):
            raise RsecError("Rank checkpoint failed SHA-256 verification")
        with torch.no_grad():
            for parameter in restored.parameters():
                if parameter.requires_grad:
                    parameter.zero_()
        model_shards, optimizer_shards = get_state_dict(restored, restored_opt)
        payload = {"model": model_shards, "optimizer": optimizer_shards}
        load_shards(payload, checkpoint_id=shards)
        set_state_dict(
            restored,
            restored_opt,
            model_state_dict=payload["model"],
            optim_state_dict=payload["optimizer"],
        )
        with torch.no_grad():
            if not torch.equal(restored(inputs), expected_shards):
                raise RsecError("Rank checkpoint did not reproduce CUDA inference")
        shard_restore_seconds = time.perf_counter() - start
        row = {
            "device": torch.cuda.get_device_name(device),
            "full_packed_elements": full_size,
            "local_shard_elements": shard_size,
            "step_seconds": elapsed / 8,
            "fixture_rows_per_second": 32 / elapsed,
            "peak_allocated_bytes": peak,
            "peak_rss_bytes": getrusage(RUSAGE_SELF).ru_maxrss * 1024,
            "checkpoint_seconds": save_seconds,
            "restore_seconds": restore_seconds,
            "shard_checkpoint_seconds": shard_save_seconds,
            "shard_restore_seconds": shard_restore_seconds,
        }
        rows = [None, None]
        dist.all_gather_object(rows, row)
        if rank == 0:
            write_json(
                output,
                {
                    "status": "CUDA_MEASURED",
                    "backend": "nccl",
                    "mode": "fsdp1",
                    "storage": "bf16",
                    "quantization": "nf4-double",
                    "checkpoint_step": 11,
                    "rank_checkpoint_files": 2,
                    "ranks": rows,
                },
            )
