"""Exercise the two historical public-checksum exceptions using a disposable repository."""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", type=Path, help="Path to the pinned gitleaks binary")
    args = parser.parse_args()
    scanner = args.scanner.resolve(strict=True)
    config = Path(".gitleaks.toml").resolve(strict=True)
    entries = dict(
        re.findall(r'(tokenizer(?:_config)?\\\.json)": "([0-9a-f]{64})"', config.read_text())
    )
    if len(entries) != 2:
        raise SystemExit("Expected two vetted tokenizer checksums")
    positive = {name.replace("\\.", "."): value for name, value in entries.items()}
    paths = ["data/manifests/pilot_statistics.json", "data/manifests/benchmark_statistics.json"]
    # Deterministic synthetic negative control. It is never printed or recorded in Git history.
    unexpected = __import__("hashlib").sha256(b"rsec scanner negative control").hexdigest()
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        subprocess.run(["git", "init", "-q", workspace], check=True)

        def write(path, data):
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(data), encoding="utf-8")

        def scan():
            subprocess.run(["git", "-C", workspace, "add", "."], check=True)
            output = root.parent / (root.name + "-redacted.json")
            cmd = [
                str(scanner),
                "git",
                workspace,
                "--config",
                str(config),
                "--pre-commit",
                "--staged",
                "--redact",
                "--report-format",
                "json",
                "--report-path",
                str(output),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            try:
                return result.returncode, {
                    finding["File"] for finding in json.loads(output.read_text())
                }
            finally:
                output.unlink(missing_ok=True)

        for path in paths:
            write(path, positive)
        if scan() != (0, set()):
            raise SystemExit("Reviewed public tokenizer checksums must pass")
        other = "data/manifests/unrelated.json"
        write(paths[0], {"tokenizer.json": unexpected})
        write(other, positive)
        if scan() != (1, {paths[0], other}):
            raise SystemExit("An unexpected value or path escaped detection")
    print("Gitleaks public checksum and negative controls passed")


if __name__ == "__main__":
    main()
