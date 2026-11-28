"""Local preflight for the pinned Inkling 2 Mini NF4 checkpoint."""

import argparse
import json
import math
import os
import re
import sys
import time
from importlib import import_module
from pathlib import Path

from rsec.errors import RsecError
from rsec.utils import bounded_read, sha256, write_json

ARCHITECTURE = "Inkling2LoopForConditionalGeneration"
MODEL_TYPE = "inkling2_loop"
CHECKPOINT = "unsloth/Inkling-2-Mini-unsloth-bnb-4bit"
REVISION = "22035f8bf3fd71a588d78591f8b3ec45c0994524"
SHARDS = {
    "model-00001-of-00004.safetensors": 4945807927,
    "model-00002-of-00004.safetensors": 4883474608,
    "model-00003-of-00004.safetensors": 4167751714,
    "model-00004-of-00004.safetensors": 1563074760,
}
GATE_PROJECTIONS = {
    f"{which}_message_gate.{projection}"
    for which in ("q", "k", "v", "mlp")
    for projection in ("down_proj", "forget_gate_proj", "message_gate_proj")
}
PRESERVE_16_BIT = {*GATE_PROJECTIONS, "mlp.gate", "vision_tower", "lm_head"}
EXPERT_PROJECTIONS = {
    f"model.llm.layers.{index}.mlp.experts.{projection}"
    for index in range(24)
    for projection in ("down_proj", "gate_up_proj")
}
STORED_GATE_DTYPES = {
    f"model.llm.layers.{index}.controllers.{group}.{parameter}": dtype
    for index in range(6, 18)
    for group in ("attn", "k", "v", "mlp")
    for parameter, dtype in (
        ("down_weight", "BF16"),
        ("forget_weight", "F32"),
        ("gain_weight", "F32"),
    )
}


def validate_quantization(config):
    if (
        not isinstance(config, dict)
        or config.get("model_type") != MODEL_TYPE
        or config.get("architectures") != [ARCHITECTURE]
    ):
        raise RsecError("Expected the native Inkling 2 Mini architecture")
    if config.get("auto_map"):
        raise RsecError("Inkling requires the installed Transformers implementation")
    quant = config.get("quantization_config")
    if (
        not isinstance(quant, dict)
        or quant.get("quant_method") != "bitsandbytes"
        or quant.get("bnb_4bit_quant_type") != "nf4"
        or quant.get("load_in_4bit") is not True
        or quant.get("bnb_4bit_use_double_quant") is not True
    ):
        raise RsecError("Expected the pre-quantized BitsAndBytes double-NF4 checkpoint")
    skipped = quant.get("llm_int8_skip_modules")
    if (
        not isinstance(skipped, list)
        or any(not isinstance(name, str) for name in skipped)
        or not PRESERVE_16_BIT.issubset(skipped)
    ):
        raise RsecError("The checkpoint must preserve the message gates, router, vision and head")


def validate_index(weight_map):
    if not isinstance(weight_map, dict) or any(
        not isinstance(name, str) or not isinstance(path, str) for name, path in weight_map.items()
    ):
        raise RsecError("Expected a local Safetensors weight map")
    if set(weight_map.values()) != SHARDS.keys():
        raise RsecError("The Inkling weight map must use the four fixed local shards")
    if any(
        not {key, key + ".nested_absmax", key + ".quant_state.bitsandbytes__nf4"}.issubset(
            weight_map
        )
        for key in EXPERT_PROJECTIONS
    ):
        raise RsecError("Missing double-NF4 metadata for one or more routed expert banks")
    if any(
        (".controllers." in key or "message_gate." in key) and ".quant_state." in key
        for key in weight_map
    ):
        raise RsecError("Unexpected quantized loop message gate")
    if not STORED_GATE_DTYPES.keys() <= weight_map.keys():
        raise RsecError("Missing one or more loop message gate tensors")


def local_file(directory, name):
    path = directory / name
    if path.resolve() != path or not path.is_file():
        raise RsecError(f"Expected a regular local checkpoint file: {name}")
    return path


