# Dataset quality standard

The pipeline distinguishes **mechanical validity** from **technical correctness**. Current candidates have automated checks but no real expert approvals. No numeric score bypasses missing rights, invalid provenance, privacy failures, contamination or human review.

## Gates

1. Strict v2 schema, actual boolean flags, alternating roles, complete assistant targets, bounded fields and known taxonomy values.
2. Known source, exact registered revision/reference identity and permitted use. License unknown or purpose disallowed means exclusion. References are matched to inspected source records, not fetched as executable input.
3. NFKC normalization; empty/oversized/repeated content checks; JSON target/label consistency; weak language/domain hints. Unsupported asserted CVE/CWE identifiers and tool-execution claims are flagged. Mentioning an ambiguous identifier as a question is not accepted as a verified fact.
4. Secret/PII and poisoning/instruction heuristics across content and metadata. Anonymization is explicit; it resets review and requires human inspection. Structured dates and CVE/CWE identifiers are excluded from phone-number matching, while unsupported asserted identifiers remain separately gated.
5. Exact/approximate duplicates, provenance/translation/code links and reserved benchmark checks. Rejected/quarantined rows retain hash and reasons, not full private text.
6. Separate hash-bound human review for technical correctness, evidence, references, privacy and rights; remediation tasks require the remediation check. Advanced/expert need two distinct reviewers.

## Review states

| State | Meaning |
|---|---|
| GENERATED | Authored/transformed candidate; no correctness approval |
| AUTOMATED VALIDATION PASSED | Mechanical checks passed; still no expert truth |
| EXPERT REVIEW REQUIRED | Valid candidate pending human technical checks |
| EXPERT REVIEWED | Separate valid human-attested decisions for this content and registry hash |
| REJECTED | Invalid or explicitly rejected; no SFT eligibility |

The incoming JSON status cannot authorize itself. Valid drafts transition through automated checks to EXPERT REVIEW REQUIRED; supplied review flags are reset without a ledger. The real pilot has **64 expert-review-required candidates and zero expert-reviewed rows**. Review packet creation always reports zero approvals.

## Score and evidence

Per-record process scores cover verifiable dimensions such as provenance, structural integrity, reference registration, evidence presence, relevance hints and clarity bounds. `technical_correctness` and `remediation_verified` remain **null** until actual review. Evidence presence is not causal adequacy, registered references are not semantic entailment, and a high mechanical score is not probability of correctness. Diversity is reported by domain/language/difficulty/families, not invented as an individual truth score.

The same controlled generator authored training and public benchmark drafts with different scenario specifications. That gives known-family separation, not independent expert authorship. No patch, Sigma rule, YARA rule, log query or generated code is executed. Dynamic remediation validation requires a future isolated authorized runner.

## Safe failure and limits

Schema/global file errors, exceeded budgets, unsafe paths, symlinks, hash/inventory changes and malformed attestations fail closed. Individual quality failures go to metadata-only quarantine. Unsigned inventories cannot protect against an attacker replacing the registry, records, decisions and manifest together. Human IDs/attestations are operator assertions, not authenticated identities.

Regex filters miss paraphrases, encoded/multilingual poisoning, some private data and technical inaccuracies; they can also reject legitimate examples. Lexical similarity cannot certify semantic independence. Manual privacy, licensing, bilingual and expert review remain mandatory. Current rejection/quarantine counts are zero in the small actual corpus; that is not evidence of perfect detection. Adversarial failures in tests are never counted as corpus examples.
