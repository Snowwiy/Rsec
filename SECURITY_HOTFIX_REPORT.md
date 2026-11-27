# Gitleaks on dev · 2026-11-26

The security workflow failed on [dev push](https://github.com/Snowwiy/Rsec/actions/runs/45910646663) and [PR #3](https://github.com/Snowwiy/Rsec/actions/runs/45910714362). Both runner logs report four findings and exit 1. A reproduction with the same remote branch graph scanned nine commits and 893,991 bytes. The findings were all `generic-api-key` in `849f0053bf3443b8d270945da9bdcaac6665667a`:

| File | Lines | Public fingerprints |
|---|---|---|
| data/manifests/pilot_statistics.json | 65, 68 | tokenizer_config.json, tokenizer.json |
| data/manifests/benchmark_statistics.json | 65, 68 | tokenizer_config.json, tokenizer.json |

Each value equals the SHA-256 recomputed from its corresponding public Qwen tokenizer file. The runner checks out dev, which lacked the config from `cb3d2d639ed99a0c8f16291353553fe734f224cb`, while its history scan also sees the fetched Phase 02 refs. The existing workflow loads the repository-root configuration automatically. The hotfix copies the prior config byte for byte. It extends every default rule and applies exact key/value matches AND the two exact paths to one detector.

The full branch-graph scan then returned 0. The regression script checks both authorized files, then adds different synthetic values and checks that findings persist across both an authorized path and another path. The history scan's default scope, redaction and exit behavior remain in force. No actual credential was identified among these findings.
