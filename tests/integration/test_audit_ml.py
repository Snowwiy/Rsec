"""Real CPU tensor/tokenizer integration; no CUDA capability is implied."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.ml


@pytest.mark.parametrize("assistant_only", [False, True])
def test_actual_trl_labels_padding_and_cross_entropy(tmp_path, assistant_only):
    torch = pytest.importorskip("torch")
    pytest.importorskip("trl")
    from trl import SFTConfig, SFTTrainer

    from rsec.config import load_training
    from rsec.train import supervised_dataset, tiny_model

    model, tokenizer = tiny_model()
    messages = [
        {"role": "user", "content": "Review code."},
        {"role": "assistant", "content": "Use queries."},
        {"role": "user", "content": "Review defensive code."},
        {"role": "assistant", "content": "Use parameterized queries."},
    ]
    short = [
        {"role": "user", "content": "Review code."},
        {"role": "assistant", "content": "Use queries."},
    ]
    config = load_training().model_copy(update={"assistant_only": assistant_only})
    data = supervised_dataset([{"messages": messages}, {"messages": short}], tokenizer, config)
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=data,
        args=SFTConfig(
            output_dir=str(tmp_path / "trainer"),
            use_cpu=True,
            report_to=[],
            packing=False,
            assistant_only_loss=assistant_only,
            completion_only_loss=not assistant_only,
        ),
    )
    batch = trainer.data_collator([trainer.train_dataset[i] for i in range(2)])
    assert torch.all(batch["labels"][batch["attention_mask"] == 0] == -100)
    full = tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False)
    if assistant_only:
        masks = tokenizer.apply_chat_template(
            messages, return_dict=True, return_assistant_tokens_mask=True
        )["assistant_masks"]
        expected = [token if mask else -100 for token, mask in zip(full, masks, strict=True)]
    else:
        prefix = tokenizer.apply_chat_template(
            messages[:-1], add_generation_prompt=True, tokenize=True, return_dict=False
        )
        expected = [-100] * len(prefix) + full[len(prefix) :]
    assert batch["labels"][0, : len(expected)].tolist() == expected
    assert any(v != -100 for v in expected)
    assert expected[-1] == tokenizer.eos_token_id
    model.eval()
    with torch.no_grad():
        output = model(**batch)
        manual = torch.nn.functional.cross_entropy(
            output.logits[:, :-1].reshape(-1, model.config.vocab_size),
            batch["labels"][:, 1:].reshape(-1),
            ignore_index=-100,
        )
    torch.testing.assert_close(output.loss, manual)
    assert torch.isfinite(output.loss)


def test_token_budget_checks_token_count_and_target_presence():
    pytest.importorskip("torch")
    from rsec.config import load_training
    from rsec.errors import RsecError
    from rsec.train import supervised_dataset, tiny_model

    _, tok = tiny_model()
    cfg = load_training().model_copy(update={"context": 64})
    rows = [
        {
            "messages": [
                {"role": "user", "content": "Review code. " * 100},
                {"role": "assistant", "content": "Use queries."},
            ]
        }
    ]
    with pytest.raises(RsecError, match="exceeds context"):
        supervised_dataset(rows, tok, cfg)
    rows[0]["messages"][0]["content"] = "Review code."
    tok.chat_template = "{% for m in messages %}{{ m['content'] }}{% endfor %}"
    with pytest.raises(RsecError, match="no assistant"):
        supervised_dataset(rows, tok, cfg.model_copy(update={"assistant_only": True}))
    tok.chat_template = (
        "{% if add_generation_prompt %}wrong prefix{% else %}Review code.{% endif %}"
    )
    with pytest.raises(RsecError, match="prompt prefix"):
        supervised_dataset(rows, tok, cfg)


def test_real_export_guards_and_integrity(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    import importlib

    from peft import LoraConfig, get_peft_model

    from rsec.artifacts import local_artifacts, verify_export
    from rsec.errors import RsecError
    from rsec.export import export, inspect_tensors, resources
    from rsec.train import tiny_model

    module = importlib.import_module("rsec.export")
    model, tok = tiny_model()
    base = tmp_path / "base"
    model.save_pretrained(base)
    tok.save_pretrained(base)
    adapter = tmp_path / "adapter"
    model = get_peft_model(model, LoraConfig(task_type="CAUSAL_LM", target_modules=["q_proj"]))
    model.save_pretrained(adapter)
    tok.save_pretrained(adapter)
    first = local_artifacts(adapter, adapter=True, fingerprint=True)
    out = tmp_path / "out"
    export(adapter, out)
    assert first == local_artifacts(adapter, adapter=True, fingerprint=True)
    verify_export(out)
    (out / "tokenizer_config.json").write_text("{}")
    with pytest.raises(RsecError, match="integrity"):
        local_artifacts(out, adapter=True)
    with pytest.raises(FileExistsError):
        export(adapter, out)
    with pytest.raises(RsecError, match="quantization"):
        export(adapter, tmp_path / "a", quantization="Q0")
    with pytest.raises(RsecError, match="requires"):
        export(adapter, tmp_path / "b", format="merged")
    with pytest.raises(RsecError, match="Unknown"):
        export(adapter, tmp_path / "c", format="bad")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RsecError, match="Safetensors"):
        inspect_tensors(empty)
    monkeypatch.setattr(module, "memory_available", lambda: 0)
    with pytest.raises(RsecError, match="RAM"):
        resources(base, tmp_path / "d")
    monkeypatch.setattr(module.shutil, "disk_usage", lambda p: type("Usage", (), {"free": 0})())
    with pytest.raises(RsecError, match="storage"):
        resources(base, tmp_path / "d")
    (adapter / "link").symlink_to(base / "config.json")
    with pytest.raises(RsecError, match="Symlink"):
        export(adapter, tmp_path / "e")


def test_native_conversion_failure_never_publishes_success_manifest(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    import importlib

    from rsec.errors import RsecError
    from rsec.train import tiny_model

    module = importlib.import_module("rsec.export")
    model, tok = tiny_model()
    base = tmp_path / "base"
    model.save_pretrained(base)
    tok.save_pretrained(base)
    checkout = tmp_path / "tool"
    (checkout / "build/bin").mkdir(parents=True)
    (checkout / "convert_hf_to_gguf.py").write_text("# inert test sentinel")
    (checkout / "build/bin/llama-quantize").write_text("inert")
    monkeypatch.setattr(module, "command", lambda args: "0" * 40 if args[-1] == "HEAD" else "")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        # The subprocess contract is tested; bytes deliberately violate GGUF.
        path = Path(args[args.index("--outfile") + 1]) if "--outfile" in args else Path(args[2])
        path.write_bytes(b"BAD!")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    out = tmp_path / "out"
    with pytest.raises(RsecError, match="header"):
        module.export(base, out, format="gguf", llama_cpp=checkout)
    assert len(calls) == 2
    assert not (out / "export_manifest.json").exists()


def test_empty_tensors_and_missing_native_toolchain_rejected(tmp_path):
    pytest.importorskip("torch")
    from safetensors.torch import save_file

    from rsec.errors import RsecError
    from rsec.export import export, inspect_tensors
    from rsec.train import tiny_model

    empty = tmp_path / "empty"
    empty.mkdir()
    save_file({}, empty / "empty.safetensors")
    with pytest.raises(RsecError, match="Empty tensor"):
        inspect_tensors(empty)
    model, tok = tiny_model()
    base = tmp_path / "base"
    model.save_pretrained(base)
    tok.save_pretrained(base)
    link = tmp_path / "link"
    link.mkdir()
    (link / "weights.safetensors").symlink_to(base / "model.safetensors")
    with pytest.raises(RsecError, match="Symlink"):
        inspect_tensors(link)
    with pytest.raises(RsecError, match="reviewed"):
        export(base, tmp_path / "out", format="gguf")
    tool = tmp_path / "tool"
    tool.mkdir()
    with pytest.raises(RsecError, match="missing"):
        export(base, tmp_path / "out2", format="gguf", llama_cpp=tool)
