"""Bounded CUDA collectives and comparable, synthetic training workloads."""

import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from rsec.errors import RsecError
from rsec.gpu import require_cuda
from rsec.utils import sha256, write_json


def local_rank():
    rank = os.environ.get("LOCAL_RANK")
    if os.environ.get("WORLD_SIZE") != "2" or rank not in ("0", "1"):
        raise RsecError("Launch with two explicitly selected CUDA devices")
    return int(rank)


@contextmanager
def nccl_worker():
    rank = local_rank()
    torch, device = require_cuda(rank)
    dist = torch.distributed
    if not dist.is_nccl_available():
        raise RsecError("NCCL is unavailable in this environment")
    try:
        dist.init_process_group("nccl", timeout=timedelta(seconds=35), device_id=device)
        yield torch, device, dist, rank
    finally:
        if dist.is_initialized():
            dist.destroy_process_group()


def validate_nccl(output):
    with nccl_worker() as (torch, device, dist, rank):
        props = torch.cuda.get_device_properties(device)
        expected_uuid = os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",")[rank]
        if (
            str(props.uuid).removeprefix("GPU-").lower()
            != expected_uuid.removeprefix("GPU-").lower()
        ):
            raise RsecError("CUDA device UUID differs from the selected physical device")
        vector = torch.full((1024,), rank + 1, device=device, dtype=torch.float32)
        start = time.perf_counter()
        dist.all_reduce(vector)
        if not torch.all(vector == 3).item():
            raise RsecError("NCCL all-reduce integrity failure")
        collective_seconds = time.perf_counter() - start
        vector.fill_(7 if rank == 0 else 0)
        dist.broadcast(vector, src=0)
        if not torch.all(vector == 7).item():
            raise RsecError("NCCL broadcast integrity failure")
        if rank == 0:
            dist.send(vector, dst=1)
        else:
            vector.zero_()
            dist.recv(vector, src=0)
            if not torch.all(vector == 7).item():
                raise RsecError("NCCL transfer integrity failure")
        timings = {}
        for size in (1024, 1024 * 1024):
            probe = torch.full((size,), 1.0, device=device)
            dist.barrier()
            torch.cuda.synchronize(device)
            start = time.perf_counter()
            for _ in range(8):
                dist.all_reduce(probe)
            torch.cuda.synchronize(device)
            timings[str(size * probe.element_size())] = (time.perf_counter() - start) / 8
            if not torch.all(probe == 256).item():
                raise RsecError("NCCL warmed collective integrity failure")
        row = {
            "device": props.name,
            "uuid": str(props.uuid),
            "capability": [props.major, props.minor],
            "free_bytes": torch.cuda.mem_get_info(device)[0],
            "native_bf16": torch.cuda.is_bf16_supported(including_emulation=False),
            "peer_access": torch.cuda.can_device_access_peer(rank, 1 - rank),
            "all_reduce_seconds": collective_seconds,
            "warm_all_reduce_seconds_by_payload_bytes": timings,
        }
        rows = [None, None]
        dist.all_gather_object(rows, row)
        dist.barrier()
        if rank == 0:
            write_json(
                output,
                {
                    "status": "CUDA_MEASURED",
                    "backend": dist.get_backend(),
                    "version": list(torch.cuda.nccl.version()),
                    "payload_bytes": 4096,
                    "p2p_disabled": os.environ.get("NCCL_P2P_DISABLE") == "1",
                    "ranks": rows,
                },
            )


