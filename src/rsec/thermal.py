"""Run only the tiny CUDA validations with selected-device thermal supervision."""

import argparse
import csv
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from rsec.utils import write_json

METRICS = (
    "uuid",
    "temperature.gpu",
    "memory.used",
    "utilization.gpu",
    "clocks.sm",
    "power.draw",
    "enforced.power.limit",
    "fan.speed",
    "pcie.link.gen.current",
    "pcie.link.width.current",
    "clocks_event_reasons.hw_thermal_slowdown",
    "clocks_event_reasons.sw_thermal_slowdown",
)
THERMAL_FLAGS = METRICS[-2:]


def sample(uuids):
    run = subprocess.run(
        ["nvidia-smi", "--query-gpu=" + ",".join(METRICS), "--format=csv,noheader,nounits"],
        text=True,
        capture_output=True,
        timeout=4,
        check=True,
    )
    rows = {}
    for row in csv.reader(run.stdout.splitlines(), skipinitialspace=True):
        if row and row[0] in uuids:
            values = dict(zip(METRICS, row, strict=True))
            temp = float(values["temperature.gpu"])
            if not math.isfinite(temp) or not 0 < temp < 150:
                raise ValueError("Invalid thermal sensor")
            values["temperature.gpu"] = temp
            rows[row[0]] = values
    if len(rows) != len(uuids):
        raise ValueError("Selected GPU is unavailable or thermal telemetry is incomplete")
    return rows


def supervise(uuids, directory, warn=80, stop=85, *, mode=None, watch=None):
    if len(uuids) not in (1, 2) or len(set(uuids)) != len(uuids) or not 0 < warn < stop <= 85:
        raise ValueError("Select distinct devices and conservative thermal thresholds")
    if len(uuids) == 2 and os.name != "posix":
        raise ValueError("Use WSL2/Linux for NCCL")
    directory = Path(directory)
    mode = mode or ("ddp" if len(uuids) == 2 else "single")
    single_modes = {"single", "compare"}
    dual_modes = {"nccl", "ddp", "fsdp", "independent"}
    if mode not in (single_modes if len(uuids) == 1 else dual_modes):
        raise ValueError("Validation mode does not match the selected GPU count")
    module = ["rsec.cli", "gpu", "validate", "--output", str(directory / "single")]
    if mode == "compare":
        module = [
            "rsec.cli",
            "gpu",
            "validate",
            "--mode",
            mode,
            "--output",
            str(directory / "compare.json"),
        ]
    elif mode in dual_modes:
        module = [
            "torch.distributed.run",
            "--standalone",
            "--nproc-per-node=2",
            "--module",
            "rsec.cli",
            "gpu",
            "validate",
            "--mode",
            mode,
            "--output",
            str(directory / f"{mode}.json"),
        ]
    return supervise_process(
        uuids, directory, [sys.executable, "-m", *module], warn=warn, stop=stop, watch=watch
    )


def supervise_process(uuids, directory, argv, *, warn=80, stop=85, watch=None, timeout=180):
    """Limit the worker's visible devices and abort on telemetry loss or overheating."""
    watched = list(dict.fromkeys([*uuids, *(watch or [])]))
    if (
        not uuids
        or len(set(uuids)) != len(uuids)
        or not 0 < warn < stop <= 85
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("Select distinct devices, a deadline and conservative thermal thresholds")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    proc = None
    started = time.monotonic()
    samples = []
    status = "interrupted"
    try:
        while True:
            rows = sample(watched)
            hottest = max(row["temperature.gpu"] for row in rows.values())
            samples.append(
                {"elapsed": time.monotonic() - started, "devices": rows, "warning": hottest >= warn}
            )
            if any(
                str(row.get(flag, "")).casefold() in {"active", "yes"}
                for row in rows.values()
                for flag in THERMAL_FLAGS
            ):
                raise RuntimeError("GPU thermal throttling detected")
            if hottest >= stop or time.monotonic() - started > timeout:
                raise RuntimeError("Thermal or time limit reached")
            if hottest >= warn and (len(samples) == 1 or not samples[-2]["warning"]):
                print("GPU temperature warning", file=sys.stderr, flush=True)
            if proc is None:
                proc = subprocess.Popen(
                    argv,
                    env={**os.environ, "CUDA_VISIBLE_DEVICES": ",".join(uuids)},
                    start_new_session=os.name == "posix",
                )
            elif proc.poll() is not None:
                if proc.returncode:
                    raise RuntimeError(f"CUDA validation exited with {proc.returncode}")
                status = "completed"
                return
            time.sleep(1)
    finally:
        if proc is not None and proc.poll() is None:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait()
        write_json(
            directory / "thermal.json",
            {"status": status, "warning_c": warn, "stop_c": stop, "samples": samples},
        )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--uuid", action="append", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mode", choices=("single", "nccl", "ddp", "fsdp", "compare", "independent"))
    p.add_argument("--watch-uuid", action="append")
    p.add_argument("--warn", type=float, default=80)
    p.add_argument("--stop", type=float, default=85)
    a = p.parse_args()
    supervise(a.uuid, a.output, a.warn, a.stop, mode=a.mode, watch=a.watch_uuid)


if __name__ == "__main__":
    main()
