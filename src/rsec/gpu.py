"""Local NVIDIA diagnostics and bounded hardware-only smoke tests."""

import csv
import io
import os
import time
from pathlib import Path

from rsec.environment import command, doctor
from rsec.errors import RsecError
from rsec.utils import atomic_write, write_json

FIELDS = {
    "index": "nvidia_index",
    "uuid": "uuid",
    "name": "name",
    "pci.bus_id": "pci_bus_id",
    "driver_version": "driver",
    "memory.total": "total_mib",
    "memory.free": "free_mib",
    "memory.used": "used_mib",
    "temperature.gpu": "temperature_c",
    "power.draw": "power_w",
    "utilization.gpu": "utilization_percent",
    "pcie.link.gen.current": "pcie_generation",
    "pcie.link.width.current": "pcie_width",
    "compute_cap": "compute_capability",
}


def nvidia_devices():
    columns = ",".join(FIELDS)
    output = command(["nvidia-smi", "--query-gpu=" + columns, "--format=csv,noheader,nounits"])
    if output is None:
        return []
    return [
        {
            field: value.strip()
            if value.strip() not in {"", "N/A", "[N/A]", "[Not Supported]"}
            else None
            for field, value in zip(FIELDS.values(), row, strict=True)
        }
        for row in csv.reader(io.StringIO(output), skipinitialspace=True)
        if len(row) == len(FIELDS)
    ]


def diagnose():
    info = doctor()
    info["nvidia_devices"] = nvidia_devices()
    info["topology"] = command(["nvidia-smi", "topo", "-m"])
    info["nvidia_smi_header"] = (command(["nvidia-smi"]) or "").splitlines()[:4]
    info["nccl_available"] = None
    try:
        import torch

        info["nccl_available"] = torch.distributed.is_nccl_available()
    except (ImportError, AttributeError):
        pass
    return info


def require_cuda(index):
    import torch

    if not torch.cuda.is_available() or not 0 <= index < torch.cuda.device_count():
        raise RsecError("Selected CUDA device is unavailable. CPU fallback is disabled.")
    device = torch.device("cuda", index)
    torch.cuda.set_device(device)
    return torch, device


def benchmark(index, steps=20):
    if not 1 <= steps <= 200:
        raise RsecError("GPU benchmark steps must be in 1..200")
    torch, device = require_cuda(index)
    torch.cuda.reset_peak_memory_stats(device)
    a = torch.rand((1024, 1024), device=device)
    b = torch.rand_like(a)
    with torch.inference_mode():
        a @ b
        torch.cuda.synchronize(device)
        start = time.perf_counter()
        for _ in range(steps):
            out = a @ b
        torch.cuda.synchronize(device)
    return {
        "mode": "matmul",
        "device": str(out.device),
        "device_name": torch.cuda.get_device_name(device),
        "steps": steps,
        "seconds_per_step": (time.perf_counter() - start) / steps,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
        "status": "CUDA_MEASURED",
        "scope": "synthetic matrix operations only",
    }


def validate_single(index, output):
    torch, device = require_cuda(index)
    import bitsandbytes as bnb
    from peft import LoraConfig, get_peft_model
    from safetensors.torch import load_file

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    torch.manual_seed(923)
    torch.cuda.reset_peak_memory_stats(device)
    with torch.cuda.device(device):
        precisions = {}
        for name, dtype in (("fp16", torch.float16), ("bf16", torch.bfloat16)):
            if name == "bf16" and not torch.cuda.is_bf16_supported(including_emulation=False):
                precisions[name] = "unsupported"
                continue
            x = torch.ones((32, 32), device=device, dtype=dtype)
            y = x @ x
            if y.device != device or y.dtype != dtype or not torch.all(y == 32).item():
                raise RsecError("Precision smoke test produced an unexpected result")
            precisions[name] = "CUDA_MEASURED"

        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.proj = bnb.nn.Linear4bit(
                    64, 64, quant_type="nf4", compress_statistics=True, compute_dtype=torch.float16
                )

            def forward(self, x):
                return self.proj(x)

        base = Tiny().to(device)
        if base.proj.weight.device != device or base.proj.weight.quant_state.quant_type != "nf4":
            raise RsecError("NF4 weights did not materialize on the selected CUDA device")
        model = get_peft_model(base, LoraConfig(r=4, lora_alpha=8, target_modules=["proj"]))
        params = {n: p for n, p in model.named_parameters() if p.requires_grad}
        if not params or any("lora_" not in n or p.device != device for n, p in params.items()):
            raise RsecError("Expected CUDA-resident LoRA parameters")
        before = {n: p.detach().clone() for n, p in params.items()}
        optimizer = torch.optim.AdamW(params.values(), lr=0.01)
        sample = torch.randn((4, 64), device=device, dtype=torch.float16)
        start = time.perf_counter()

        def step(model, optimizer, sample):
            optimizer.zero_grad()
            prediction = model(sample)
            loss = prediction.float().square().mean()
            if prediction.device != device or not torch.isfinite(loss).item():
                raise RsecError("Expected finite CUDA loss")
            loss.backward()
            optimizer.step()
            torch.cuda.synchronize(device)
            return loss.item()

        first_loss = step(model, optimizer, sample)
        if not any(not torch.equal(p, before[n]) for n, p in params.items()):
            raise RsecError("Optimizer did not update LoRA parameters")
        elapsed = time.perf_counter() - start
        start = time.perf_counter()
        from safetensors.torch import save_file

        save_file(
            {n: p.detach().cpu().contiguous() for n, p in params.items()},
            str(output / "adapter.safetensors"),
        )
        torch.save(optimizer.state_dict(), output / "optimizer.pt")
        save_seconds = time.perf_counter() - start
        start = time.perf_counter()
        with torch.no_grad():
            expected = model(sample).detach().clone()
            for p in params.values():
                p.zero_()
            restored = load_file(str(output / "adapter.safetensors"))
            for name, p in params.items():
                p.copy_(restored[name])
            if not torch.equal(model(sample), expected):
                raise RsecError("Reloaded adapter did not reproduce inference")
        optimizer = torch.optim.AdamW(params.values(), lr=0.01)
        optimizer.load_state_dict(
            torch.load(output / "optimizer.pt", map_location=device, weights_only=True)
        )
        resume_seconds = time.perf_counter() - start
        resumed_loss = step(model, optimizer, sample)
        if not all(state["step"].item() == 2 for state in optimizer.state.values()):
            raise RsecError("Optimizer step did not resume")
        peak = torch.cuda.max_memory_allocated(device)
        del model, base, params, optimizer, before, sample, expected, x, y, p
        torch.cuda.empty_cache()
        free, total = torch.cuda.mem_get_info(device)
    report = {
        "mode": "single",
        "status": "CUDA_MEASURED",
        "scope": "tiny synthetic NF4 linear layer",
        "cuda_device": index,
        "device_name": torch.cuda.get_device_name(device),
        "precisions": precisions,
        "nf4": True,
        "first_loss": first_loss,
        "resumed_loss": resumed_loss,
        "checkpoint_step": 2,
        "step_seconds": elapsed,
        "checkpoint_seconds": save_seconds,
        "restore_seconds": resume_seconds,
        "peak_allocated_bytes": peak,
        "free_after_bytes": free,
        "total_bytes": total,
    }
    write_json(output / "validation.json", report)
    return report


