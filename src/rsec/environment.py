"""Hardware diagnostics. Missing measurements remain null, never estimated as observed."""

import csv
import importlib.metadata
import io
import os
import platform
import shutil
import subprocess
import sys


def command(args):
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=15, check=True
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def memory_available():
    try:
        import psutil

        return psutil.virtual_memory().available
    except ImportError:
        try:
            from pathlib import Path

            fields = dict(
                line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines()
            )
            return int(fields["MemAvailable"].split()[0]) * 1024
        except (OSError, KeyError):
            return None


def gpu_info():
    result = {"cuda": False, "cuda_version": None, "gpus": [], "peer_access": [], "topology": None}
    try:
        import torch
    except ImportError:
        return result
    result["cuda"] = torch.cuda.is_available()
    result["cuda_version"] = torch.version.cuda
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        free, total = torch.cuda.mem_get_info(i)
        with torch.cuda.device(i):
            bf16 = torch.cuda.is_bf16_supported()
        result["gpus"].append(
            {
                "index": i,
                "name": p.name,
                "uuid": str(p.uuid) if getattr(p, "uuid", None) is not None else None,
                "total_bytes": total,
                "free_bytes": free,
                "capability": [p.major, p.minor],
                "bf16": bf16,
                "fp16": p.major >= 5,
            }
        )
    result["peer_access"] = [
        [
            torch.cuda.can_device_access_peer(i, j) if i != j else True
            for j in range(len(result["gpus"]))
        ]
        for i in range(len(result["gpus"]))
    ]
    result["topology"] = command(["nvidia-smi", "topo", "-m"])
    return result


def doctor():
    packages = {}
    for name in (
        "torch",
        "transformers",
        "peft",
        "trl",
        "accelerate",
        "bitsandbytes",
        "unsloth",
        "datasets",
        "safetensors",
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    hw = gpu_info()
    telemetry = command(
        [
            "nvidia-smi",
            "--query-gpu=index,driver_version,temperature.gpu,utilization.gpu,power.draw,memory.used",
            "--format=csv,noheader,nounits",
        ]
    )
    return {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "packages": packages,
        **hw,
        "nvidia_telemetry": list(csv.reader(io.StringIO(telemetry))) if telemetry else None,
        "ram_available_bytes": memory_available(),
        "ram_total_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        if hasattr(os, "sysconf")
        else None,
        "disk_free_bytes": shutil.disk_usage(".").free,
        "llama_cpp": shutil.which("llama-cli"),
        "ollama": shutil.which("ollama"),
        "cpu_status": "compatible",
        "training_status": "compatible_with_warnings" if hw["cuda"] else "not_compatible",
        "gpu_validation": "not_verified",
        "windows_note": "Use Linux/WSL2 for the validated training path"
        if sys.platform == "win32"
        else None,
    }
