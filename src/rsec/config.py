"""Strict configuration; GPU packages are never imported here."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from rsec.errors import RsecError
from rsec.utils import bounded_read, identifier


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Training(Strict):
    model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    revision: str
    backend: Literal["transformers", "unsloth"] = "transformers"
    strategy: Literal["single", "ddp", "fsdp"] = "single"
    precision: Literal["auto", "fp16", "bf16", "fp32"] = "auto"
    quantize: bool = True
    context: int = Field(2048, ge=64, le=131072)
    rank: int = Field(16, ge=1, le=256)
    alpha: int = Field(32, ge=1)
    dropout: float = Field(0.05, ge=0, lt=1)
    learning_rate: float = Field(0.0001, gt=0, le=0.1)
    batch_size: int = Field(1, ge=1)
    accumulation: int = Field(16, ge=1)
    epochs: float = Field(1, gt=0, le=100)
    max_steps: int = Field(-1, ge=-1)
    warmup_ratio: float = Field(0.03, ge=0, lt=1)
    seed: int = 42
    save_steps: int = Field(100, ge=1)
    eval_steps: int = Field(100, ge=1)
    early_stopping_patience: int | None = Field(None, ge=1)
    assistant_only: bool = False
    target_modules: list[str] = [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]
    dataset: str = "data/processed/demo"
    output: str = "experiments"
    adapter: str | None = None
    tensorboard: bool = False
    local_files_only: bool = True

    @model_validator(mode="after")
    def check(self):
        if not self.target_modules or len(set(self.target_modules)) != len(self.target_modules):
            raise RsecError("Provide unique nonempty LoRA target modules")
        if any(not m.strip() for m in self.target_modules):
            raise RsecError("LoRA target modules cannot be empty")
        if self.max_steps == 0:
            raise RsecError("max_steps must be -1 or positive")
        if len(self.revision) != 40 or any(c not in "0123456789abcdef" for c in self.revision):
            raise RsecError("Pin model revision to a full 40-character commit SHA")
        if self.backend == "unsloth" and self.strategy != "single":
            raise RsecError("Use the Transformers backend for experimental distributed profiles")
        if self.strategy == "fsdp" and self.backend != "transformers":
            raise RsecError("FSDP requires the Transformers backend")
        if self.early_stopping_patience and self.eval_steps != self.save_steps:
            raise RsecError("Early stopping requires equal eval_steps and save_steps")
        return self


def load_training(config="configs/qlora_cybersec.yaml", profile=None):
    raw = yaml.safe_load(bounded_read(config))
    if not isinstance(raw, dict):
        raise RsecError("Training configuration must be a mapping")
    if profile:
        identifier(profile)
        overlay = yaml.safe_load(bounded_read(Path(config).parent / "profiles" / f"{profile}.yaml"))
        if not isinstance(overlay, dict):
            raise RsecError("Training profile must be a mapping")
        raw.update(overlay)
    return Training.model_validate(raw)
