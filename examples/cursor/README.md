# Cursor / Cursor Cloud + TaskPin

Copy `hooks.json` into `.cursor/hooks.json` at the repository root.
Cursor Cloud Agents run **project** hooks from the repo, not `~/.cursor`.

Copy `../check.sh` into the repo (or point `command` at an absolute path).

Optional: set `TASKPIN_CWD` to the workspace root if the hook cwd is not
the Git checkout. Do not pass branch, worktree, or stop-payload fields
into TaskPin. CHECK reads Git.

## Operator approval (required, manual)

```bash
taskpin save --allowed-path src --allowed-path tests
```

Optional:

```bash
taskpin save --instruction-file PLAN.md --allowed-path src
```

## Agent work

The agent edits the repository.

## Stop hook

```text
examples/check.sh
```

which is:

```text
taskpin check --json
```

from the project directory. Stdin from Cursor is discarded.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | MATCH |
| `1` | ERROR |
| `2` | MISMATCH |

Honor these in the host. TaskPin does not auto-approve or auto-save.

## What this example does not do

- no trust of agent-reported branch / worktree / stop payload
- no Cursor SDK in TaskPin
- no SessionStart SAVE
- no TaskPin core changes
