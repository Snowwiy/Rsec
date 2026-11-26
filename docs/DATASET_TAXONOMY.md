# Dataset taxonomy · 1.0.0

The authoritative [configuration](../configs/taxonomy.json) defines eight domains, their allowed subcategories, 18 task types, 13 programming languages, English/Spanish and four difficulty levels. Every Candidate v2 declares its taxonomy version. Unknown domain/subcategory/task/language/difficulty combinations are rejected. Correct categorization is still a human technical judgment; schema membership and keyword hints do not prove it.

| Domain | Proposed share | Current SFT candidates | Public benchmark/regression |
|---|---:|---:|---:|
| Application Security | 25% | 8 | 4 |
| SOC / Detection Engineering | 20% | 8 | 4 |
| Vulnerability Management | 15% | 8 | 4 |
| Infrastructure Security | 15% | 8 | 4 |
| DFIR | 10% | 8 | 4 |
| GRC | 5% | 8 | 4 |
| AI Security | 5% | 8 | 4 |
| Cryptography / Identity | 5% | 8 | 4 |

The three external reference-index rows additionally belong to Vulnerability Management, not SFT or the benchmark. Current pilot breadth is deliberately equal across domains. It is not the proposed training distribution and does not imply exhaustive subcategory coverage.

Application Security includes code audit/secure coding, authentication/authorization/API, dependencies, remediation and SDLC. SOC covers triage/logs/rules/hunting/false positives/telemetry. Vulnerability Management includes advisories, CVE/CWE/CVSS, exposure, priority and version matching. Infrastructure includes Linux/Windows/AD/network/cloud/containers/hardening. DFIR covers preservation/timelines/response/artifacts/reporting. GRC covers risk/assets/controls/audit/reporting without reproducing protected standards. AI Security covers injection/RAG/agents/poisoning/model supply chain. Identity covers TLS/PKI/hashing/keys/MFA/IAM/OAuth/OIDC/secrets.

## Language, task and difficulty

Targets are EN 65% / ES 35%; actual pilot is **32 EN / 32 ES**, benchmark **16 EN / 16 ES**. Original evidence may be English while the explanation is Spanish. Explicit translation/original IDs keep versions in one family; this does not automatically detect all undeclared translations. Domain terminology and technical meaning require bilingual review.

Difficulty targets fundamental/intermediate/advanced/expert are 15/35/35/15%. Actual pilot: **32 fundamental, 32 intermediate, 0 advanced, 0 expert**. Difficulty is a draft label based on required reasoning, not response length. Advanced/expert promotion requires two distinct human reviewers. Do not manufacture advanced examples by making answers longer.

Task types include grounded QA, code audits and safe/unsafe comparisons, vulnerability/CWE classification, logs/SOC/configuration, remediation/priority, false-positive validation, advisories/reports, uncertainty, incorrect-claim correction, contradictory evidence, structured JSON and useful multi-turn conversations. The taxonomy supports all 13 requested languages; **current code fixtures use Python and JavaScript only**. Coverage of a taxonomy entry is not implied by its presence in configuration.

Future taxonomy changes require a new version, explicit migration and a fresh immutable curation bundle. Quality, rights and family independence take precedence over percentages or the proposed pilot size of 500–1,000.
