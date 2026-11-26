"""TRL SFT + PEFT QLoRA, explicit distribution, and real offline CPU smoke training."""

import os
import signal
from pathlib import Path

from rsec.artifacts import local_artifacts
from rsec.config import Training
from rsec.data import load_rows, validate_release
from rsec.environment import command, doctor
from rsec.errors import RsecError
from rsec.tracking import Experiment
from rsec.utils import digest, read_json, sha256, write_json


def tiny_model():
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from transformers import PreTrainedTokenizerFast, Qwen2Config, Qwen2ForCausalLM

    words = [
        "[PAD]",
        "[UNK]",
        "[EOS]",
        "user",
        "assistant",
        "system",
        "Review",
        "defensive",
        "code",
        "Use",
        "parameterized",
        "queries",
        ".",
        ":",
    ]
    backend = Tokenizer(WordLevel({word: i for i, word in enumerate(words)}, unk_token="[UNK]"))
    backend.pre_tokenizer = Whitespace()
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=backend, unk_token="[UNK]", pad_token="[PAD]", eos_token="[EOS]"
    )
    tokenizer.chat_template = "{% for m in messages %}{{m['role'] + ': '}}{% if m['role'] == 'assistant' %}{% generation %}{{m['content'] + eos_token}}{% endgeneration %}{% else %}{{m['content'] + '\n'}}{% endif %}{% endfor %}{% if add_generation_prompt %}{{'assistant: '}}{% endif %}"
    model = Qwen2ForCausalLM(
        Qwen2Config(
            vocab_size=len(words),
            hidden_size=32,
            intermediate_size=64,
            num_hidden_layers=1,
            num_attention_heads=2,
            num_key_value_heads=2,
            max_position_embeddings=256,
            pad_token_id=0,
            eos_token_id=2,
            bos_token_id=None,
        )
    )
    return model, tokenizer


def verify_checkpoint(path, signature):
    path = Path(path).resolve(strict=True)
    metadata = read_json(path / "rsec_checkpoint.json")
    if metadata["signature"] != signature:
        raise RsecError("Checkpoint model/data/config signature mismatch")
    if not {"trainer_state.json", "optimizer.pt", "scheduler.pt"}.issubset(metadata["files"]):
        raise RsecError("Resume requires a full trainer checkpoint including optimizer/scheduler")
    from rsec.utils import confined

    actual = {
        str(p.relative_to(path))
        for p in path.rglob("*")
        if p.is_file() and p.name != "rsec_checkpoint.json"
    }
    if actual != set(metadata["files"]) or any(p.is_symlink() for p in path.rglob("*")):
        raise RsecError("Checkpoint contains unmanifested or symlink files")
    for name, expected in metadata["files"].items():
        if sha256(confined(path, name)) != expected:
            raise RsecError("Checkpoint integrity mismatch")
    return str(path)


def supervised_dataset(records, tokenizer, config):
    from datasets import Dataset

    examples = []
    for r in records:
        messages = r["messages"]
        ids = tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False)
        if len(ids) > config.context:
            raise RsecError(
                "Example exceeds context; curate or increase context, never silently truncate answers"
            )
        if config.assistant_only:
            masked = tokenizer.apply_chat_template(
                messages, tokenize=True, return_dict=True, return_assistant_tokens_mask=True
            )
            if not any(masked["assistant_masks"]):
                raise RsecError("Chat template produced no assistant target tokens")
            examples.append({"messages": messages})
        else:
            prefix = tokenizer.apply_chat_template(
                messages[:-1], tokenize=True, add_generation_prompt=True, return_dict=False
            )
            if ids[: len(prefix)] != prefix or len(prefix) >= len(ids):
                raise RsecError(
                    "Chat template must preserve the prompt prefix and nonempty completion"
                )
            examples.append({"prompt": messages[:-1], "completion": messages[-1:]})
    return Dataset.from_list(examples)