def inspect_checkpoint(directory):
    """Check the fixed layout and stored tensor dtypes without importing CUDA."""
    directory = Path(directory).resolve(strict=True)
    config = json.loads(bounded_read(local_file(directory, "config.json"), 131072))
    validate_quantization(config)
    index = json.loads(bounded_read(local_file(directory, "model.safetensors.index.json"), 1048576))
    weight_map = index.get("weight_map")
    validate_index(weight_map)
    for name in ("chat_template.jinja", "tokenizer.json", "processor_config.json"):
        local_file(directory, name)
    gate_tensors = set()
    expert_tensors = set()
    for name, size in SHARDS.items():
        shard = local_file(directory, name)
        if shard.stat().st_size != size:
            raise RsecError(f"Unexpected byte size for pinned shard: {name}")
        with shard.open("rb") as stream:
            length = int.from_bytes(stream.read(8), "little")
            if not 2 <= length <= 8 * 1024**2:
                raise RsecError("Invalid Safetensors header length")
            tensors = json.loads(stream.read(length))
        for key, tensor in tensors.items():
            if key in EXPERT_PROJECTIONS:
                expert_tensors.add(key)
                if weight_map[key] != name or tensor["dtype"] != "U8":
                    raise RsecError("Packed NF4 expert storage must be uint8")
            if key in STORED_GATE_DTYPES:
                gate_tensors.add(key)
                if weight_map[key] != name or tensor["dtype"] != STORED_GATE_DTYPES[key]:
                    raise RsecError("A loop message gate has unexpected storage precision")
    if gate_tensors != STORED_GATE_DTYPES.keys() or expert_tensors != EXPERT_PROJECTIONS:
        raise RsecError("Expected both stored message gates and all expert banks")
    return {
        "checkpoint": CHECKPOINT,
        "expected_revision": REVISION,
        "architecture": ARCHITECTURE,
        "status": "LOCAL_LAYOUT_CHECKED",
        "weights_bytes": sum(SHARDS.values()),
        "packed_expert_banks": len(expert_tensors),
        "preserved_gate_tensors": len(gate_tensors),
    }


def smoke(checkpoint, output, *, steps=2, accumulation=1, attention_only=False):
    """Exercise the vendor's single-process layer split using only synthetic text."""
    if not 1 <= steps <= 4 or not 1 <= accumulation <= 8:
        raise RsecError("Use at most four steps and eight accumulation iterations for this fixture")
    if os.environ.get("WORLD_SIZE", "1") != "1":
        raise RsecError("Inkling smoke requires the single-process layer split")
    checkpoint = Path(checkpoint).resolve(strict=True)
    evidence = inspect_checkpoint(checkpoint)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    for name in (
        "HF_HUB_OFFLINE",
        "HF_HUB_DISABLE_TELEMETRY",
        "TRANSFORMERS_OFFLINE",
        "HF_DATASETS_OFFLINE",
        "UNSLOTH_DISABLE_STATISTICS",
    ):
        os.environ[name] = "1"
    os.environ.setdefault("UNSLOTH_COMPILE_LOCATION", str(output / "unsloth_compiled_cache"))

    fast_model = import_module("unsloth").FastModel
    train_on_responses_only = import_module("unsloth.chat_templates").train_on_responses_only

    import torch
    from datasets import Dataset
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    from safetensors.torch import load_file
    from trl import SFTConfig, SFTTrainer

    if not torch.cuda.is_available() or torch.cuda.device_count() != 2:
        raise RsecError("Expose exactly two CUDA devices by UUID for the Inkling smoke")
    for index in range(2):
        torch.cuda.reset_peak_memory_stats(index)

    start = time.perf_counter()
    model, processor = fast_model.from_pretrained(
        model_name=str(checkpoint),
        max_seq_length=512,
        load_in_4bit=True,
        full_finetuning=False,
        trust_remote_code=False,
        local_files_only=True,
    )
    placement = {p.device.index for p in model.parameters() if p.device.type == "cuda"}
    if placement != {0, 1}:
        raise RsecError("The checkpoint did not place parameters across both CUDA devices")
    gate_weights = {
        name: parameter
        for name, parameter in model.named_parameters()
        if any(name.endswith(f"{gate}.weight") for gate in GATE_PROJECTIONS)
    }
    if len(gate_weights) != len(STORED_GATE_DTYPES) or any(
        weight.dtype != torch.float32
        if name.endswith(("forget_gate_proj.weight", "message_gate_proj.weight"))
        else weight.dtype not in (torch.bfloat16, torch.float32)
        for name, weight in gate_weights.items()
    ):
        raise RsecError("Loaded message gates must preserve their BF16 or FP32 precision")
    load_seconds = time.perf_counter() - start
    print(f"Inkling weights placed on two GPU devices in {load_seconds:.1f} s", flush=True)

    model = fast_model.get_peft_model(
        model,
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=not attention_only,
        r=8,
        lora_alpha=8,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    params = {name: value for name, value in model.named_parameters() if value.requires_grad}
    if not params or any("lora_" not in name for name in params):
        raise RsecError("Only LoRA parameters may be trainable in the Inkling smoke")
    before = {
        name: value.detach().reshape(-1)[:128].cpu().clone() for name, value in params.items()
    }
    pairs = [
        ("What is two plus five? Give the number only.", "7"),
        ("¿Cuál es el doble de cuatro? Responde con el número.", "8"),
    ]
    texts = [
        processor.apply_chat_template(
            [{"role": "user", "content": question}, {"role": "assistant", "content": answer}],
            tokenize=False,
            add_generation_prompt=False,
            reasoning_effort="none",
        )
        for question, answer in pairs
    ]
    trainer = SFTTrainer(
        model=model,
        processing_class=processor,
        train_dataset=Dataset.from_dict({"text": texts}),
        args=SFTConfig(
            output_dir=str(output / "trainer"),
            dataset_text_field="text",
            max_length=512,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=accumulation,
            max_steps=steps,
            learning_rate=2e-4,
            optim="adamw_8bit",
            seed=3407,
            logging_steps=1,
            save_strategy="no",
            report_to="none",
            packing=False,
        ),
    )
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|message_user|>",
        response_part="<|message_model|>",
    )
    start = time.perf_counter()
    stats = trainer.train()
    for index in range(2):
        torch.cuda.synchronize(index)
    elapsed = time.perf_counter() - start
    loss = float(stats.training_loss)
    if stats.global_step != steps or not math.isfinite(loss):
        raise RsecError("Expected each requested optimizer step and finite training loss")
    changed = sum(
        not torch.equal(value.detach().reshape(-1)[:128].cpu(), before[name])
        for name, value in params.items()
    )
    if not changed:
        raise RsecError("LoRA parameters did not update")
    peak = [torch.cuda.max_memory_allocated(i) for i in range(2)]
    adapter = output / "adapter"
    start = time.perf_counter()
    model.save_pretrained(adapter, safe_serialization=True, save_embedding_layers=False)
    processor.save_pretrained(adapter)
    adapter_file = adapter / "adapter_model.safetensors"
    digest = sha256(adapter_file)
    save_seconds = time.perf_counter() - start
    start = time.perf_counter()
    state = load_file(str(adapter_file))
    with torch.no_grad():
        for p in params.values():
            p.zero_()
    set_peft_model_state_dict(model, state)
    recovered = get_peft_model_state_dict(model)
    if set(state) != set(recovered) or any(
        not torch.equal(value, recovered[name].detach().cpu()) for name, value in state.items()
    ):
        raise RsecError("Restored Inkling adapter differs from the saved tensors")
    if digest != sha256(adapter_file):
        raise RsecError("Inkling adapter changed during recovery")
    evidence.update(
        status="CUDA_LAYER_SPLIT_MEASURED",
        devices=[torch.cuda.get_device_name(i) for i in range(2)],
        parameter_bytes_by_device={
            str(device): sum(
                p.numel() * p.element_size() for p in model.parameters() if p.device == device
            )
            for device in {p.device for p in model.parameters()}
        },
        peak_allocated_bytes=peak,
        steps=steps,
        context=512,
        rank=8,
        accumulation=accumulation,
        attention_only=attention_only,
        loss=loss,
        changed_sampled_parameters=changed,
        load_seconds=load_seconds,
        train_seconds=elapsed,
        save_seconds=save_seconds,
        restore_seconds=time.perf_counter() - start,
        adapter_sha256=digest,
    )
    write_json(output / "validation.json", evidence)
    return evidence


