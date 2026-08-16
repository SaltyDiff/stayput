# StayPut

StayPut — make sure your coding agent did the work where you told it to.

Deterministic integrity primitive for the Git locus an operator explicitly sealed.

StayPut is a host-neutral library and CLI. Hosts consume it with thin examples
under `examples/`. It is not an AI evaluator, sandbox, or workflow engine.

## What StayPut checks

After an operator runs `stayput save`, `stayput check` verifies that the
delivered Git locus matches the sealed approval:

- same repository lineage (`repo_id` from the sealed base commit)
- same worktree (`worktree_key`)
- sealed `base_commit` is an ancestor of `HEAD`
- every Git-visible delivered mutation is inside `allowed_paths`
- if `instruction_digest` was sealed, supplied instruction bytes digest to that value

## What StayPut does not check

StayPut does not determine correctness, test honesty, intent, safety,
unauthorized data, runtime behavior, or model-context accuracy.

`allowed_paths` is not a sandbox. `instruction_digest=null` means instruction
integrity is **not verified**.

## Explicit save / approval

`cwd` is not approval. There is no SessionStart save, TOFU, or silent overwrite.

```bash
stayput save --allowed-path src --allowed-path tests
```

Optional instruction binding — freeze bytes, then seal those exact bytes:

```bash
stayput save --instruction-file PLAN.md --allowed-path src
```

`--replace` is required to overwrite an existing `.stayput/approval.json`.

## Check

```bash
stayput check --json
```

Check never writes. It verifies `record_digest` before trusting the snapshot,
then compares the delivered Git locus. Git is the authority — not agent-reported
branch, worktree, or hook payload metadata.

## `allowed_paths`

Literal repo-relative prefixes. Default `["."]` means any Git-visible mutation
**inside the approved repository**. `src/auth` does not match `src/auth_backup`.
Globs and regex are not supported. A symlink whose resolved target leaves the
repository is `PATH_OUTSIDE_ALLOWLIST`.

## Optional instruction binding

`--instruction-file` is `read_bytes()`. No whitespace, newline, or Unicode
normalization. A sealed digest with omitted bytes is `INSTRUCTION_REQUIRED`
(operational error), not MATCH and not drift.

Capture of prompt bytes is not approval. The human still runs `stayput save`.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | `project` / `save` success, or `check` MATCH |
| `1` | operational ERROR (usage, missing approval, cannot prove) |
| `2` | `check` MISMATCH |

JSON `"ok": true` is not success. A completed MISMATCH is also `ok=true`.
Honor the process exit code. StayPut does not check branch names.

Locus/path classes: `REPOSITORY_MISMATCH`, `WORKTREE_MISMATCH`,
`BASE_COMMIT_MISMATCH`, `PATH_OUTSIDE_ALLOWLIST`. See
[`docs/failures.md`](docs/failures.md).

## CLI

```bash
stayput project [--cwd PATH] [--instruction-file FILE] [--allowed-path PATH ...] [--json]
stayput save    [--cwd PATH] [--path FILE] [--instruction-file FILE] [--allowed-path PATH ...] [--replace] [--json]
stayput check   [--cwd PATH] [--path FILE] [--instruction-file FILE] [--json]
```

Requires Python `>=3.12,<3.13`, [`salt-grain==0.1.0`](https://pypi.org/project/salt-grain/), and Git.

```bash
pip install -e '.[dev]'
```

## Host examples

Same flow everywhere: operator `save` → agent work → hook/CI `check`.

| Host | Example |
|---|---|
| Claude Code | [`examples/claude-code/`](examples/claude-code/) |
| Cursor / Cursor Cloud | [`examples/cursor/`](examples/cursor/) |
| OpenHands | [`examples/openhands/`](examples/openhands/) |
| Ordinary CI | [`examples/ci/`](examples/ci/) |

CI needs full history (`fetch-depth: 0`). Shallow clones fail closed
(`SHALLOW_REPOSITORY`, exit `1`). Honor the process exit code; do not
gate on JSON `"ok": true`.

See [`docs/usage.md`](docs/usage.md), [`docs/failures.md`](docs/failures.md),
and [`examples/README.md`](examples/README.md).

## Snapshot (`stayput.snapshot.v0.1`)

| Field | Meaning |
|---|---|
| `schema_version` | `stayput.snapshot.v0.1` |
| `instruction_digest` | SHA-256 of explicit instruction bytes, or `null` |
| `repo_id` | Sorted unique 40-hex roots of sealed-base ancestry |
| `worktree_key` | `""` for the main worktree; otherwise a POSIX relative git-dir key |
| `base_commit` | 40 lowercase hex |
| `allowed_paths` | Literal repo-relative prefixes; default `["."]` |

Approval wrapper `stayput.approval.v0.1`: `schema_version`, `snapshot`,
`record_digest`. Default path: `.stayput/approval.json`.

## Tests

```bash
python -m pytest -q
```

## Windows

Windows Git/worktree CI is **deferred**. See [`docs/windows.md`](docs/windows.md).
