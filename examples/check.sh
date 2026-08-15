#!/bin/sh
# Host-neutral CHECK wrapper. Does not SAVE. Does not trust hook stdin.
# Prefer an explicit project directory; otherwise use the current working directory.
set -eu

if [ -n "${TASKPIN_CWD:-}" ]; then
  cd "${TASKPIN_CWD}"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  cd "${CLAUDE_PROJECT_DIR}"
elif [ -n "${OPENHANDS_PROJECT_DIR:-}" ]; then
  cd "${OPENHANDS_PROJECT_DIR}"
fi

# Drain host payload so it cannot be mistaken for CLI input.
if [ ! -t 0 ]; then
  cat >/dev/null
fi

exec taskpin check --json "$@"
