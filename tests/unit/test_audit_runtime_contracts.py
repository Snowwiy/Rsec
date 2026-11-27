"""Optional runtime API contracts use fakes and do not validate runtime execution."""

import io
import json
import sys
import types

import pytest

from rsec.errors import RsecError
from rsec.inference import LocalOnly, infer


@pytest.mark.parametrize(
    "options",
    [
        {"temperature": -1},
        {"top_p": 0},
        {"top_k": -1},
        {"max_tokens": 2048},
        {"gpu_layers": -2},
        {"tensor_split": [-1, 1]},
        {"tensor_split": [float("nan")]},
        {"tensor_split": [0, 0]},
        {"tensor_split": [1]},
        {"adapter": "ignored"},
    ],
)
def test_generation_contract_rejects_bad_inputs(options):
    with pytest.raises(RsecError):
        infer("fixture", "text", backend="ollama", **options)


def test_prompt_limits_unknown_backend_and_local_redirect():
    with pytest.raises(RsecError, match="budget"):
        infer("fixture", "x" * 100001)
    with pytest.raises(RsecError, match="Unknown"):
        infer("fixture", "text", backend="unknown")
    with pytest.raises(RsecError, match="redirects"):
        LocalOnly().redirect_request(None)
    with pytest.raises(RsecError, match="Cloud"):
        infer("cloud-model", "text", backend="ollama")


def test_ollama_loopback_no_proxy_and_response_limits(monkeypatch):
    import rsec.inference as module

    payload = {
        "message": {"content": "fixture answer"},
        "eval_count": 4,
        "eval_duration": 2_000_000_000,
    }

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "http://127.0.0.1:11434/api/chat"
            assert json.loads(request.data)["stream"] is False
            return io.BytesIO(json.dumps(payload).encode())

    def build(*handlers):
        assert handlers[0].proxies == {}
        assert isinstance(handlers[1], LocalOnly)
        return Opener()

    monkeypatch.setattr(module.urllib.request, "build_opener", build)
    result = infer("local-fixture", "text", backend="ollama")
    assert result["answer"] == "fixture answer" and result["tokens_per_second"] == 2
    payload["message"]["content"] = "x" * (4 * 1024 * 1024)
    with pytest.raises(RsecError, match="budget"):
        infer("local-fixture", "text", backend="ollama")


def test_llama_binding_api_tensor_distribution(monkeypatch, tmp_path):
    class FakeLlama:
        metadata = {"tokenizer.chat_template": "official-template-fixture"}

        def __init__(self, **kwargs):
            assert kwargs["tensor_split"] == [0.6, 0.4] and kwargs["n_gpu_layers"] == -1

        def create_chat_completion(self, **kwargs):
            assert kwargs["messages"][0]["role"] == "system"
            return {
                "choices": [{"message": {"content": "fixture"}}],
                "usage": {"completion_tokens": 2},
            }

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=FakeLlama))
    path = tmp_path / "fixture.gguf"
    path.write_bytes(b"GGUF fixture only")
    result = infer(path, "text", backend="llama-cpp", gpu_layers=-1, tensor_split=[0.6, 0.4])
    assert result["answer"] == "fixture" and result["chat_template_hash"]
