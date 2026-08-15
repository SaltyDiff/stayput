# Claude Code + TaskPin

Copy `settings.json` into `.claude/settings.json` (or merge the `hooks.Stop` block).
Copy `../check.sh` next to it, or change `command` to an absolute path.

## Operator approval (required, manual)

```bash
taskpin save --allowed-path src --allowed-path tests
```

Optional instruction binding — freeze bytes first, then seal them:

```bash
# capture (not approval)
cp CLAUDE.md /tmp/taskpin-instruction.bin

# approve / seal those exact bytes
taskpin save --instruction-file /tmp/taskpin-instruction.bin --allowed-path src
```

Do **not** treat `UserPromptSubmit` or `SessionStart` as SAVE.
If you capture prompt bytes, keep that file separate from the SAVE command.
The human still runs `taskpin save`.

## Agent work

Claude Code edits the repository as usual.

## Stop hook

The Stop hook runs `examples/check.sh`, which execs `taskpin check --json`.
TaskPin reads Git from `$CLAUDE_PROJECT_DIR` (or `TASKPIN_CWD`).
It does not read Claude's hook JSON as identity.

## Exit codes vs Claude Code

| TaskPin | Meaning | Typical Claude Code Stop behavior |
|---|---|---|
| `0` | MATCH | stop proceeds |
| `2` | MISMATCH | Claude Code treats exit `2` as blocking |
| `1` | ERROR (no repo, bad approval, usage) | Claude Code does **not** treat `1` as a blocking Stop error |

TaskPin will not remap ERROR to `2`. If a host must block on ERROR,
wrap the command in that host — do not change TaskPin.

## What this example does not do

- no SessionStart auto-save
- no UserPromptSubmit approval
- no Claude SDK
- no TaskPin core changes
