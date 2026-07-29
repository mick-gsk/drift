#!/usr/bin/env bash
# Claude Code SessionStart: reset the session tally and make sure an index
# exists. A missing index is built detached, so the session never waits.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

guard_resolve || exit 0
$GUARD_CMD --hook SessionStart --repo "$(guard_repo_root)" session-start 2>/dev/null || true
exit 0