def train(config: Training, smoke=False, resume=None, allow_experimental=False):
    environment = doctor()
    if not smoke and not environment["cuda"]:
        raise RsecError(
            "QLoRA requires a verified CUDA environment; use --smoke for real tiny CPU training"
        )
    if config.strategy != "single" and not allow_experimental:
        raise RsecError(
            "Distributed profiles require --allow-experimental and physical GPU validation"
        )
    world = int(os.environ.get("WORLD_SIZE", "1"))
    if config.strategy != "single" and world < 2:
        raise RsecError("Launch distributed profiles with Accelerate and at least two GPUs")
    if config.strategy == "single" and world != 1:
        raise RsecError("Single-GPU profile cannot run under a distributed launcher")
    if config.strategy == "fsdp" and os.environ.get("ACCELERATE_USE_FSDP", "").lower() != "true":
        raise RsecError("FSDP profile requires configs/accelerate/multi_gpu_fsdp.yaml")
    if smoke and (config.strategy != "single" or config.adapter):
        raise RsecError("Smoke mode uses its own fresh single-CPU model")
    adapter_hash = (
        local_artifacts(config.adapter, adapter=True, fingerprint=True) if config.adapter else None
    )
    if not smoke and config.strategy != "single" and world > len(environment["gpus"]):
        raise RsecError("Distributed process count exceeds visible CUDA devices")
    if not smoke and config.precision == "bf16" and not all(g["bf16"] for g in environment["gpus"]):
        raise RsecError("BF16 requested but unavailable on a detected GPU")
    if not smoke and config.backend == "unsloth":
        raise RsecError(
            "Unsloth 2026.11.12 is BLOCKED: incompatible Transformers, TRL and datasets pins; use transformers"
        )

    import torch
    from accelerate import PartialState
    from accelerate.utils import broadcast_object_list
    from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        EarlyStoppingCallback,
        TrainerCallback,
        set_seed,
    )
    from trl import SFTConfig, SFTTrainer

    distributed = PartialState(cpu=smoke)
    set_seed(config.seed)
    if smoke:
        torch.set_num_threads(1)
        model, tokenizer = tiny_model()
        rows = [
            {
                "messages": [
                    {"role": "user", "content": "Review defensive code."},
                    {"role": "assistant", "content": "Use parameterized queries."},
                ]
            }
        ] * 8
        evaluation = rows[:2]
        dataset_hash = digest(rows)
    else:
        validate_release(config.dataset)
        dataset_hash = sha256(Path(config.dataset) / "dataset_manifest.json")
        rows = list(load_rows(Path(config.dataset) / "train.jsonl"))
        evaluation = list(load_rows(Path(config.dataset) / "eval.jsonl"))
        bf16 = config.precision == "bf16" or (
            config.precision == "auto" and all(g["bf16"] for g in environment["gpus"])
        )
        dtype = (
            torch.bfloat16
            if bf16
            else torch.float32
            if config.precision == "fp32"
            else torch.float16
        )
        storage_dtype = (
            torch.float32 if config.strategy == "fsdp" and dtype == torch.float16 else dtype
        )
        tokenizer = AutoTokenizer.from_pretrained(
            config.model,
            revision=config.revision,
            trust_remote_code=False,
            local_files_only=config.local_files_only,
        )
        kwargs = {
            "revision": config.revision,
            "trust_remote_code": False,
            "use_safetensors": True,
            "local_files_only": config.local_files_only,
            "dtype": storage_dtype if config.strategy == "fsdp" else dtype,
        }
        if config.quantize:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=dtype,
                **({"bnb_4bit_quant_storage": storage_dtype} if config.strategy == "fsdp" else {}),
            )
        if config.strategy != "fsdp":
            kwargs["device_map"] = {"": distributed.local_process_index}
        model = AutoModelForCausalLM.from_pretrained(config.model, **kwargs)
        if config.quantize and config.strategy != "fsdp":
            # PEFT upcasts non-4bit layers to FP32. FSDP must retain matched storage/model dtype.
            model = prepare_model_for_kbit_training(
                model,
                use_gradient_checkpointing=True,
                activation_checkpointing_kwargs={"use_reentrant": False},
            )
    if not tokenizer.chat_template:
        raise RsecError("An official model chat template is required")
    if tokenizer.eos_token_id is None:
        raise RsecError("Tokenizer requires an explicit EOS token")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    if config.assistant_only and "{% generation" not in tokenizer.chat_template:
        raise RsecError("Assistant masks unsupported by this template; use completion-only default")

    training_data = supervised_dataset(rows, tokenizer, config)
    eval_data = supervised_dataset(evaluation, tokenizer, config)
    lora = LoraConfig(
        r=config.rank,
        lora_alpha=config.alpha,
        lora_dropout=config.dropout,
        target_modules=config.target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )
    if config.adapter:
        model = PeftModel.from_pretrained(
            model,
            str(Path(config.adapter).resolve(strict=True)),
            is_trainable=True,
            local_files_only=True,
        )
    else:
        model = get_peft_model(model, lora)
    model.config.use_cache = False
    signature = digest(
        {
            "model": "tiny-local" if smoke else config.model,
            "revision": config.revision,
            "dataset": dataset_hash,
            "rank": config.rank,
            "alpha": config.alpha,
            "modules": config.target_modules,
            "seed": config.seed,
            "context": config.context,
            "adapter": config.adapter,
            "adapter_hash": adapter_hash,
            "training_config": config.model_dump(
                exclude={"output", "max_steps", "local_files_only"}
            ),
        }
    )
    if resume:
        resume = verify_checkpoint(resume, signature)
    experiment = (
        Experiment(
            config.output,
            {
                "config": config.model_dump(),
                "dataset_hash": dataset_hash,
                "commit": command(["git", "rev-parse", "HEAD"]),
                "environment": environment,
                "smoke": smoke,
                "resume": resume,
            },
        )
        if distributed.is_main_process
        else None
    )
    shared = [experiment.id if experiment else None]
    broadcast_object_list(shared)
    run_path = Path(config.output) / shared[0]
    interrupted = [False]
    previous_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))

    class Tracking(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if experiment:
                metrics = dict(logs or {})
                metrics["step"] = state.global_step
                metrics["tokens_processed"] = state.num_input_tokens_seen
                if torch.cuda.is_available():
                    metrics["vram_allocated_bytes"] = torch.cuda.memory_allocated()
                    metrics["vram_peak_bytes"] = torch.cuda.max_memory_allocated()
                experiment.log(metrics)

        def on_step_end(self, args, state, control, **kwargs):
            if interrupted[0]:
                control.should_save = True
                control.should_training_stop = True
            return control

        def on_save(self, args, state, control, **kwargs):
            distributed.wait_for_everyone()
            if distributed.is_main_process:
                checkpoint = Path(args.output_dir) / f"checkpoint-{state.global_step}"
                files = {
                    str(p.relative_to(checkpoint)): sha256(p)
                    for p in checkpoint.rglob("*")
                    if p.is_file() and p.name != "rsec_checkpoint.json"
                }
                write_json(
                    checkpoint / "rsec_checkpoint.json",
                    {"signature": signature, "files": files},
                    overwrite=True,
                )

    callbacks = [Tracking()]
    if config.early_stopping_patience:
        callbacks.append(
            EarlyStoppingCallback(early_stopping_patience=config.early_stopping_patience)
        )
    bf16 = not smoke and (
        config.precision == "bf16"
        or (config.precision == "auto" and all(g["bf16"] for g in environment["gpus"]))
    )
    try:
        args = SFTConfig(
            output_dir=str(run_path / "checkpoints"),
            max_length=config.context,
            per_device_train_batch_size=config.batch_size,
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=1 if smoke else config.accumulation,
            num_train_epochs=config.epochs,
            max_steps=(3 if config.max_steps == -1 else config.max_steps)
            if smoke
            else config.max_steps,
            learning_rate=config.learning_rate,
            warmup_steps=config.warmup_ratio,
            save_strategy="steps",
            save_steps=1 if smoke else config.save_steps,
            save_total_limit=None,
            eval_strategy="steps",
            eval_steps=1 if smoke else config.eval_steps,
            logging_steps=1,
            seed=config.seed,
            data_seed=config.seed,
            bf16=bf16,
            fp16=not smoke and not bf16 and config.precision != "fp32",
            use_cpu=smoke,
            activation_checkpointing=not smoke,
            activation_checkpointing_kwargs={"use_reentrant": False},
            # PEFT documents a checkpoint-save failure for paged_adamw_8bit with FSDP-QLoRA.
            optim="adamw_torch"
            if smoke or not config.quantize or config.strategy == "fsdp"
            else "paged_adamw_8bit",
            report_to=["tensorboard"] if config.tensorboard else [],
            push_to_hub=False,
            packing=False,
            assistant_only_loss=config.assistant_only,
            completion_only_loss=not config.assistant_only,
            include_num_input_tokens_seen=True,
            ddp_find_unused_parameters=False if config.strategy == "ddp" else None,
            load_best_model_at_end=bool(config.early_stopping_patience),
            metric_for_best_model="eval_loss",
            greater_is_better=False,
        )
        trainer = SFTTrainer(
            model=model,
            args=args,
            train_dataset=training_data,
            eval_dataset=eval_data,
            processing_class=tokenizer,
            callbacks=callbacks,
        )
        if config.strategy == "fsdp":
            from peft.utils.other import fsdp_auto_wrap_policy

            trainer.accelerator.state.fsdp_plugin.auto_wrap_policy = fsdp_auto_wrap_policy(
                trainer.model
            )
        result = trainer.train(resume_from_checkpoint=resume)
        if config.strategy == "fsdp":
            trainer.accelerator.state.fsdp_plugin.set_state_dict_type("FULL_STATE_DICT")
        trainer.save_model(str(run_path / "adapter"))
        if distributed.is_main_process:
            # Trainer emits a pickle of TrainingArguments; final model loaders need only JSON config.
            (run_path / "adapter" / "training_args.bin").unlink(missing_ok=True)
            tokenizer.save_pretrained(run_path / "adapter")
            write_json(run_path / "training_config.json", config.model_dump())
            experiment.finish(
                "interrupted" if interrupted[0] else "completed",
                metrics=result.metrics,
                checkpoints=[str(p) for p in (run_path / "checkpoints").glob("checkpoint-*")],
            )
        return {
            "experiment": shared[0],
            "path": str(run_path),
            "status": "interrupted" if interrupted[0] else "completed",
            "smoke": smoke,
            "metrics": result.metrics,
        }
    except BaseException as error:
        if experiment:
            experiment.finish(
                "failed",
                error_type=type(error).__name__,
                cuda_oom=isinstance(error, torch.cuda.OutOfMemoryError),
            )
        raise
    finally:
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    from rsec.cli import main

    raise SystemExit(main(["train", *os.sys.argv[1:]]))
