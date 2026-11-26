"""Offline local inference with a uniform, future API-compatible response envelope."""

import json
import time
import urllib.request
from pathlib import Path

from rsec.errors import RsecError
from rsec.utils import bounded_read


def infer(
    model,
    prompt,
    backend="transformers",
    adapter=None,
    system=None,
    temperature=0.2,
    top_p=0.9,
    top_k=40,
    context=2048,
    max_tokens=256,
    gpu_layers=0,
    tensor_split=None,
):
    if not (
        0 <= temperature <= 2
        and 0 < top_p <= 1
        and top_k >= 0
        and 1 <= max_tokens < context <= 131072
    ):
        raise RsecError("Invalid generation limits or sampling parameters")
    if len(prompt) > 100000:
        raise RsecError("Prompt exceeds input budget")
    system_text = (
        bounded_read(system, 32768)
        if system
        else "You are Rsec, a defensive cybersecurity assistant. Distinguish evidence from hypotheses and state uncertainty."
    )
    messages = [{"role": "system", "content": system_text}, {"role": "user", "content": prompt}]
    start = time.perf_counter()
    if backend == "transformers":
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        path = str(Path(model).resolve(strict=True))
        tokenizer = AutoTokenizer.from_pretrained(
            path, local_files_only=True, trust_remote_code=False
        )
        loaded = AutoModelForCausalLM.from_pretrained(
            path,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            dtype="auto",
        )
        if adapter:
            from peft import PeftModel

            loaded = PeftModel.from_pretrained(
                loaded, str(Path(adapter).resolve(strict=True)), local_files_only=True
            )
        device = "cuda" if torch.cuda.is_available() else "cpu"
        loaded.to(device).eval()
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            return_token_type_ids=False,
        ).to(device)
        if inputs["input_ids"].shape[-1] + max_tokens > context:
            raise RsecError("Prompt plus generation exceeds context budget")
        generation_start = time.perf_counter()
        kwargs = {
            "max_new_tokens": max_tokens,
            "do_sample": temperature > 0,
            "pad_token_id": tokenizer.pad_token_id
            if tokenizer.pad_token_id is not None
            else tokenizer.eos_token_id,
        }
        if temperature > 0:
            kwargs.update(temperature=temperature, top_p=top_p, top_k=top_k)
        with torch.inference_mode():
            outputs = loaded.generate(**inputs, **kwargs)
        if device == "cuda":
            torch.cuda.synchronize()
        tokens = outputs[0, inputs["input_ids"].shape[-1] :]
        answer = tokenizer.decode(tokens, skip_special_tokens=True)
        count = len(tokens)
        generation_time = time.perf_counter() - generation_start
        vram = torch.cuda.memory_allocated() if device == "cuda" else None
    elif backend == "llama-cpp":
        from llama_cpp import Llama

        loaded = Llama(
            model_path=str(Path(model).resolve(strict=True)),
            n_ctx=context,
            n_gpu_layers=gpu_layers,
            tensor_split=tensor_split,
            verbose=False,
        )
        generation_start = time.perf_counter()
        result = loaded.create_chat_completion(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_tokens=max_tokens,
        )
        answer = result["choices"][0]["message"]["content"]
        count = result["usage"]["completion_tokens"]
        generation_time = time.perf_counter() - generation_start
        vram = None
    elif backend == "ollama":
        # Fixed loopback endpoint; never calls pull or a cloud provider.
        if "cloud" in model.lower():
            raise RsecError("Cloud-tagged Ollama models are outside the local-only backend")
        body = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "num_ctx": context,
                "num_predict": max_tokens,
            },
        }
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
            request, timeout=600
        ) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise RsecError("Ollama response exceeds output budget")
        result = json.loads(raw)
        answer = result["message"]["content"]
        count = result.get("eval_count")
        generation_time = result.get("eval_duration", 0) / 1e9
        vram = None
    else:
        raise RsecError("Unknown local inference backend")
    return {
        "model": model,
        "backend": backend,
        "answer": answer,
        "latency_seconds": time.perf_counter() - start,
        "generation_seconds": generation_time,
        "generated_tokens": count,
        "tokens_per_second": count / generation_time
        if count is not None and generation_time
        else None,
        "vram_bytes": vram,
    }
