from pathlib import Path

import pytest

pytestmark = pytest.mark.ml


def test_real_sft_resume_merge_and_inference(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("trl")
    from rsec.config import load_training
    from rsec.export import export
    from rsec.inference import infer
    from rsec.train import tiny_model, train, verify_checkpoint
    from rsec.utils import read_json

    config = load_training().model_copy(update={"output": str(tmp_path / "runs"), "max_steps": 2})
    run = train(config, smoke=True)
    assert run["status"] == "completed"
    assert run["metrics"]["num_input_tokens_seen"] > 0
    checkpoint = Path(run["path"]) / "checkpoints/checkpoint-2"
    manifest = read_json(checkpoint / "rsec_checkpoint.json")
    assert "optimizer.pt" in manifest["files"]
    verify_checkpoint(checkpoint, manifest["signature"])
    resumed = train(config.model_copy(update={"max_steps": 3}), smoke=True, resume=checkpoint)
    assert resumed["status"] == "completed"
    assert (Path(resumed["path"]) / "checkpoints/checkpoint-3").exists()
    adapter = Path(resumed["path"]) / "adapter"
    assert export(adapter, tmp_path / "export-adapter")["format"] == "adapter"
    torch.manual_seed(config.seed)
    model, tokenizer = tiny_model()
    base = tmp_path / "base"
    model.save_pretrained(base, safe_serialization=True)
    tokenizer.save_pretrained(base)
    merged = tmp_path / "merged"
    export(adapter, merged, format="merged", base=base)
    result = infer(merged, "Review defensive code.", context=128, max_tokens=4, temperature=0)
    assert 0 < result["generated_tokens"] <= 4
    assert result["latency_seconds"] > 0
    assert result["tokens_per_second"] > 0
    from rsec.evaluate import evaluate
    from rsec.predict import predict

    predictions = tmp_path / "random-predictions.jsonl"
    predict("benchmarks/suite.jsonl", str(merged), str(predictions), max_tokens=4)
    report = evaluate(
        "benchmarks/suite.jsonl", predictions, tmp_path / "evaluation.json", "tiny-random-fixture"
    )
    assert report["overall"]["cases"] == 10
    assert report["overall"]["missing_predictions"] == 0
    assert report["overall"]["schema_compliance"] == 0
    assert report["latency_seconds_mean"] > 0
    with (checkpoint / "optimizer.pt").open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(ValueError, match="integrity"):
        verify_checkpoint(checkpoint, manifest["signature"])


def test_assistant_mask_and_template_special_tokens():
    pytest.importorskip("torch")
    from rsec.train import tiny_model

    _, tokenizer = tiny_model()
    messages = [
        {"role": "user", "content": "Review code."},
        {"role": "assistant", "content": "Use parameterized queries."},
    ]
    result = tokenizer.apply_chat_template(
        messages, tokenize=True, return_dict=True, return_assistant_tokens_mask=True
    )
    assert result["input_ids"][-1] == tokenizer.eos_token_id
    assert 0 < sum(result["assistant_masks"]) < len(result["input_ids"])
