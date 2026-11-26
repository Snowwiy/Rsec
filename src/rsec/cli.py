"""Central CLI; optional stacks are imported only by their respective commands."""

import argparse
import json
import subprocess
import sys

from rsec import __version__
from rsec.errors import RsecError


def parser():
    p = argparse.ArgumentParser(prog="rsec", description="Rsec defensive AI research foundation")
    p.add_argument("--version", action="version", version=__version__)
    commands = p.add_subparsers(dest="command", required=True)
    doc = commands.add_parser("doctor", help="Inspect CPU/GPU/tool availability")
    doc.add_argument("--output")
    cfg = commands.add_parser("config", help="Validate training configuration")
    cfg.add_argument("--config", default="configs/qlora_cybersec.yaml")
    cfg.add_argument("--profile")
    data = commands.add_parser("data", help="Acquire, curate and verify datasets")
    ds = data.add_subparsers(dest="action", required=True)
    download = ds.add_parser("download", help="Acquire explicitly reviewed sources")
    download.add_argument("--config", default="configs/datasets.yaml")
    download.add_argument("--output", default="data/raw")
    hf = ds.add_parser("download-hf", help="Acquire a licensed, pinned HF dataset")
    hf.add_argument("dataset_id")
    hf.add_argument("--revision", required=True)
    hf.add_argument("--license", required=True)
    hf.add_argument("--reviewed", action="store_true", required=True)
    hf.add_argument("--split", default="train")
    hf.add_argument("--output", required=True)
    ing = ds.add_parser(
        "ingest", help="Curate knowledge/RAG documents without creating SFT examples"
    )
    ing.add_argument("--input", nargs="+", required=True)
    ing.add_argument("--output", required=True)
    for field in ("source", "source-url", "license", "version", "redistribution"):
        ing.add_argument("--" + field, required=True)
    ing.add_argument("--reviewed", action="store_true", required=True)
    ing.add_argument("--purpose", choices=["knowledge", "rag"], default="knowledge")
    ing.add_argument("--anonymize", action="store_true")
    prep = ds.add_parser("prepare", help="Release train/eval/test splits")
    prep.add_argument("--input", nargs="+", required=True)
    prep.add_argument("--replay", nargs="*", default=[])
    prep.add_argument("--output", required=True)
    prep.add_argument("--seed", type=int, default=42)
    prep.add_argument("--benchmarks", nargs="*", default=["benchmarks/suite.jsonl"])
    prep.add_argument("--anonymize", action="store_true")
    prep.add_argument("--category-cap", type=int)
    val = ds.add_parser("validate", help="Check release hashes, schemas and leakage")
    val.add_argument("directory")
    tr = commands.add_parser("train", help="Run real SFT/QLoRA or tiny CPU smoke training")
    tr.add_argument("--config", default="configs/qlora_cybersec.yaml")
    tr.add_argument("--profile")
    tr.add_argument("--smoke", action="store_true")
    tr.add_argument("--resume")
    tr.add_argument("--adapter")
    tr.add_argument("--output")
    tr.add_argument("--max-steps", type=int)
    tr.add_argument("--allow-network", action="store_true")
    tr.add_argument("--allow-experimental", action="store_true")
    ev = commands.add_parser(
        "evaluate", help="Score independent prediction JSONL deterministically"
    )
    ev.add_argument("--config", default="configs/evaluation.yaml")
    ev.add_argument("--benchmark", required=True)
    ev.add_argument("--predictions", required=True)
    ev.add_argument("--model-id", required=True)
    ev.add_argument("--baseline")
    ev.add_argument("--output", required=True)
    ex = commands.add_parser("export", help="Export local weights with integrity manifests")
    ex.add_argument("--source", required=True)
    ex.add_argument("--output", required=True)
    ex.add_argument(
        "--format", choices=["adapter", "merged", "safetensors", "gguf"], default="adapter"
    )
    ex.add_argument("--base")
    ex.add_argument("--llama-cpp")
    ex.add_argument(
        "--quantization", choices=["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"], default="Q4_K_M"
    )
    inf = commands.add_parser("infer", help="Generate using a local backend")
    inf.add_argument("--config", default="configs/inference.yaml")
    inf.add_argument("--model", required=True)
    inf.add_argument("--prompt", required=True)
    inf.add_argument("--backend", choices=["transformers", "llama-cpp", "ollama"], default=None)
    inf.add_argument("--adapter")
    inf.add_argument("--system")
    inf.add_argument("--temperature", type=float, default=None)
    inf.add_argument("--top-p", type=float, default=None)
    inf.add_argument("--top-k", type=int, default=None)
    inf.add_argument("--context", type=int, default=None)
    inf.add_argument("--max-tokens", type=int, default=None)
    inf.add_argument("--gpu-layers", type=int, default=None)
    inf.add_argument("--tensor-split", type=float, nargs="+")
    models = commands.add_parser("models", help="Immutable local registry and rollback")
    models.add_argument("--root", default="models/registry")
    ms = models.add_subparsers(dest="action", required=True)
    ms.add_parser("list")
    reg = ms.add_parser("register")
    reg.add_argument("metadata")
    activate = ms.add_parser("activate")
    activate.add_argument("model_id")
    experiments = commands.add_parser("experiments", help="Inspect local experiment records")
    experiments.add_argument("action", choices=["list"])
    experiments.add_argument("--root", default="experiments")
    return p


