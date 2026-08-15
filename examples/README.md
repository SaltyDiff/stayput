# StayPut host examples

These examples show how a host can **consume** the StayPut CLI.
They do not add host logic to StayPut.

Required flow:

1. Operator explicitly runs `stayput save` (approval).
2. The coding agent does work.
3. A completion/stop hook or CI job runs `stayput check --json`.
4. The host honors the exit code: `0` MATCH, `1` ERROR, `2` MISMATCH.

None of these examples invoke `stayput save`.
SessionStart / UserPromptSubmit / agent-reported metadata are not approval.

| Host | Config | Check command |
|---|---|---|
| Claude Code | `claude-code/settings.json` | `examples/check.sh` |
| Cursor / Cursor Cloud | `cursor/hooks.json` | `examples/check.sh` |
| OpenHands | `openhands/hooks.json` | `examples/check.sh` |
| Ordinary CI | `ci/github-actions-check.yml` | `stayput check --json` |

`check.sh` only changes directory (when a project env var is set),
drains stdin, and execs `stayput check --json`.
Git identity is read by StayPut from the repository, not from hook JSON.
