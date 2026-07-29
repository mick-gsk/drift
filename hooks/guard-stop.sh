#!/usr/bin/env bash
# Claude Code Stop: show the user what the guard caught during this session.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

cmd="$(guard_cmd)" || exit 0
$cmd --hook Stop --repo "$(guard_repo_root)" stats 2>/dev/null || true
exit 0
