# OpenHands + TaskPin

Copy `hooks.json` into `.openhands/hooks.json` if the runtime loads that
file, or register the same `stop` command in the OpenHands hook UI.

Copy `../check.sh` into the repo (or use an absolute path).

`PLAN.md` may be supplied as instruction bytes **only** when the operator
explicitly seals it at SAVE time.

## Operator approval (required, manual)

```bash
taskpin save --allowed-path src --allowed-path tests
```

Optional PLAN.md binding:

```bash
taskpin save --instruction-file PLAN.md --allowed-path src
```

## Agent work

OpenHands edits the repository.

## Completion / stop

```text
examples/check.sh
```

→ `taskpin check --json` from `$OPENHANDS_PROJECT_DIR` or `TASKPIN_CWD`.
Hook stdin is discarded. Git is the authority.

## Exit codes

| Exit | Meaning |
|---|---|
| `0` | MATCH |
| `1` | ERROR |
| `2` | MISMATCH |

OpenHands commonly treats hook exit `2` as a blocking failure.
Exit `1` is TaskPin ERROR and is not remapped.

## What this example does not do

- no OpenHands SDK dependency
- no automatic SAVE
- no TaskPin core changes