def add_arguments(parser):
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--smoke-output", type=Path)
    parser.add_argument("--uuid", action="append", help="Physical GPU UUID, in CUDA device order")
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--accumulation", type=int, default=1)
    parser.add_argument("--attention-only", action="store_true")


def dispatch(args):
    if args.smoke_output is None:
        if args.uuid:
            raise RsecError("GPU UUIDs are only used with --smoke-output")
        return inspect_checkpoint(args.checkpoint)
    if os.name != "posix":
        raise RsecError("Run the Inkling CUDA fixture in the isolated WSL2/Linux environment")
    if not args.uuid or len(set(args.uuid)) != 2 or len(args.uuid) != 2:
        raise RsecError("Use exactly two distinct --uuid arguments for thermal supervision")
    if any(not re.fullmatch(r"GPU-[0-9a-fA-F-]{36}", value) for value in args.uuid):
        raise RsecError("Use complete NVIDIA GPU UUIDs")

    from rsec.thermal import supervise_process

    output = args.smoke_output / "fixture"
    command = [
        sys.executable,
        "-m",
        "rsec.inkling",
        str(args.checkpoint),
        "--smoke-output",
        str(output),
        "--steps",
        str(args.steps),
        "--accumulation",
        str(args.accumulation),
    ]
    if args.attention_only:
        command.append("--attention-only")
    supervise_process(args.uuid, args.smoke_output, command, timeout=1200)
    return json.loads((output / "validation.json").read_text(encoding="utf-8"))


def main():
    """Worker entry point invoked by the supervised Rsec command."""
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args()
    smoke(
        args.checkpoint,
        args.smoke_output,
        steps=args.steps,
        accumulation=args.accumulation,
        attention_only=args.attention_only,
    )


if __name__ == "__main__":
    main()
