# Local model registry

No Rsec model is registered initially. Proposed future lines Rsec-7B, Rsec-14B, Rsec-32B, Rsec-Coder, Rsec-SOC and Rsec-DFIR are names only, not existing products.

Use `rsec models register metadata.json` to create an immutable version. Required keys: id, rsec_version, base_model, revision, architecture, adapters, config, dataset_hash, trained_at, hardware, commit, metrics, license, artifacts, validation, compatibility and limitations. Artifacts is a nonempty list of existing local files. Registration records resolved path, SHA-256 and bytes; an existing id cannot be overwritten. Include the independent evaluation report in the artifacts list to bind the evidence.

`rsec models activate ID` accepts only TESTED entries and rechecks every file hash before atomically changing active.json. Activating a previous tested entry is rollback. TESTED is an operator assertion, not a substitute for review: release signoff must verify independent evaluation and regression evidence. No automatic replacement of deployed models occurs. Registry metadata and private artifact paths stay outside Git.
