# Examples

Thin integrations only. StayPut core stays host-neutral.

Operator seals approval with `stayput save`. The host stop/completion hook
or CI job runs `stayput check --json` (see `examples/check.sh`, copied as
each host's `stayput-check.sh`).

| Host | Config | Hook script destination |
|---|---|---|
| Claude Code | `examples/claude-code/settings.json` → `.claude/settings.json` | `.claude/hooks/stayput-check.sh` |
| Cursor / Cursor Cloud | `examples/cursor/hooks.json` → `.cursor/hooks.json` | `.cursor/hooks/stayput-check.sh` |
| OpenHands | `examples/openhands/hooks.json` → `.openhands/hooks.json` | `.openhands/hooks/stayput-check.sh` |
| CI | `examples/ci/github-actions-check.yml` | `stayput check --json` |

None of the hook/CI configs invoke `stayput save`.

Technical failure classes: [`failures.md`](failures.md).
