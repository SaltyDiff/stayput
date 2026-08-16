# Changelog

## 0.1.0

- Public identity is StayPut (`stayput` package, CLI, schemas, and `.stayput/approval.json`)
- TaskPin was an unpublished working name and is not a public compatibility alias
- Thin host/CI examples (Claude Code, Cursor, OpenHands, ordinary CI)
- Ready-to-copy Stop-hook files: project `.claude/settings.json`,
  `.cursor/hooks.json` (`version: 1`), native OpenHands top-level `stop`,
  and `examples/check.sh` copied as each host's `stayput-check.sh`
- Ordinary GitHub Actions CHECK honors process exit code; does not gate
  on JSON `"ok": true` (MISMATCH is also `ok=true`)
- Technical failure documentation for `REPOSITORY_MISMATCH`,
  `WORKTREE_MISMATCH`, `BASE_COMMIT_MISMATCH`, `PATH_OUTSIDE_ALLOWLIST`,
  and MISMATCH vs ERROR (`docs/failures.md`)
- User documentation for save / check / `allowed_paths` / exit codes
- Locus/mismatch/Git/path/instruction semantics unchanged from the unpublished TaskPin candidate
- T6: thin `stayput` CLI (`project`, `save`, `check`); exit 0/1/2
- T5: library `save` / `check` for `.stayput/approval.json`
- T5: explicit `replace=True` required to overwrite; `record_digest` verified before compare
- T4: optional instruction-byte digest and `INSTRUCTION_DRIFT`
- T4: sealed digest without bytes is `INSTRUCTION_REQUIRED`, not drift
- T3: changed-path projection and `PATH_OUTSIDE_ALLOWLIST`
- T3: literal `allowed_paths` prefix match; symlink escape is containment failure
- T2: Git locus projection (`project_locus`, `project_snapshot`, `compare_locus`)
- T2: fail-closed shallow / grafts / bare / missing objects / old Git
- T1: closed `stayput.snapshot.v0.1` six-field schema
- T1: `stayput.approval.v0.1` wrapper with `record_digest`
- T1: salt-grain canonicalization and digest verification
- T1: golden vectors for canonical bytes and digests
- Host adapters stay outside `src/stayput`
