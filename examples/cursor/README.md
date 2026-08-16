# Cursor / Cursor Cloud + StayPut

Copy these files into the **project** (Cloud Agents do not load `~/.cursor`):

```bash
mkdir -p .cursor/hooks
cp examples/cursor/hooks.json .cursor/hooks.json
cp examples/check.sh .cursor/hooks/stayput-check.sh
# or: cp examples/cursor/stayput-check.sh .cursor/hooks/stayput-check.sh
chmod +x .cursor/hooks/stayput-check.sh
```

The hook script is `examples/check.sh` copied to `.cursor/hooks/stayput-check.sh`.
Do not add a `stayput-stop.sh` translator. StayPut's native exit contract
is the integration.

Optional: set `STAYPUT_CWD` to the workspace root if the hook cwd is not
the Git checkout. Do not pass branch, worktree, or stop-payload fields
into StayPut. CHECK reads Git.

## Operator approval (required, manual)

`stayput save` happens **before** the agent works. The Stop hook never saves.

```bash
stayput save --allowed-path src --allowed-path tests
```

Optional:

```bash
stayput save --instruction-file PLAN.md --allowed-path src
```

## Agent work

The agent edits the repository.

## Stop hook

`.cursor/hooks.json` is Cursor hooks schema `version: 1` with
`hooks.stop` pointing at:

```text
.cursor/hooks/stayput-check.sh
```

which execs:

```text
stayput check --json
```

from the project directory. Stdin from Cursor is discarded.

Cursor may accept a JSON `followup_message` on hook stdout. That is
optional Cursor behavior. It is **not** required for StayPut
integration, and this example does not emit one.

## Exit codes

| Exit | Meaning | Typical Cursor Stop behavior |
|---|---|---|
| `0` | MATCH | stop proceeds |
| `2` | MISMATCH | exit `2` blocks Stop |
| `1` | ERROR | ERROR; do not remap to MISMATCH |

Honor these in the host. StayPut does not auto-approve or auto-save.

See [`docs/failures.md`](../../docs/failures.md).

## What this example does not do

- no `stayput-stop.sh` or other exit-code translator
- no required `followup_message`
- no trust of agent-reported branch / worktree / stop payload
- no Cursor SDK in StayPut
- no SessionStart SAVE
- no user-level `~/.cursor` hooks for Cloud Agents
- no StayPut core changes
