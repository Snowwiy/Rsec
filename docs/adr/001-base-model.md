# ADR 001 — Preliminary base model and licensing

Date: 2026-11-26. Status: accepted for infrastructure implementation; **GPU VALIDATION PENDING** for specialization.

Choose Qwen/Qwen2.5-Coder-7B-Instruct at c03e6d358207e414f1eca0bb1891e29f1db0e242 (official Hub API observed on the date above). The model is instruction-tuned, code-oriented and has a native Transformers Qwen2 architecture and tokenizer template. Its Apache-2.0 license permits derivative distribution subject to its obligations; redistribution still requires preserving applicable notices/license and reviewing the adapter/base combination. This does not relicense Rsec's existing MIT code or any datasets.

Alternatives reviewed: meta-llama/Llama-3.1-8B-Instruct uses the custom Llama 3.1 license; mistralai/Mistral-Nemo-Instruct-2407 is a larger Apache-2.0 multilingual/code candidate; Qwen/Qwen3-Coder-30B-A3B-Instruct is a newer Apache-2.0 MoE candidate with substantially larger resident weights despite fewer active parameters. The latter two are not assumed trainable on a 12 GB card. No choice is based solely on release date.

Publisher coding/general/multilingual benchmarks support consideration, not a cybersecurity ranking. Different publisher benchmark setups are not directly comparable, and no independent Spanish/English Rsec base evaluation has been run. The model choice balances familiar architecture/tooling, code specialization, derivative rights and a conservative first target. The owner's bilingual and cybersecurity quality requirements remain empirical acceptance gates for phase 03.

Transformers/PEFT/TRL support the architecture and QLoRA integration. Unsloth documents Qwen training, but Rsec's optional backend has not been exercised. llama.cpp's Qwen2 conversion and Ollama's GGUF import establish a format path, not proof that Rsec's future adapter exports preserve quality. Hardware memory, template handling and all final exports must be measured. No promise is made that 7B SFT at context 2048 fits the RTX 4070 until a physical test confirms it.

Primary sources consulted:
- https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
- https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct/blob/main/LICENSE
- https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
- https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407
- https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- https://huggingface.co/docs/trl/sft_trainer
- https://huggingface.co/docs/bitsandbytes/fsdp_qlora
- https://huggingface.co/docs/peft/accelerate/fsdp
- https://unsloth.ai/docs/basics/multi-gpu-training-with-unsloth
- https://github.com/ggml-org/llama.cpp/blob/master/convert_hf_to_gguf.py
- https://docs.ollama.com/import

Version-specific TRL v1.19.0 documentation was not retrievable through the search tool, so installed signatures/source and real CPU integration tests establish API behavior. Upgrading initial vulnerable versions required using warmup_steps as a fractional warmup and activation_checkpointing; removed save_safetensors training options are not passed.
