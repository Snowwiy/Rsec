# Evaluation contract

The shipped suite consists of ten authored synthetic fixtures across English/Spanish and defensive domains. It contains vulnerable, benign and insufficient-evidence cases. Reference predictions in tests/fixtures are explicitly test expectations, never model outputs. The suite tests plumbing and must not support a production quality claim.

`rsec predict` uses local inference and requests JSON fields id/label/cwe/references/answer. Invalid JSON becomes a schema failure; it is not silently corrected. `rsec evaluate` can score any compatible prediction file, so evaluate base/adapted/merged/GGUF/previous versions under the same benchmark hash and sampling settings. Generation defaults to deterministic decoding in the benchmark runner. No generated code is executed.

Accuracy and exact label match count missing predictions as errors. Per-label precision/recall/F1, macro/micro F1, binary false-positive/negative rates and exact CWE-set match are deterministic. Undefined denominators are null. Schema compliance checks field types; lexical unsupported-reference rate only compares against allowed references. It does not measure semantic hallucinations or every unsupported factual claim. Latency, generation throughput and VRAM are reported only when actually recorded; absent measurements are null.

Baseline comparison requires identical benchmark hashes. The regression gate currently requires nondecreasing overall accuracy and macro F1. This is a minimal mechanical gate; release review must additionally inspect each domain, language, safety behavior, false positives, abstention, evidence quality and programming ability. Controlled dynamic remediation testing and a broad independently curated gold corpus are **NOT IMPLEMENTED** in phase 01. Do not treat classification scores as remediation success.

Test releases remain reserved. Benchmark exclusion uses both content and provenance families. New external suites must be added to preparation explicitly. Human reviewers must establish reference correctness and benchmark licensing, date and version. Test-data improvements are separately versioned from model changes.
