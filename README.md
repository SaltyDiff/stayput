# TaskPin

Deterministic integrity primitive for the git locus an operator explicitly sealed.

**T1** is the closed data layer: six-field snapshot, salt-grain canonicalization, and approval `record_digest`.

**T2** adds Git locus projection for `repo_id`, `worktree_key`, and base ancestry.

**T3** adds changed-path projection and `PATH_OUTSIDE_ALLOWLIST`.

**T4** adds optional instruction-byte verification and `INSTRUCTION_DRIFT`.

**T5** adds library `save` / `check` for `.taskpin/approval.json`.

**T6** adds a thin `taskpin` CLI. There are no hooks or host integrations yet.

## Guarantee (when later `check` exists)

The delivered Git locus matches the explicitly sealed TaskPin approval under the V0 projection.

T1 does not perform that check. It only makes the sealed snapshot and digest deterministic.

## Non-guarantees

TaskPin does not determine whether code is correct, tests passed honestly, intent was fulfilled, the environment was safe, or anything outside Git-visible delivered mutations. `allowed_paths` is not a sandbox. `instruction_digest=null` means instruction integrity is **not verified**.

## Snapshot (`taskpin.snapshot.v0.1`)

Exactly six fields:

| Field | Meaning |
|---|---|
| `schema_version` | `taskpin.snapshot.v0.1` |
| `instruction_digest` | SHA-256 of explicit instruction bytes, or `null` |
| `repo_id` | Sorted unique 40-hex roots of sealed-base ancestry (HEAD at save) |
| `worktree_key` | `""` for the main worktree; otherwise a POSIX relative git-dir key |
| `base_commit` | 40 lowercase hex |
| `allowed_paths` | Literal repo-relative prefixes; default `["."]` |

`allowed_paths` is a **set**: canonical form is sorted and deduplicated. `["."]` means any mutation **inside the approved repository**, not unrestricted filesystem access.

## Approval (`taskpin.approval.v0.1`)

```json
{
  "schema_version": "taskpin.approval.v0.1",
  "snapshot": { "...six fields..." },
  "record_digest": "<sha256 of salt-grain canonical snapshot bytes>"
}
```

Default future path: `.taskpin/approval.json`. T1 defines parse/verify only. No save/check CLI.

`record_digest` is computed with public [`salt-grain`](https://pypi.org/project/salt-grain/) `0.1.0` (`canonicalize_json` + `digest_bytes`). No custom cryptography. Receipt bind is omitted in T1; digest verification is sufficient.

## Install

```bash
pip install -e '.[dev]'
```

Requires Python `>=3.12,<3.13`.

## CLI

```bash
taskpin project [--cwd PATH] [--instruction-file FILE] [--allowed-path PATH ...] [--json]
taskpin save    [--cwd PATH] [--path FILE] [--instruction-file FILE] [--allowed-path PATH ...] [--replace] [--json]
taskpin check   [--cwd PATH] [--path FILE] [--instruction-file FILE] [--json]
```

Exit codes: `0` success/MATCH, `1` operational ERROR, `2` CHECK MISMATCH.

`--instruction-file` is read as exact bytes. `--replace` is required to overwrite an existing approval. `project` never writes an approval.

## Tests

```bash
python -m pytest -q
```

## Git locus (T2)

`project_snapshot(cwd)` / `project_locus(cwd)` observe the current work tree.

`compare_locus(sealed, cwd, instruction_bytes=...)` compares sealed `repo_id` / `worktree_key` / ancestry / changed paths / optional instruction bytes.

`instruction_digest=null` means instruction integrity is **not verified**. A sealed digest with omitted bytes is `INSTRUCTION_REQUIRED`, not MATCH and not drift. Digests are exact salt-grain SHA-256 of the supplied bytes. No whitespace, newline, or Unicode normalization.

CHECK `repo_id` is recomputed from the **sealed** `base_commit`, not delivered HEAD. Shallow clones, grafts, and bare repos fail closed. Replace refs are disabled during identity reads. `merge-base --is-ancestor` exit 128 is `CANNOT_PROVE_ANCESTRY`, not a mismatch.

Delivered paths are the sorted union of committed-since-base, staged, unstaged tracked, and untracked-not-ignored paths. Renames contribute both sides. `allowed_paths` is a literal prefix set; `src/auth` does not match `src/auth_backup`. A symlink whose resolved target leaves the repository is `PATH_OUTSIDE_ALLOWLIST`. Inability to project paths is `CANNOT_PROJECT_PATHS` / `UNCANONICAL_PATH`, not MATCH.

## Approval artifact (T5)

`save(cwd, replace=False)` writes `taskpin.approval.v0.1` to `.taskpin/approval.json` under `cwd` unless `path` is supplied. An existing file fails with `APPROVAL_ALREADY_EXISTS` unless `replace=True`.

`check(cwd)` reads that artifact, verifies `record_digest` before trusting the snapshot, then compares the delivered Git locus. Integrity failures are errors, not mismatches. Check never writes or repairs the file.

`cwd` alone never implies approval. There is no SessionStart save, TOFU, or silent overwrite.

## Windows

The worktree algorithm specifies `--path-format=absolute`, `\\` → `/`, and Windows-only case-fold equality. Windows Git/worktree CI is still **deferred**. See `docs/windows.md`.

## What this repository is not

Not a sandbox, policy engine, workflow engine, agent framework, hosted service, or Factory product. Core stays host-neutral.
