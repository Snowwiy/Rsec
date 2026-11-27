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

METRICS = ("uuid", "temperature.gpu", "memory.used", "utilization.gpu", "clocks.sm", "power.draw")


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


def supervise(uuids, directory, warn=80, stop=85):
    if len(uuids) not in (1, 2) or len(set(uuids)) != len(uuids) or not 0 < warn < stop <= 85:
        raise ValueError("Select distinct devices and conservative thermal thresholds")
    if len(uuids) == 2 and os.name != "posix":
        raise ValueError("Use WSL2/Linux for NCCL")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    proc = None
    started = time.monotonic()
    samples = []
    status = "interrupted"
    try:
        while True:
            rows = sample(uuids)
            hottest = max(row["temperature.gpu"] for row in rows.values())
            samples.append(
                {"elapsed": time.monotonic() - started, "devices": rows, "warning": hottest >= warn}
            )
            if hottest >= stop or time.monotonic() - started > 180:
                raise RuntimeError("Thermal or time limit reached")
            if hottest >= warn and (len(samples) == 1 or not samples[-2]["warning"]):
                print("GPU temperature warning", file=sys.stderr, flush=True)
            if proc is None:
                module = ["rsec.cli", "gpu", "validate", "--output", str(directory / "single")]
                if len(uuids) == 2:
                    module = [
                        "torch.distributed.run",
                        "--standalone",
                        "--nproc-per-node=2",
                        "--module",
                        "rsec.cli",
                        "gpu",
                        "validate",
                        "--mode",
                        "ddp",
                        "--output",
                        str(directory / "ddp.json"),
                    ]
                proc = subprocess.Popen(
                    [sys.executable, "-m", *module],
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
    p.add_argument("--warn", type=float, default=80)
    p.add_argument("--stop", type=float, default=85)
    a = p.parse_args()
    supervise(a.uuid, a.output, a.warn, a.stop)


if __name__ == "__main__":
    main()
