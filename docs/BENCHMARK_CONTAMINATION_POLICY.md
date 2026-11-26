# Benchmark contamination policy

Training, eval, test, external benchmarks and regression cases have different purposes. Reserved cases must not enter SFT or replay. Public does not mean training-authorized. Current default reservations contain **42 cases: 32 new public candidates plus 10 legacy fixtures**; new pilot candidates linked to these reservations: **0** under the implemented checks.

## Detection and split rules

- Exact normalized conversation hashes reject duplicate conversations even with changed metadata.
- Origin IDs, declared family IDs, explicit translation/original IDs (including forward references) and document lineage connect variants. Use repository/commit/file/CVE-document origins when importing real data. A broad CWE class alone is not necessarily one example family; link concrete source/patch/advisory variants.
- Whitespace/comment-normalized code fingerprints connect code variants. This detects some reformatting, not arbitrary semantic equivalence.
- Inverted-index lexical shingles and Jaccard overlap detect close paraphrases. Approximate deduplication additionally requires matching language/evidence/target so distinct cases are not removed merely for common boilerplate.
- Candidate/reserved linkage is checked before SFT promotion and repeated during bundle/SFT validation. Questions remain reserved even if an answer or declared family changes.
- Entire connected families stay in one split or benchmark partition. EN/ES variants and secure/insecure variants of the same code scenario remain together.

No universal embedding, semantic, multilingual paraphrase or undeclared translation detector is implemented. Zero detected overlap does not establish independence of authorship, hidden exposure or technical content. The same controlled generator authored the current public drafts and pilot; an independent expert final benchmark remains missing.

## Freeze and future imports

Record source URLs/revisions, upstream split, repository/document identifiers, original IDs, translation links, hashes and acquisition decisions. Reserve external official benchmark families before selecting training samples. Mirrored PrimeVul/CyberSecEval or other benchmark rows must not be repurposed as SFT merely because their license is permissive. Review their upstream split contamination and rights.

The API caller of `curate` must pass reservations explicitly; CLI defaults include both tracked suites. Missing reservation input is not proof that no external benchmark exists. Keep final evaluator-held data and review identities outside Git. Do not redistribute hidden suites in a curation bundle intended for publication: processed bundles are ignored by default and require separate disclosure review.

For future releases maintain a frozen external test lineage. Mixing new data and replay then re-splitting can move groups; it is not a valid replacement for unchanged longitudinal tests. Review all cross-shard matches before global promotion. The 10,000-row and 200,000-comparison budgets fail closed; budget exhaustion cannot be accepted as a clean contamination report.

## Reservas y similitud en Fase 02-B

Las reservas CLI vigentes suman 54 casos e incluyen CodeBench, CyberBench y el conjunto legacy. Los futuros casos gold se mantienen fuera de Git y se pasan explícitamente a las operaciones autorizadas. `rsec data semantic-check` agrega señales de similitud coseno desde un JSON de vectores locales con claves `digest(prompt_text(row))`, identificador, revisión, dimensión y matriz. No altera la curación automáticamente. Conserva el método/modelo, reporta coincidencias ambiguas y revisa cada enlace.

La ficha de [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) documenta MIT, 384 dimensiones, soporte multilingüe y la preparación de entradas. Es un candidato para producir vectores fuera de core en un entorno aislado con revisión fijada. Consulta tamaño de los pesos Safetensors en su repositorio y mide RAM/VRAM localmente antes de usarlo. En esta fase se probaron vectores sintéticos; no se descargó ni ejecutó E5 ni se ha calibrado umbral EN/ES.
