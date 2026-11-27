# Source license and authorization matrix

Inspected 2026-11-26. These are **pipeline permissions for this release**, not an assertion that all disabled uses are legally prohibited. `false` means not authorized by this local policy. Public access is independent of download, training and redistribution. **APPROVED is scoped to the listed intended use, not expert correctness of records.** No external source is approved for SFT.

| Source | Public | Download enabled | Training enabled | Redistribution enabled | Policy | License / terms |
|---|---|---|---|---|---|---|
| rsec-pilot | Yes | No | Yes | Yes | APPROVED | [MIT](https://github.com/Snowwiy/Rsec/blob/main/LICENSE) |
| rsec-cyberbench | Yes | No | No | Yes | APPROVED | [MIT](https://github.com/Snowwiy/Rsec/blob/main/LICENSE) |
| nvd | Yes | No | No | No | REVIEW REQUIRED | [NIST data statement; third-party materials excluded](https://www.nist.gov/open/license) |
| cve-program | Yes | Yes | No | No | APPROVED | [LicenseRef-CVE-Terms](https://cveproject.github.io/docs/terms.html) |
| cwe | Yes | No | No | No | REVIEW REQUIRED | [LicenseRef-CWE-Terms](https://cwe.mitre.org/about/termsofuse.html) |
| attack | Yes | No | No | No | REVIEW REQUIRED | [LicenseRef-ATTACK-Terms](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/) |
| cisa-kev | Yes | No | No | No | REVIEW REQUIRED | [Unverified primary license access (403)](https://www.cisa.gov/sites/default/files/licenses/kev/license.txt) |
| owasp-top10 | Yes | No | No | No | REVIEW REQUIRED | [Project-specific attribution/share-alike review required](https://github.com/OWASP/Top10) |
| osv | Yes | No | No | No | REVIEW REQUIRED | [Mixed per upstream source](https://google.github.io/osv.dev/data/) |
| github-advisories | Yes | No | No | No | REVIEW REQUIRED | [CC-BY-4.0](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features) |
| python-docs | Yes | No | No | No | REVIEW REQUIRED | [PSF-2.0 and documentation/code-example conditions](https://docs.python.org/3/license.html) |
| microsoft-learn | Yes | No | No | No | REVIEW REQUIRED | [Per-page/document license review](https://learn.microsoft.com/en-us/legal/termsofuse) |
| kubernetes-docs | Yes | No | No | No | REVIEW REQUIRED | [Site documentation license; per-page review pending](https://kubernetes.io/docs/home/) |
| nist-csf | Yes | No | No | No | REVIEW REQUIRED | [NIST technical publication statement](https://www.nist.gov/open/license) |
| iso-27001 | Yes | No | No | No | RESTRICTED | [Commercial protected standard](https://www.iso.org/standard/27001) |
| cis-controls | Yes | No | No | No | REVIEW REQUIRED | [CIS terms; exact artifact review pending](https://www.cisecurity.org/controls) |
| sigma-rules | Yes | No | No | No | REVIEW REQUIRED | [DRL-1.1](https://github.com/SigmaHQ/Detection-Rule-License) |
| yara-rules | Yes | No | No | No | REVIEW REQUIRED | [Repository license plus per-rule provenance review](https://github.com/Yara-Rules/rules/blob/master/LICENSE) |
| primevul | Yes | No | No | No | REVIEW REQUIRED | [Dataset/project and underlying repositories require review](https://github.com/DLVulDet/PrimeVul) |
| hf-primevul | Yes | No | No | No | REVIEW REQUIRED | [Card labels MIT; upstream rights not established](https://huggingface.co/datasets/colin/PrimeVul) |
| hf-cyberseceval | Yes | No | No | No | REVIEW REQUIRED | [Card labels MIT; inherited code/provenance review](https://huggingface.co/datasets/walledai/CyberSecEval) |
| hf-cybernative | Yes | No | No | No | REVIEW REQUIRED | [Card labels Apache-2.0; generation/technical rights unverified](https://huggingface.co/datasets/CyberNative/Code_Vulnerability_Security_DPO) |

Counts: APPROVED 3, REVIEW REQUIRED 18, RESTRICTED 1, REJECTED 0. The approved entries are original Rsec candidate templates (SFT rights only, expert review still required), original public development benchmark templates (never training) and the bounded CVE knowledge/reference snapshots (no training or payload redistribution).

## Source-specific conditions

- **rsec-pilot** — Training: Public access is not training authorization. Original controlled templates only; expert review required for SFT promotion. Redistribution: Retain source attribution, license and modification notice; no third-party linked material is sublicensed. Restrictions: Authored infrastructure fixtures, not incidents or expert gold. No commercial API outputs harvested. No automatic expert status.

- **rsec-cyberbench** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: Retain source attribution, license and modification notice; no third-party linked material is sublicensed. Restrictions: Public development only; expert review pending. Reserved final evaluation must be independently authored and kept outside Git.

- **nvd** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **cve-program** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Bounded internal reference acquisition only under published CVE copy/derivative terms; retain MITRE notice/license locally. Linked advisories not covered; ML training and public payload redistribution disabled.

- **cwe** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **attack** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **cisa-kev** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Official mirror existence verified. CISA website/license returned 403 in this environment; no blanket license inferred from third-party summaries.

- **owasp-top10** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **osv** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: OSV aggregates CC-BY, CC0, MIT, share-alike and restricted/NC-ND datasets. Schema/software licenses do not relicense every advisory. Review each upstream.

- **github-advisories** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Retain attribution to individual advisories; source-linked code/advisories have separate rights. No corpus imported in this phase.

- **python-docs** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **microsoft-learn** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **kubernetes-docs** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **nist-csf** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **iso-27001** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Public catalog metadata only. No standard text acquired, reproduced or used as SFT; obtain explicit permission for intended use.

- **cis-controls** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Per-item rights, provenance, technical review and immutable snapshot required before ingestion.

- **sigma-rules** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: DRL requires author attribution in rule reproductions and displayed matches. Review how that obligation applies to outputs and derived training data.

- **yara-rules** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Community detection corpus; license of YARA software is not license of rule contents. No rules executed or imported.

- **primevul** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Code originates from many upstream projects with separate rights. Preserve chronological/project splits; reserve evaluation families. No bulk download.

- **hf-primevul** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Verified real mirror; original code licenses and original splits prevail. Card license alone is insufficient for approval; no download.

- **hf-cyberseceval** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: Evaluation suite candidate; exclude from SFT, retain upstream restrictions and project/CVE families. No records downloaded.

- **hf-cybernative** — Training: Public access is not training authorization. Not enabled for automatic SFT; source-specific training review remains pending. Redistribution: No public payload redistribution enabled by this registry. Restrictions: DPO preferred/rejected answers are not gold. Sample card contains claims requiring technical verification; generation origin/service terms and code rights need review. Not automatically converted to SFT.

## Promotion policy

Unknown licenses, unresolved mixed upstream rights, missing revisions and disallowed purposes block eligibility regardless of quality score. A source catalog edit changes the registry hash and invalidates previous review attestations until re-reviewed. Use opaque reviewer IDs and keep private legal/identity material outside the public repository. Engineering inspection of publisher terms is not counsel signoff.

Rsec's existing MIT license covers original repository work; it does not relicense linked standards, advisories, rule collections, base models or upstream code. No commercial ISO text or third-party raw dataset is included. Future generated or transformed samples require their own provenance/authorization and must not be labeled expert-reviewed by automation. No commercial chat/API outputs were harvested.
