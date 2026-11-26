# Dataset sources · inspected 2026-11-26

**20 external source locations verified for existence, plus 2 internal fixture sources = 22 registered sources.** Existence is not SFT authorization, complete download, technical validation or verification of every upstream item. No external source is enabled for SFT. The registry records URLs, responsible organization, versions, nullable publication/acquisition dates, rights conditions, restrictions, formats, domains, estimated quality, review method and snapshot hashes when available. Unknown publication dates are retained as null, never invented.

| Source | Organization | Revision / version | Published | Acquired | Format | Status |
|---|---|---|---|---|---|---|
| [rsec-pilot](https://github.com/Snowwiy/Rsec) | Rsec | generator-1.0.0 | Unknown / rolling | Not acquired | Python templates | APPROVED |
| [rsec-cyberbench](https://github.com/Snowwiy/Rsec) | Rsec | cyberbench-0.1.0 | Unknown / rolling | Not acquired | JSONL | APPROVED |
| [nvd](https://nvd.nist.gov/general) | NIST | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | API JSON | REVIEW REQUIRED |
| [cve-program](https://github.com/CVEProject/cvelistV5) | CVE Program / MITRE and CNAs | 1bb6bf3e2a5dac32d643b091c6f4d9ed6026653e | Unknown / rolling | 2026-11-26 | CVE JSON 5 | APPROVED |
| [cwe](https://cwe.mitre.org/) | MITRE | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | HTML | REVIEW REQUIRED |
| [attack](https://attack.mitre.org/) | MITRE | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | STIX JSON | REVIEW REQUIRED |
| [cisa-kev](https://github.com/cisagov/kev-data) | CISA | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | JSON/CSV | REVIEW REQUIRED |
| [owasp-top10](https://owasp.org/projects/top-ten) | OWASP | 2025 | Unknown / rolling | Not acquired | HTML/Markdown | REVIEW REQUIRED |
| [osv](https://google.github.io/osv.dev/data/) | Google / contributing ecosystems | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | OSV JSON | REVIEW REQUIRED |
| [github-advisories](https://github.com/github/advisory-database) | GitHub and contributors | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | OSV JSON | REVIEW REQUIRED |
| [python-docs](https://docs.python.org/3/) | Python Software Foundation | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | HTML | REVIEW REQUIRED |
| [microsoft-learn](https://learn.microsoft.com/) | Microsoft | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | HTML | REVIEW REQUIRED |
| [kubernetes-docs](https://kubernetes.io/docs/home/) | Kubernetes contributors | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | HTML | REVIEW REQUIRED |
| [nist-csf](https://www.nist.gov/cyberframework) | NIST | CSF 2.0; publication-level pin pending | Unknown / rolling | Not acquired | HTML/PDF | REVIEW REQUIRED |
| [iso-27001](https://www.iso.org/standard/27001) | ISO / IEC | ISO/IEC 27001:2022 | Unknown / rolling | Not acquired | Commercial PDF | RESTRICTED |
| [cis-controls](https://www.cisecurity.org/controls) | Center for Internet Security | v8.1 (publisher page) | Unknown / rolling | Not acquired | HTML/PDF | REVIEW REQUIRED |
| [sigma-rules](https://github.com/SigmaHQ/sigma) | SigmaHQ / individual rule authors | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | YAML | REVIEW REQUIRED |
| [yara-rules](https://github.com/Yara-Rules/rules) | Yara-Rules contributors | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | YARA | REVIEW REQUIRED |
| [primevul](https://github.com/DLVulDet/PrimeVul) | DLVulDet research authors | PrimeVul-v0.1 | Unknown / rolling | Not acquired | JSONL | REVIEW REQUIRED |
| [hf-primevul](https://huggingface.co/datasets/colin/PrimeVul) | Mirror maintainer; upstream DLVulDet | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | JSON/Parquet | REVIEW REQUIRED |
| [hf-cyberseceval](https://huggingface.co/datasets/walledai/CyberSecEval) | Walled AI mirror / upstream Meta | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | Parquet | REVIEW REQUIRED |
| [hf-cybernative](https://huggingface.co/datasets/CyberNative/Code_Vulnerability_Security_DPO) | CyberNative | live site; reviewed 2026-11-26 | Unknown / rolling | Not acquired | JSON DPO | REVIEW REQUIRED |

## Acquisition actually performed

Only three official CVEProject/cvelistV5 documents were acquired, at commit `1bb6bf3e2a5dac32d643b091c6f4d9ed6026653e`: CVE-2021-44228, CVE-2022-22965 and CVE-2023-34362, totalling **66,108 bytes**. The authorized GitHub connector fetched their bytes; local `git hash-object` matched the official blob IDs. SHA-256 was then derived locally and frozen in the registry/config. These are not publisher-signed SHA-256 checksums. Individual hashes/blob IDs/publication dates are in [acquisition evidence](../data/manifests/acquisition_evidence.json).

The native HTTPS path initially failed with DNS `gaierror` in this environment. Subsequent `data download --registered` runs verified the connector-populated cache with no DNS requests. Unit tests exercise network failures, bounds and hashes; native live download success is not claimed. On a normally networked machine, a missing cache uses the bounded HTTPS downloader. CISA's primary catalog/license endpoint returned 403; its official GitHub mirror establishes existence, while its ingestion/rights remain blocked for review.

Raw third-party payloads remain ignored under `data/raw/cve/`; none are redistributed by this PR. The three derived reference-index rows remain ignored under `data/interim/`, with no conversations or SFT eligibility. Complete CNA interpretation, affected-version reasoning and record-level expert validation remain pending. Publisher dates are not acquisition timestamps.

## Scope of source review

The CVE Program terms permit the bounded reference use recorded by policy; this registry intentionally enables no CVE training or public payload redistribution. Python placeholders and CWE-79/CWE-89 official reference pages were inspected as references for controlled examples. Linking a valid page does not prove that every candidate answer is correct. Dataset cards and repository license labels do not establish rights for all upstream code or labels.

OWASP 2025, CIS v8.1 and other rolling documentation are inventoried at the inspected revision/date. No ISO standard text was copied. OSV includes source-specific upstream restrictions, including noncommercial/no-derivative terms; it is not uniformly permissive. Sigma's Detection Rule License 1.1 must be reviewed separately from its engine/tools. YARA rule rights differ from the YARA engine license. Hugging Face entries are real mirrors/cards, not claims of canonical ownership or validated gold. PrimeVul upstream code rights and split contamination require item-level review.

## Reproduce and extend

```bash
rsec data sources
rsec data download --registered
rsec data normalize-cve --input data/raw/cve/CVE-2021-44228.json data/raw/cve/CVE-2022-22965.json data/raw/cve/CVE-2023-34362.json --output data/interim/cve-reference-new.jsonl
```

The legacy `sources: []` is deliberately preserved: plain `data download` does not silently acquire the new catalog. `registered_sources` selects only the three pinned CVE snapshots. Approval is scoped by intended use and separate booleans. Add an immutable snapshot, source-specific terms decision, exact reference revisions and an explicit schema adapter before expanding acquisition. No paid API or bulk acquisition is required.

English summary: the inventory establishes source existence and a conservative policy; it is not an approved external SFT corpus. See [license matrix](LICENSE_MATRIX.md) for separate permissions and the machine-readable [registry](../data/manifests/source_registry.json) for full conditions.
