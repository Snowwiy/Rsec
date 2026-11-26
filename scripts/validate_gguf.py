"""Reproduce CPU GGUF conversion with random tiny weights and the official tokenizer.

This is an infrastructure test, not model training or a quality benchmark.
"""

import argparse
import subprocess
from pathlib import Path

import torch
from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM

from rsec.config import load_training
from rsec.export import export
from rsec.utils import atomic_write, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llama-cpp", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    config = load_training()
    tokenizer = AutoTokenizer.from_pretrained(
        config.model,
        revision=config.revision,
        trust_remote_code=False,
        local_files_only=not args.allow_network,
    )
    torch.set_num_threads(2)
    torch.manual_seed(42)
    model = Qwen2ForCausalLM(
        Qwen2Config(
            vocab_size=len(tokenizer),
            hidden_size=256,
            intermediate_size=512,
            num_hidden_layers=1,
            num_attention_heads=4,
            num_key_value_heads=4,
            max_position_embeddings=2048,
            eos_token_id=tokenizer.eos_token_id,
            bos_token_id=tokenizer.bos_token_id,
        )
    )
    model.save_pretrained(root / "random-base")
    tokenizer.save_pretrained(root / "random-base")
    result = export(root / "random-base", root / "gguf", format="gguf", llama_cpp=args.llama_cpp)
    binary_root = Path(args.llama_cpp).resolve() / "build/bin"
    binary = next(
        (p for name in ("llama-completion", "llama-cli") if (p := binary_root / name).is_file()),
        None,
    )
    if binary is None:
        raise ValueError("Build llama-completion or llama-cli for the inference check")
    completed = subprocess.run(
        [
            str(binary),
            "-m",
            str(root / "gguf/rsec-Q4_K_M.gguf"),
            "-p",
            "Review defensive code.",
            "-n",
            "4",
            "-c",
            "128",
            "-t",
            "2",
            "--no-warmup",
            "--no-display-prompt",
            "--no-conversation",
        ],
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )
    atomic_write(root / "inference.txt", completed.stdout)
    atomic_write(root / "native-runtime.log", completed.stderr)
    write_json(
        root / "result.json",
        {
            "scope": "random tiny weights; no cybersecurity quality claim",
            "native_inference": "TESTED",
            "export": result,
        },
    )
    print(root / "result.json")


if __name__ == "__main__":
    main()
