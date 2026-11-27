"""Local artifact export with integrity manifests and conservative resource guards."""

import shutil
import subprocess
import sys
from pathlib import Path

from rsec.artifacts import local_artifacts
from rsec.environment import command, memory_available
from rsec.errors import RsecError
from rsec.utils import atomic_write, read_json, sha256, write_json


def inspect_tensors(directory):
    from safetensors import safe_open

    files = list(Path(directory).glob("*.safetensors"))
    if not files:
        raise RsecError("Safetensors weights required")
    for path in files:
        if path.is_symlink():
            raise RsecError("Symlink artifacts are not accepted")
        with safe_open(path, framework="pt", device="cpu") as tensors:
            if not list(tensors.keys()):
                raise RsecError("Empty tensor artifact")
    return sum(p.stat().st_size for p in files)


def resources(source, output, multiplier=3):
    size = inspect_tensors(source)
    ancestor = Path(output).parent.resolve()
    while not ancestor.exists():
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < size * multiplier:
        raise RsecError("Insufficient storage for export and intermediate artifacts")
    ram = memory_available()
    if ram is None or ram < size * multiplier:
        raise RsecError("Insufficient verified available RAM for conservative export budget")


def export(source, output, format="adapter", base=None, llama_cpp=None, quantization="Q4_K_M"):
    source, output = Path(source).resolve(strict=True), Path(output)
    if output.exists():
        raise FileExistsError("Choose a new export directory")
    if quantization not in {"Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"}:
        raise RsecError("Unsupported quantization")
    inspect_tensors(source)
    local_artifacts(source, adapter=format != "gguf")
    if format in {"merged", "safetensors"}:
        if not base:
            raise RsecError("Merged/Safetensors export requires a local unquantized base model")
        resources(base, output)
        local_artifacts(base)
    elif format == "gguf":
        resources(source, output)
        if not llama_cpp:
            raise RsecError("Specify a reviewed, locally built llama.cpp checkout")
        checkout = Path(llama_cpp).resolve(strict=True)
        if (
            not (checkout / "convert_hf_to_gguf.py").is_file()
            or not (checkout / "build/bin/llama-quantize").is_file()
        ):
            raise RsecError("llama.cpp converter/build missing")
        config = read_json(source / "config.json")
        if config["model_type"] not in {"qwen2", "llama", "mistral", "qwen3_moe"}:
            raise RsecError("Model architecture is outside the reviewed export allowlist")
    elif format != "adapter":
        raise RsecError("Unknown export format")
    output.mkdir(parents=True)
    tool_revision = None
    if format == "adapter":
        read_json(source / "adapter_config.json")
        allowed = {
            "adapter_config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "chat_template.jinja",
            "vocab.json",
            "merges.txt",
            "tokenizer.model",
            "added_tokens.json",
            "README.md",
        }
        for path in source.iterdir():
            if path.is_symlink():
                raise RsecError("Symlink artifacts are not accepted")
            if path.is_file() and (path.suffix == ".safetensors" or path.name in allowed):
                shutil.copyfile(path, output / path.name)
        if not (output / "tokenizer_config.json").exists():
            raise RsecError("Adapter export requires its tokenizer and chat template")
    elif format in {"merged", "safetensors"}:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        base_path = str(Path(base).resolve(strict=True))
        tokenizer = AutoTokenizer.from_pretrained(
            str(source), local_files_only=True, trust_remote_code=False
        )
        model = AutoModelForCausalLM.from_pretrained(
            base_path,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            dtype="auto",
        )
        merged = PeftModel.from_pretrained(
            model, str(source), local_files_only=True
        ).merge_and_unload(safe_merge=True)
        merged.save_pretrained(output, safe_serialization=True)
        tokenizer.save_pretrained(output)
    else:
        tool_revision = command(["git", "-C", str(checkout), "rev-parse", "HEAD"])
        if not tool_revision or command(["git", "-C", str(checkout), "status", "--porcelain"]):
            raise RsecError("Use a clean, versioned llama.cpp checkout")
        subprocess.run(
            [
                sys.executable,
                str(checkout / "convert_hf_to_gguf.py"),
                str(source),
                "--outfile",
                str(output / "model-f16.gguf"),
                "--outtype",
                "f16",
            ],
            check=True,
            timeout=7200,
        )
        target = output / f"rsec-{quantization}.gguf"
        subprocess.run(
            [
                str(checkout / "build/bin/llama-quantize"),
                str(output / "model-f16.gguf"),
                str(target),
                quantization,
            ],
            check=True,
            timeout=7200,
        )
        for path in output.glob("*.gguf"):
            with path.open("rb") as stream:
                if stream.read(4) != b"GGUF":
                    raise RsecError("Invalid GGUF artifact header")
        atomic_write(
            output / "Modelfile",
            f"FROM ./{target.name}\nPARAMETER num_ctx 2048\nPARAMETER temperature 0.2\n",
        )
    if format != "gguf":
        inspect_tensors(output)
    manifest = {
        "format": format,
        "source": str(source),
        "llama_cpp_revision": tool_revision,
        "integrity_validation": "TESTED",
        "runtime_validation": None,
        "runtime_validation_note": "Run inference/evaluation separately on the actual exported artifact",
        "files": {
            p.name: {"sha256": sha256(p), "bytes": p.stat().st_size}
            for p in output.iterdir()
            if p.is_file()
        },
    }
    write_json(output / "export_manifest.json", manifest)
    return {"output": str(output), **manifest}
