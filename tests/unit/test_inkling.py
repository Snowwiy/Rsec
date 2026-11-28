from pathlib import Path
from runpy import run_path

import pytest

from rsec import inkling
from rsec.errors import RsecError


def test_inference_aggregates_global_and_sliding_window_kv_buffers():
    script = Path(__file__).parents[2] / "scripts" / "inkling_inference_probe.py"
    parse = run_path(script)["kv_allocations"]
    log = (
        "llama_kv_cache: CUDA0 KV buffer size = 272.00 MiB\n"
        "llama_kv_cache: CUDA1 KV buffer size = 272.00 MiB\n"
        "llama_kv_cache: CUDA0 KV buffer size = 73.31 MiB\n"
        "llama_kv_cache: CUDA1 KV buffer size = 54.19 MiB\n"
    )
    assert parse(log) == {"CUDA0": 345.31, "CUDA1": 326.19}


def configuration():
    return {
        "model_type": inkling.MODEL_TYPE,
        "architectures": [inkling.ARCHITECTURE],
        "quantization_config": {
            "quant_method": "bitsandbytes",
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_use_double_quant": True,
            "load_in_4bit": True,
            "llm_int8_skip_modules": sorted(inkling.PRESERVE_16_BIT),
        },
    }


def test_inkling_requires_native_architecture_and_preserved_loop_gates():
    config = configuration()
    inkling.validate_quantization(config)
    config["quantization_config"]["llm_int8_skip_modules"].remove("q_message_gate.down_proj")
    with pytest.raises(RsecError, match="preserve the message gates"):
        inkling.validate_quantization(config)
    config = configuration()
    config["auto_map"] = {"AutoModel": "remote.Code"}
    with pytest.raises(RsecError, match="installed Transformers"):
        inkling.validate_quantization(config)


def test_inkling_rejects_missing_experts_quantized_gate_and_external_shards():
    weight_map = {}
    for i, key in enumerate(sorted(inkling.EXPERT_PROJECTIONS)):
        name = tuple(inkling.SHARDS)[i % 4]
        for suffix in ("", ".nested_absmax", ".quant_state.bitsandbytes__nf4"):
            weight_map[key + suffix] = name
    weight_map.update(dict.fromkeys(inkling.STORED_GATE_DTYPES, name))
    inkling.validate_index(weight_map)
    tensor, original = next(iter(weight_map.items()))
    weight_map[tensor] = "../unexpected.safetensors"
    with pytest.raises(RsecError, match="four fixed local shards"):
        inkling.validate_index(weight_map)
    weight_map[tensor] = original
    weight_map["model.q_message_gate.down_proj.weight.quant_state.bitsandbytes__nf4"] = original
    with pytest.raises(RsecError, match="quantized loop message gate"):
        inkling.validate_index(weight_map)
    weight_map.pop("model.q_message_gate.down_proj.weight.quant_state.bitsandbytes__nf4")
    weight_map.pop(next(iter(inkling.STORED_GATE_DTYPES)))
    with pytest.raises(RsecError, match="Missing one or more loop message gate"):
        inkling.validate_index(weight_map)
    weight_map.pop(tensor)
    with pytest.raises(RsecError, match="double-NF4 metadata"):
        inkling.validate_index(weight_map)


def test_inkling_smoke_rejects_ddp_and_unbounded_steps_before_loading(tmp_path, monkeypatch):
    monkeypatch.setenv("WORLD_SIZE", "2")
    with pytest.raises(RsecError, match="single-process layer split"):
        inkling.smoke(tmp_path / "missing", tmp_path / "output")
    with pytest.raises(RsecError, match="four steps"):
        inkling.smoke(tmp_path / "missing", tmp_path / "output", steps=5)
    assert not (tmp_path / "output").exists()
