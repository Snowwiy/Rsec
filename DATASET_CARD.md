# Rsec Dataset Pilot · dataset card

Version `pilot-0.2.0`, Candidate schema v2, taxonomy 1.0.0, generated 2026-11-26. Owner: Snowwiy / Rsec. Purpose: controlled bilingual defensive data-engineering and review staging. **Not an expert-approved SFT release. DATASET READINESS: FAIL; TRAINING READINESS: NOT READY.**

## Contents and provenance

64 original synthetic conversations from 32 controlled scenario specifications × EN/ES. Generation method/version/template/original IDs, dates, authorization and validation method are explicit. These are AI-assisted authored templates, not harvested commercial chat/API outputs, real incidents, customer logs or prevalidated cybersecurity knowledge. Source rights for original templates are MIT; linked third-party references retain their own rights. See the source registry and license matrix.

32 separate public development/regression benchmark conversations are not SFT. Three acquired official CVE documents produce reference-index metadata only, with `trusted=false`, SFT false and redistribution false. Those external payloads are not included. Legacy 12 sample conversations are plumbing regressions, not part of this pilot.

| Domain | SFT drafts | Benchmark/regression | Knowledge indexes |
|---|---:|---:|---:|
| Application Security | 8 | 4 | 0 |
| SOC / Detection | 8 | 4 | 0 |
| Vulnerability Management | 8 | 4 | 3 |
| Infrastructure | 8 | 4 | 0 |
| DFIR | 8 | 4 | 0 |
| GRC | 8 | 4 | 0 |
| AI Security | 8 | 4 | 0 |
| Cryptography / Identity | 8 | 4 | 0 |

| Language | SFT drafts | Benchmark/regression | CNA index document language |
|---|---:|---:|---:|
| English | 32 | 16 | 3 |
| Spanish | 32 | 16 | 0 |

The three CNA language labels describe the inspected description field, not a complete linguistic audit of every advisory container. Current pilot difficulty is 32 fundamental/32 intermediate; advanced/expert 0. Some evidence/code is English with Spanish explanation. Python and JavaScript appear in code scenarios. Proposed domain/language/difficulty proportions and the 500–1,000 pilot goal are unmet; low-quality volume was not added.

## Processing and splits

All 64 drafts pass deterministic structural/rights/reference/privacy checks and remain EXPERT REVIEW REQUIRED. Approved 0, rejected 0, quarantined 0. No actual human reviewer ledger exists. Train/eval/test files are absent, counts **0/0/0**. Promotion needs actual hash-bound decisions and three or more approved independent families. Related translations, origin variants, secure/insecure code pairs and detected paraphrases remain grouped; default reserved suites are excluded.

Only conversation `messages` enter tokenization. Evidence/reference text supplied in the user request is part of the task; answer/quality/expected-label metadata is not appended. Assistant JSON includes explicit label/CWE/references/answer fields compatible with the existing scorer. No source code or query is executed.

## Identity and measurements

- Candidate JSONL SHA-256: `459b76721ee5472adfe31ad2409b2f7bd64b86408e0a996df3acdb125b4c2077`.
- Reproduced curation manifest SHA-256: `764a04ba9506a660ef8b254941ad93280c5f737bff6272dd050a1c04951973af`.
- Serialized pilot JSONL: 155,760 UTF-8 bytes.
- Measured official-template tokens: total 16,114; mean 251.78; median 261.5; p90 279; p95 291.2; p99 381.87; max 414.
- Current eligible tokens/epoch: 0. Prospective full-pilot conversation total 16,114 only if every example is later approved unchanged; response-loss tokens are not this total.

[Statistics](data/manifests/pilot_statistics.json) include per-row lengths and tokenizer identities. Whitespace units are separately labeled and never called tokenizer tokens. No GPU memory or training duration was measured.

## Intended use and limitations

Use for review, pipeline regression and authorized future curation. Do not present it as an expert gold benchmark, proof of competence, real forensic evidence or an autonomous operational authority. Technical labels, reference entailment, remediations, bilingual meaning, difficulty and diversity all require qualified review. Small controlled scenarios underrepresent real systems, complex code and advanced reasoning. Privacy, poisoning and lexical filters are incomplete; authenticity is not established by hashes alone.

English/Spanish summary: hay 64 borradores SFT, 32 casos públicos de desarrollo y 3 índices de referencia; **cero ejemplos SFT o gold aprobados por expertos**. No existe un modelo especializado entrenado. Full accounting: [engineering report](DATASET_ENGINEERING_REPORT.md), [quality report](DATASET_QUALITY_REPORT.md).
