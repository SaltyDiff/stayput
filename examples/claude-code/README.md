# Claude Code + StayPut

Copy these files into the project (not `~/.claude`):

```bash
mkdir -p .claude/hooks
cp examples/claude-code/settings.json .claude/settings.json
cp examples/check.sh .claude/hooks/stayput-check.sh
# or: cp examples/claude-code/stayput-check.sh .claude/hooks/stayput-check.sh
chmod +x .claude/hooks/stayput-check.sh
```

Merge the `hooks.Stop` block if `.claude/settings.json` already exists.
The hook script is `examples/check.sh` copied to `.claude/hooks/stayput-check.sh`.

## Operator approval (required, manual)

`stayput save` happens **before** the agent works. The Stop hook never saves.

```bash
stayput save --allowed-path src --allowed-path tests
```

Optional instruction binding — freeze bytes first, then seal them:

```bash
# capture (not approval)
cp CLAUDE.md /tmp/stayput-instruction.bin

# approve / seal those exact bytes
stayput save --instruction-file /tmp/stayput-instruction.bin --allowed-path src
```

Do **not** treat `UserPromptSubmit` or `SessionStart` as SAVE.
If you capture prompt bytes, keep that file separate from the SAVE command.
The human still runs `stayput save`.

## Agent work

Claude Code edits the repository as usual.

## Stop hook

`.claude/settings.json` registers a `command` Stop hook:

```text
.claude/hooks/stayput-check.sh
```

That script prefers `$CLAUDE_PROJECT_DIR` (then `$STAYPUT_CWD`), drains
stdin, and execs `stayput check --json`. StayPut reads Git from the
project directory. It does not read Claude's hook JSON as identity.

## Exit codes vs Claude Code

| StayPut | Meaning | Typical Claude Code Stop behavior |
|---|---|---|
| `0` | MATCH | stop proceeds |
| `2` | MISMATCH | Claude Code treats exit `2` as blocking |
| `1` | ERROR (no repo, bad approval, usage) | Claude Code does **not** treat `1` as a blocking Stop error |

Exit `1` remains ERROR. Do not reinterpret it as MISMATCH.
StayPut will not remap ERROR to `2`. If a host must block on ERROR,
wrap the command in that host — do not change StayPut.

See [`docs/failures.md`](../../docs/failures.md).

## What this example does not do

- no SessionStart auto-save
- no UserPromptSubmit approval
- no Claude SDK
- no StayPut core changes
