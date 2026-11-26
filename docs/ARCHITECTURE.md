# Architecture

Rsec separates the reusable `src/rsec` Python package from repository configuration and research artifacts. This standard package layout replaces the proposed flat `src/*.py` layout to avoid namespace collisions and provide a normal installed `rsec` executable.

| Module | Responsibility |
|---|---|
| cli / config | Argument parsing, strict typed config and profile overlays |
| download | Reviewed HTTPS/HF acquisition, retry/cache/resume/integrity |
| data / knowledge | Independent SFT vs knowledge ingestion, screening, releases |
| train | TRL SFT, PEFT LoRA/QLoRA, checkpoint recovery and incremental adapters |
| environment | Optional-stack and physical device diagnostics |
| tracking | Local experiment log and immutable model registry |
| predict / evaluate | Offline prediction generation and deterministic scoring |
| artifacts / export / inference | Local model trust checks, artifact lifecycle and runtime adapters |
| interfaces | Future evidence retrieval and local analyzer protocols |
| utils / errors | Bounded reads, hashing, confined paths and safe diagnostics |

No model code or content is executed from datasets. No commercial inference API is required. Training imports are lazy so the CPU curation/CLI path stays small. Model/data/export directories are ignored. No empty directories are created to imply implemented behavior.

## Future local RAG

Fine-tuning teaches behavior and domain capabilities; retrieval supplies changing, attributable evidence. Future ingestion will retain authorized source snapshots with license, freshness, content hash and trust classification. Local embeddings and keyword indexes will support hybrid retrieval, optional reranking and source citations. Index updates should be incremental and atomic. Private corpora require separate access control and must not enter public training releases.

Retrieved text must remain an evidence object, never a higher-priority instruction. Reject tool directives in documents, limit content budgets, preserve trust boundaries and evaluate citation correctness. `Evidence` and `Retriever` in interfaces.py reserve the contract; no database or retrieval implementation is claimed.

## Future SENTRA

`LocalAnalyzer` receives JSON events plus versioned evidence and returns findings, uncertainties, references and remediations. A future authenticated loopback API can expose it. SENTRA remains independent; this phase neither connects to nor modifies it.