def validate_ddp(output):
    rank = int(os.environ.get("LOCAL_RANK", "-1"))
    world = int(os.environ.get("WORLD_SIZE", "0"))
    if world != 2 or rank not in {0, 1}:
        raise RsecError(
            "Launch two explicitly selected GPUs with torchrun --standalone --nproc-per-node=2"
        )
    torch, device = require_cuda(rank)
    if not torch.distributed.is_nccl_available():
        raise RsecError("NCCL is unavailable in this environment")
    from datetime import timedelta

    dist = torch.distributed
    dist.init_process_group("nccl", timeout=timedelta(seconds=45), device_id=device)
    try:
        model = torch.nn.parallel.DistributedDataParallel(
            torch.nn.Linear(32, 32).to(device), device_ids=[rank]
        )
        before = model.module.weight.detach().clone()
        opt = torch.optim.SGD(model.parameters(), lr=0.01)
        x = torch.ones((8, 32), device=device) * (rank + 1)
        torch.cuda.reset_peak_memory_stats(device)
        dist.barrier()
        start = time.perf_counter()
        opt.zero_grad()
        model(x).float().square().mean().backward()
        opt.step()
        torch.cuda.synchronize(device)
        elapsed = time.perf_counter() - start
        weights = [torch.empty_like(before) for _ in range(world)]
        dist.all_gather(weights, model.module.weight.detach())
        if torch.equal(before, model.module.weight) or not torch.equal(weights[0], weights[1]):
            raise RsecError("DDP updates did not synchronize")
        measured = torch.tensor(
            [elapsed, float(torch.cuda.max_memory_allocated(device))],
            device=device,
            dtype=torch.float64,
        )
        outputs = [torch.empty_like(measured) for _ in range(world)]
        dist.all_gather(outputs, measured)
        report = {
            "mode": "ddp",
            "status": "CUDA_MEASURED",
            "world_size": world,
            "per_rank_step_seconds_and_peak_bytes": [m.tolist() for m in outputs],
            "scope": "tiny dense DDP synchronization only",
        }
        if rank == 0:
            write_json(output, report)
        return report
    finally:
        dist.destroy_process_group()


def write_diagnostic(json_path, markdown_path=None):
    info = diagnose()
    if json_path:
        write_json(json_path, info)
    if markdown_path:
        devices = (
            "\n".join(
                f"- {g['name']} · {g['uuid']} · {g['free_mib']} MiB libres · PCIe {g['pcie_generation']} ×{g['pcie_width']}"
                for g in info["nvidia_devices"]
            )
            or "Sin telemetría NVIDIA disponible."
        )
        atomic_write(
            markdown_path,
            f"# Rsec hardware\n\n{devices}\n\n- CUDA de PyTorch: {info['cuda_version']}\n- NCCL disponible: {info['nccl_available']}\n- RAM libre: {info['ram_available_bytes']} bytes\n- Disco libre: {info['disk_free_bytes']} bytes\n- Validación física: pendiente de pruebas.\n",
        )
    return info
