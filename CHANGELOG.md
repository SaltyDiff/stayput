# Changelog

## 0.1.0

- T3: changed-path projection and `PATH_OUTSIDE_ALLOWLIST`
- T3: literal `allowed_paths` prefix match; symlink escape is containment failure
- T2: Git locus projection (`project_locus`, `project_snapshot`, `compare_locus`)
- T2: fail-closed shallow / grafts / bare / missing objects / old Git
- T1: closed `taskpin.snapshot.v0.1` six-field schema
- T1: `taskpin.approval.v0.1` wrapper with `record_digest`
- T1: salt-grain canonicalization and digest verification
- T1: golden vectors for canonical bytes and digests
- No CLI, hooks, instruction checking, or host adapters