def dispatch(args):
    if args.command == "doctor":
        from rsec.environment import doctor
        from rsec.utils import write_json

        result = doctor()
        if args.output:
            write_json(args.output, result)
        return result
    if args.command in {"config", "train"}:
        from rsec.config import Training, load_training

        config = load_training(args.config, args.profile)
        if args.command == "config":
            return config.model_dump()
        overrides = {
            name: getattr(args, name)
            for name in ("adapter", "output", "max_steps")
            if getattr(args, name) is not None
        }
        if args.allow_network:
            overrides["local_files_only"] = False
        config = Training.model_validate({**config.model_dump(), **overrides})
        from rsec.train import train

        return train(config, args.smoke, args.resume, args.allow_experimental)
    if args.command == "data":
        if args.action == "ingest":
            from rsec.knowledge import ingest

            return ingest(
                args.input,
                args.output,
                args.source,
                args.source_url,
                args.license,
                args.version,
                args.redistribution,
                args.reviewed,
                args.purpose,
                args.anonymize,
            )
        if args.action == "download":
            from rsec.download import acquire

            return acquire(args.config, args.output)
        if args.action == "download-hf":
            from rsec.download import acquire_hf

            return acquire_hf(
                args.dataset_id, args.revision, args.output, args.license, args.reviewed, args.split
            )
        from rsec.data import prepare, validate_release

        if args.action == "validate":
            return validate_release(args.directory)
        if args.category_cap is not None and args.category_cap < 1:
            raise RsecError("Category cap must be positive")
        return prepare(
            [*args.input, *args.replay],
            args.output,
            args.seed,
            args.benchmarks,
            args.anonymize,
            args.category_cap,
        )
    if args.command == "predict":
        from rsec.predict import predict

        return predict(
            args.benchmark, args.model, args.output, args.backend, args.adapter, args.max_tokens
        )
    if args.command == "evaluate":
        from rsec.evaluate import evaluate

        return evaluate(
            args.benchmark, args.predictions, args.output, args.model_id, args.baseline, args.config
        )
    if args.command == "export":
        from rsec.export import export

        return export(
            args.source, args.output, args.format, args.base, args.llama_cpp, args.quantization
        )
    if args.command == "infer":
        import yaml

        from rsec.inference import infer
        from rsec.utils import bounded_read

        options = vars(args).copy()
        options.pop("command")
        settings = yaml.safe_load(bounded_read(options.pop("config")))
        if settings.pop("local_files_only", True) is not True:
            raise RsecError("Inference requires local_files_only=true")
        allowed = {
            "backend",
            "temperature",
            "top_p",
            "top_k",
            "context",
            "max_tokens",
            "system",
            "gpu_layers",
            "tensor_split",
        }
        if set(settings) - allowed:
            raise RsecError("Unknown inference configuration field")
        settings.update({key: value for key, value in options.items() if value is not None})
        return infer(**settings)
    if args.command == "models":
        from rsec.tracking import Registry
        from rsec.utils import read_json

        registry = Registry(args.root)
        if args.action == "list":
            return registry.list()
        if args.action == "register":
            return registry.register(read_json(args.metadata))
        return registry.activate(args.model_id)
    if args.command == "experiments":
        from rsec.tracking import list_runs

        return list_runs(args.root)
    raise RsecError("Unknown command")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = dispatch(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except RsecError as error:
        print(f"rsec: {error}", file=sys.stderr)
        return 2
    except subprocess.SubprocessError:
        print(
            "rsec: external tool failed; inspect its diagnostics and toolchain dependencies",
            file=sys.stderr,
        )
        return 2
    except ImportError as error:
        print(
            f"rsec: missing optional dependency {error.name}; see installation profiles",
            file=sys.stderr,
        )
        return 2
    except (ValueError, OSError, KeyError, RuntimeError) as error:
        # Input/credentials from third-party exception strings are not printed.
        print(
            f"rsec: {type(error).__name__}: operation failed; check inputs, paths, integrity and configuration",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
