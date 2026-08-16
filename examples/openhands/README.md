# OpenHands + StayPut

Copy these files into the project:

```bash
mkdir -p .openhands/hooks
cp examples/openhands/hooks.json .openhands/hooks.json
cp examples/check.sh .openhands/hooks/stayput-check.sh
# or: cp examples/openhands/stayput-check.sh .openhands/hooks/stayput-check.sh
chmod +x .openhands/hooks/stayput-check.sh
```

The hook script is `examples/check.sh` copied to
`.openhands/hooks/stayput-check.sh`.

`.openhands/hooks.json` uses the native OpenHands shape: top-level
`stop`, `matcher: "*"`, nested `hooks[].command`. Do not use a
`{"hooks":{"stop":[{"command":...}]}}` hybrid.

`PLAN.md` may be supplied as instruction bytes **only** when the operator
explicitly seals it at SAVE time.

## Operator approval (required, manual)

`stayput save` happens **before** the agent works. The Stop hook never saves.

```bash
stayput save --allowed-path src --allowed-path tests
```

Optional PLAN.md binding:

```bash
stayput save --instruction-file PLAN.md --allowed-path src
```

## Agent work

OpenHands edits the repository.

## Completion / stop

```text
.openhands/hooks/stayput-check.sh
```

→ `stayput check --json` from `$OPENHANDS_PROJECT_DIR` or `$STAYPUT_CWD`.
Hook stdin is discarded. Git is the authority.

## Exit codes

| Exit | Meaning | Typical OpenHands Stop behavior |
|---|---|---|
| `0` | MATCH | stop proceeds |
| `2` | MISMATCH | exit `2` blocks |
| `1` | ERROR | ERROR; do not remap to MISMATCH |

OpenHands treats hook exit `2` as a blocking failure.
Exit `1` is StayPut ERROR and is not remapped.

See [`docs/failures.md`](../../docs/failures.md).

## What this example does not do

- no older hybrid/incorrect hook shape
- no OpenHands SDK dependency
- no automatic SAVE
- no StayPut core changes
