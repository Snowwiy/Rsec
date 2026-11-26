# Threat model and residual risks

Scope: local defensive research, untrusted source files, package/model supply chain, public repository and optional local runtimes. Assets: credentials, private logs, training corpora, checkpoints, integrity of model behavior and evidence provenance.

| Threat | Control | Residual boundary |
|---|---|---|
| Malicious model code / pickle | trust_remote_code=False; Safetensors for weights | Full trainer optimizer checkpoints remain trusted-local state; hashes are not signatures |
| Path traversal / output clobber | Confined manifest paths, id validation, atomic no-clobber outputs | Local filesystem owner is trusted; concurrent malicious symlink changes are not fully sandboxed |
| Secrets / PII in datasets | Heuristics, reject metadata, optional content redaction, content-free quarantine | Manual review is required; patterns do not cover every identifier |
| Poisoned text / indirect injection | Phrase screening, provenance review, no execution, knowledge/SFT separation | Semantic poisoning cannot be eliminated by regex |
| SSRF / malicious downloads | HTTPS host allowlist, global address check, redirect recheck, bounded files | DNS rebinding is not fully prevented without a network sandbox; use reviewed publishers and egress restrictions |
| Corrupted artifacts / manifests | SHA-256 and schema validation, immutable versions | An attacker replacing both manifest and data defeats unsigned integrity checks |
| Dependency compromise | Version pins, CPU lock, pip-audit and SHA-pinned actions | Audit databases are incomplete; GPU/optional stacks need separate audit |
| CI exfiltration | Read-only tokens; no persist-credentials; no pull_request_target | Third-party code and runner environment remain dependencies |
| Arbitrary generated code | Static structured scoring only | Isolated dynamic remediation testing is future work |
| Local runtime cloud forwarding | Local file paths; loopback Ollama; cloud-name rejection | Operator must configure the local service and network for strict offline enforcement |

Do not store credentials, private logs, unreviewed datasets, model weights or checkpoints in this public repository. No telemetry service is configured; report_to is empty unless local TensorBoard is explicitly enabled. Source acquisition is explicit and licensed. Environment diagnostics log hardware/configuration, not source records or prompts. Trusted application errors can be displayed; third-party exception bodies are suppressed by the CLI to reduce accidental disclosure.

GitHub Actions use immutable reviewed SHA references and minimum contents:read permissions. Security CI audits the frozen CPU dependency set and scans Git history with Gitleaks. No workflows access repository secrets or run a paid/self-hosted GPU. Report security issues privately through repository owner channels; do not place sensitive exploit details or live credentials in public issues.
