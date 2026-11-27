# Rsec-CyberBench · development 0.1.0

**32 public candidate cases, 15 linked families, 0 expert gold cases.** This is an implemented development/regression scaffold, not a completed independent expert benchmark. No final hidden evaluation case is committed. Gold authorship/review independence remains a Phase 02 exit blocker.

The 32 cases contain 22 development-evaluation and 10 regression cases, 16 EN / 16 ES, four per domain. Draft expected labels: 10 vulnerable, 10 benign, 12 insufficient. SQL parameter-binding SFT scenarios and JavaScript DOM-sink development cases use distinct families. DOM `innerHTML`/`textContent` variants share a regression family, so similar cases cannot cross the development/regression boundary. Translation pairs remain linked.

Capabilities represented include code evidence/CWE, remediation plans, benign false positives, SOC/log context, DFIR custody/timelines, infrastructure effective policy/hardening, GRC scope, AI trust boundaries, identity/integrity, uncertainty and unsupported claims. This does not exhaust all taxonomy subcategories. References are registered and primary pages were inspected; proposed answers have not been independently certified.

## Rubrics and metrics

[Rubrics](../benchmarks/rsec_cyberbench/rubrics.json) define domain-specific criteria weighted 2 or 3 on a human scale 0 unsupported/incorrect, 1 partial, 2 supported with appropriate scope. For each case rating the normalized score is `sum(weight * score) / (2 * sum(weight))`; coverage is separately reported. Multiple reviewer ratings remain separate observations, not automatic consensus. Human disagreement needs adjudication.

`benchmark evaluate` uses the existing deterministic scorer for labels, per-class precision/recall/F1, macro/micro summaries, false positives/negatives, CWE exact match, schema and registered-reference matching. It records category rubric, semantic hallucination and remediation success as null. These are not inferred from matching labels. There are **no real model predictions or performance results** in this phase.

`benchmark rubric-score` aggregates explicit hash-bound **case ratings** and reports coverage. It does not authenticate expert identities or certify gold. Current rating records bind the case/rubric, not an immutable model prediction; therefore use this command for candidate/reference review only. It is not a model-comparison gate until prediction/model identity binding is added. Actual real ratings: zero. Temporary test attestations are hypothetical fixtures only.

For future model comparison export the cases, generate outputs with the same frozen prompts, base revision, tokenizer/template, system message, decoding settings and context, and use existing prediction metadata/comparability gates. Separate base/adapted/merged/quantized runs. Public development cases may inform debugging; they must never be described as blind final performance.

## Future independent final evaluation

Have evaluators who did not author training samples construct and adjudicate final cases using authorized sources. Keep prompts, answers and private review records outside this public repository and outside the tuning loop. Freeze provenance families and evaluation conditions before tuning; release only aggregate approved results. `benchmarks/private/` is ignored and repository checks reject tracked private benchmark paths. This is a protection mechanism, not evidence that a hidden gold set already exists.

English/Spanish review must assess technical meaning, benign lookalikes, uncertainty and unsupported execution/advisory claims. No generated code runs on the host. See [contamination policy](BENCHMARK_CONTAMINATION_POLICY.md) and [benchmark report](../BENCHMARK_REPORT.md).