def run_dense(torch, device, output, *, rank=0, dist=None):
    """Compare synthetic token positions at the same global batch and sequence length."""
    import psutil

    output = Path(output)
    if dist is None:
        output.parent.mkdir(parents=True, exist_ok=True)
    steps, warmup, batch, context, vocab = 64, 8, 8, 128, 1024
    torch.manual_seed(923)
    generator = torch.Generator().manual_seed(923)
    ids = torch.randint(vocab, (batch, context), generator=generator).to(device)
    if dist is not None:
        ids = ids.chunk(2)[rank]
    targets = (ids + 1) % vocab

    def create_model():
        module = torch.nn.Sequential(
            torch.nn.Embedding(vocab, 256), torch.nn.Linear(256, vocab)
        ).to(device)
        if dist is None:
            return module, module
        wrapper = torch.nn.parallel.DistributedDataParallel(module, device_ids=[device.index])
        return module, wrapper

    def step(model, optimizer):
        optimizer.zero_grad(set_to_none=True)
        loss = torch.nn.functional.cross_entropy(model(ids).flatten(0, 1), targets.flatten())
        loss.backward()
        optimizer.step()
        return loss

    raw, model = create_model()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.005)
    before = raw[1].weight.detach().clone()
    for _ in range(warmup):
        step(model, optimizer)
    torch.cuda.reset_peak_memory_stats(device)
    if dist is not None:
        dist.barrier()
    torch.cuda.synchronize(device)
    start = time.perf_counter()
    for _ in range(steps):
        loss = step(model, optimizer)
    torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - start
    expected = model(ids).detach()
    if not torch.isfinite(loss).item() or torch.equal(before, raw[1].weight):
        raise RsecError("Synthetic parameters did not update with a finite CUDA loss")
    sync_seconds = None
    if dist is not None:
        start = time.perf_counter()
        dist.barrier(device_ids=[device.index])
        sync_seconds = time.perf_counter() - start
    peak = torch.cuda.max_memory_allocated(device)
    checkpoint = output.with_suffix(".pt")
    manifest = output.with_suffix(".sha256.json")
    start = time.perf_counter()
    if rank == 0 or dist is None:
        if checkpoint.exists():
            raise RsecError("Checkpoint already exists")
        with checkpoint.open("xb") as handle:
            torch.save({"model": raw.state_dict(), "optimizer": optimizer.state_dict()}, handle)
        write_json(manifest, {"sha256": sha256(checkpoint)})
    if dist is not None:
        dist.barrier()
    save_seconds = time.perf_counter() - start
    start = time.perf_counter()
    if json.loads(manifest.read_text(encoding="utf-8"))["sha256"] != sha256(checkpoint):
        raise RsecError("Synthetic checkpoint failed SHA-256 verification")
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    restored_raw, restored = create_model()
    restored_raw.load_state_dict(state["model"])
    restarted_opt = torch.optim.AdamW(restored.parameters(), lr=0.005)
    restarted_opt.load_state_dict(state["optimizer"])
    if not torch.equal(restored(ids).detach(), expected):
        raise RsecError("Restored checkpoint did not reproduce CUDA inference")
    restore_seconds = time.perf_counter() - start
    step(restored, restarted_opt)
    if not all(x["step"].item() == warmup + steps + 1 for x in restarted_opt.state.values()):
        raise RsecError("Optimizer step did not resume")
    if dist is not None:
        weights = torch.cat([p.detach().flatten() for p in restored_raw.parameters()])
        copies = [torch.empty_like(weights) for _ in range(2)]
        dist.all_gather(copies, weights)
        if not torch.equal(copies[0], copies[1]):
            raise RsecError("DDP parameters diverged after restoring the checkpoint")
    row = {
        "device": torch.cuda.get_device_name(device),
        "seconds": elapsed,
        "step_seconds": elapsed / steps,
        "peak_allocated_bytes": peak,
        "checkpoint_seconds": save_seconds,
        "restore_seconds": restore_seconds,
        "barrier_seconds": sync_seconds,
        "rss_bytes": psutil.Process().memory_info().rss,
    }
    if sys.platform == "linux":
        import resource

        row["peak_rss_bytes"] = max(
            row["rss_bytes"], resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        )
    rows = [row]
    if dist is not None:
        rows = [None, None]
        dist.all_gather_object(rows, row)
    report = {
        "mode": "ddp" if dist is not None else "single",
        "status": "CUDA_MEASURED",
        "global_batch": batch,
        "context": context,
        "steps": steps,
        "precision": "fp32",
        "seed": 923,
        "synthetic_tokens": steps * batch * context,
        "tokens_per_second": steps * batch * context / max(x["seconds"] for x in rows),
        "ranks": rows,
    }
    if rank == 0 or dist is None:
        write_json(output, report)
    return report


def validate_ddp(output):
    with nccl_worker() as (torch, device, dist, rank):
        return run_dense(torch, device, output, rank=rank, dist=dist)


def validate_comparison(index, output, *, independent=False):
    if independent:
        index = local_rank()
        output = Path(output).with_suffix(f".rank-{index}.json")
    torch, device = require_cuda(index)
    return run_dense(torch, device, output)
