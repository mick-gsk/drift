#!/usr/bin/env bash
# Claude Code PostToolUse(Write|Edit): report duplicates and first-ever
# boundary crossings introduced by the edit that just happened.
#
# The payload is handed to the guard unparsed. Reading file_path here would
# cost a second interpreter start per edit, and the whole round trip has a
# 150 ms budget.
set -uo pipefail
# shellcheck source=/dev/null
. "$(dirname "$0")/_guard_lib.sh"

cmd="$(guard_cmd)" || exit 0
$cmd --hook PostToolUse --repo "$(guard_repo_root)" post --payload-stdin 2>/dev/null || true
exit 0
