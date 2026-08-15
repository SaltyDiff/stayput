# Changelog

## 0.1.0

- T5: library `save` / `check` for `.taskpin/approval.json`
- T5: explicit `replace=True` required to overwrite; `record_digest` verified before compare
- T4: optional instruction-byte digest and `INSTRUCTION_DRIFT`
- T4: sealed digest without bytes is `INSTRUCTION_REQUIRED`, not drift
- T3: changed-path projection and `PATH_OUTSIDE_ALLOWLIST`
- T3: literal `allowed_paths` prefix match; symlink escape is containment failure
- T2: Git locus projection (`project_locus`, `project_snapshot`, `compare_locus`)
- T2: fail-closed shallow / grafts / bare / missing objects / old Git
- T1: closed `taskpin.snapshot.v0.1` six-field schema
- T1: `taskpin.approval.v0.1` wrapper with `record_digest`
- T1: salt-grain canonicalization and digest verification
- T1: golden vectors for canonical bytes and digests
- No CLI, hooks, or host adapters
