"""Local model trust checks, before handing paths to third-party loaders."""

from pathlib import Path

from rsec.errors import RsecError
from rsec.utils import confined, digest, read_json, sha256


def verify_export(directory):
    root = Path(directory)
    manifest_path = root / "export_manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        actual = {
            str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p != manifest_path
        }
        if actual != set(manifest["files"]):
            raise RsecError("Export contains unmanifested or missing files")
        for name, entry in manifest["files"].items():
            path = confined(root, name)
            if (
                path.is_symlink()
                or sha256(path) != entry["sha256"]
                or path.stat().st_size != entry["bytes"]
            ):
                raise RsecError("Export integrity mismatch")


def local_artifacts(directory, adapter=False, fingerprint=False):
    root = Path(directory).resolve(strict=True)
    files = sorted(root.rglob("*"))
    if any(p.is_symlink() for p in files):
        raise RsecError("Symlink model artifacts are not accepted")
    if any(p.suffix in {".bin", ".pt", ".pth", ".pkl", ".pickle"} for p in files):
        raise RsecError("Only Safetensors model/adapter weights are accepted")
    if not list(root.glob("*.safetensors")):
        raise RsecError("Safetensors model/adapter weights required")
    if adapter:
        if not (root / "adapter_model.safetensors").is_file():
            raise RsecError("Local adapter_model.safetensors required")
        config = read_json(root / "adapter_config.json")
        if config.get("peft_type") != "LORA" or config.get("task_type") != "CAUSAL_LM":
            raise RsecError("Only causal language model LoRA adapters are supported")
    verify_export(root)
    return (
        digest({str(p.relative_to(root)): sha256(p) for p in files if p.is_file()})
        if fingerprint
        else None
    )
