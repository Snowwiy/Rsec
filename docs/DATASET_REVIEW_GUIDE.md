# Human dataset review guide

A mechanical pass, generated answer, review packet or local operator flag is not expert review. **No real review attestations were submitted in Phase 02.** Candidates must remain pending until actual qualified people inspect them. Do not copy test-only fake attestations into production data.

## Reproduce the staging and packet

Run from checkout root, using a new immutable destination:

```bash
rsec data curate --input data/pilot/candidates.jsonl --output data/processed/review-pilot --version pilot-0.2.0
rsec data validate data/processed/review-pilot
rsec data quality data/processed/review-pilot
rsec data quarantine data/processed/review-pilot
rsec data version data/processed/review-pilot
rsec data review data/processed/review-pilot --output reports/review-packet.json
```

Inspect `records.jsonl`, `quality_observations.jsonl`, the source registry/license matrix, references, evidence and translations. Packet creation provides content/registry hashes and required reviewers but approves nothing. Use an opaque reviewer identifier; keep personal identity/qualifications and sensitive notes in an authorized private location.

For each candidate check causal technical correctness, source/revision, reference entailment, privacy, rights and defensive usefulness. For remediation inspect whether the proposed change addresses the cause and specify safe negative/regression checks; never claim a command executed without evidence. Check uncertainty, benign lookalikes, contradictory evidence, language meaning and declared difficulty. Do not reproduce protected standards. Advanced/expert require at least two distinct reviewers; one reject blocks promotion.

## Decision ledger

Each JSONL decision follows `rsec.datasets.review.Decision`:

```json
{
  "record_id": "<actual-record-id>",
  "record_hash": "<64-hex-content-hash-from-packet>",
  "registry_hash": "<64-hex-registry-hash-from-packet>",
  "reviewer_id": "reviewer-opaque-01",
  "decision": "approve",
  "human_attested": true,
  "checks": ["technical_correctness", "evidence", "references", "privacy", "rights"],
  "reviewed_at": "2026-11-26"
}
```

This is a **schema illustration with invalid placeholders**, not an actual approval. Use the real review date and add `remediation` for remediation tasks. Set decision `reject` when appropriate. Review the exact current content; edits, anonymization or policy changes require fresh hashes/review. Reviewer identity and expertise are not cryptographically authenticated by this tool; the operator must verify authority outside it.

Store private ledgers under ignored `data/reviews/` or another authorized location. Then create a new bundle, never edit the old release:

```bash
rsec data curate --input data/pilot/candidates.jsonl --decisions data/reviews/decisions.jsonl --output data/processed/reviewed-pilot --version pilot-reviewed-1
rsec data validate data/processed/reviewed-pilot
rsec data split data/processed/reviewed-pilot --output data/processed/reviewed-sft
rsec data validate data/processed/reviewed-sft
```

These last commands are a future operator procedure; no real decisions file exists now. With zero eligible rows `data split` exits 2. With fewer than three approved independent families promotion stays blocked. The SFT bridge preserves the complete review ledger and policies locally, so inspect disclosure before sharing any generated artifact. Do not publish reviewer personal data or private benchmark content.

Only `messages` are tokenized. Current 64 candidates are not training-approved, despite source template rights. Keep final gold review independent of training curation and use BENCHMARK_DESIGN.md for the additional rubric/identity limitations.

## Fase 02-B

El flujo actual de interfaz local, decisiones firmadas y exportación se documenta en [la guía vigente](../DATASET_REVIEW_GUIDE.md).
