# StayPut 0.1.0 failures

`stayput check` finishes in one of three process outcomes. JSON `ok` is
**not** that outcome.

| Exit | Status | JSON | Meaning |
|---|---|---|---|
| `0` | MATCH | `"ok": true`, `"status": "MATCH"` | delivered locus matches the seal |
| `1` | ERROR | `"ok": false`, `"error": "<CODE>"` | cannot prove; comparison did not complete |
| `2` | MISMATCH | `"ok": true`, `"status": "MISMATCH"` | comparison completed; sealed ≠ delivered |

MISMATCH is a completed comparison. ERROR is an operational failure
(missing approval, unreadable Git, shallow clone, cannot prove ancestry,
tampered `record_digest`, sealed instruction bytes omitted, usage).

Do **not** treat `"ok": true` as success. A MISMATCH payload is `ok=true`
because StayPut produced a structured result, not because the locus matched.

StayPut does **not** check branch names. The 0.1.0 snapshot has no branch
field. Git objects and worktree identity are the authority — not
agent-reported branch, worktree, or hook payload metadata.

## MISMATCH classes

Each mismatch item is `{ "class", "sealed", "delivered" }`.
`REPOSITORY_MISMATCH` short-circuits; later axes are not collected.

### `REPOSITORY_MISMATCH`

CHECK `repo_id` is the sorted unique 40-hex roots of the **sealed**
`base_commit`, not of `HEAD`.

Fired when that value is missing or differs from the sealed `repo_id`:

- different repository lineage
- sealed `base_commit` object is absent (`delivered` is `null`)

An orphan `HEAD` in the **same** repository is not this class. That is
`BASE_COMMIT_MISMATCH` (sealed base is no longer an ancestor of `HEAD`).

### `WORKTREE_MISMATCH`

`worktree_key` differs.

- main worktree: `""`
- linked worktree: POSIX path of `git-dir` relative to `common-dir`

Same repository, different worktree. Not a branch-name check.

### `BASE_COMMIT_MISMATCH`

`git merge-base --is-ancestor <sealed_base> HEAD` returned `1`.
The sealed `base_commit` is not an ancestor of current `HEAD`.

If that command returns neither `0` nor `1`, StayPut raises
`CANNOT_PROVE_ANCESTRY` (ERROR, exit `1`). Inability to prove is not a
mismatch.

### `PATH_OUTSIDE_ALLOWLIST`

A Git-visible delivered path is outside `allowed_paths`, or a path
resolves outside the approved work tree.

Literal repo-relative prefixes only. No globs, regex, or policy language.
`allowed_paths` is not a sandbox.

| Sealed prefix | Matches | Does not match |
|---|---|---|
| `.` (default) | any in-repo Git-visible path | a symlink whose resolved target leaves the repository |
| `src/auth` | `src/auth`, `src/auth/a.py` | `src/auth_backup`, `src/auth_backup/a.py` |

Match rule: `path == prefix` or `path.startswith(prefix + "/")`.
`.` is the in-repo wildcard.

Delivered paths are the Git-visible union since the sealed base:
committed, staged, unstaged, and untracked-not-ignored. The approval
file itself is excluded from that set.

A symlink (or symlink prefix) whose `realpath` leaves the repository
toplevel is `PATH_OUTSIDE_ALLOWLIST`. StayPut does not walk or read the
escaped target. Unresolvable paths are ERROR (`UNCANONICAL_PATH` /
`WORKTREE_UNRESOLVABLE`), not this class.

## Related 0.1.0 outcomes (not the four locus/path classes)

| Code | Kind | Notes |
|---|---|---|
| `INSTRUCTION_DRIFT` | MISMATCH | sealed `instruction_digest` ≠ supplied bytes |
| `INSTRUCTION_REQUIRED` | ERROR | digest was sealed; bytes were omitted |
| `DIGEST_MISMATCH` | ERROR | approval `record_digest` failed before compare |
| `SHALLOW_REPOSITORY` | ERROR | shallow clones fail closed during inspect |
| `CANNOT_PROVE_ANCESTRY` | ERROR | `merge-base --is-ancestor` was not 0 or 1 |
| `APPROVAL_MISSING` | ERROR | no `.stayput/approval.json` (or `--path`) |

Hosts must honor the process exit code. Exit `1` stays ERROR. Do not
remap it to `2`.
