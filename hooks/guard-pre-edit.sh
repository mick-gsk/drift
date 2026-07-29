#!/usr/bin/env bash
# Claude Code PreToolUse(Write|Edit): brief the agent before it creates a NEW
# Python file. Never fails, never blocks — it returns context, not a verdict.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

guard_resolve || exit 0
$GUARD_CMD --hook PreToolUse --repo "$(guard_repo_root)" pre --payload-stdin 2>/dev/null || true
exit 0
