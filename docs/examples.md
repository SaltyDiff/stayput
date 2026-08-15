# Examples

Thin integrations only. StayPut core stays host-neutral.

Operator seals approval with `stayput save`. The host stop/completion hook
or CI job runs `stayput check --json` (see `examples/check.sh`).

| Host | Config |
|---|---|
| Claude Code | `examples/claude-code/settings.json` |
| Cursor / Cursor Cloud | `examples/cursor/hooks.json` |
| OpenHands | `examples/openhands/hooks.json` |
| CI | `examples/ci/github-actions-check.yml` |

None of the hook/CI configs invoke `stayput save`.
