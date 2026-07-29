#!/usr/bin/env bash
# Shared helpers for the drift guard hooks. Sourced, never executed directly.

# Resolve how to run the guard and put it in GUARD_CMD. Returns 1 when there is
# no way to run it, in which case the hooks stay silent.
#
# The last branch is what makes `/plugin install drift@drift` enough on its own.
# The marketplace clones this repository, so the guard's source ships inside the
# installed plugin, and the guard imports nothing but the standard library — it
# runs from that copy under any system Python 3.11+, with no `pip install` and
# no dependency to resolve. Without this branch a fresh install is completely
# inert: every hook exits 0 with no output, forever, and looks like a guard that
# simply never finds anything.
#
# This sets a variable rather than echoing a command, because a `PYTHONPATH`
# exported inside `$(...)` would be lost with the subshell.
guard_resolve() {
  if command -v drift-guard >/dev/null 2>&1; then
    GUARD_CMD="drift-guard"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1 && python3 -c "import drift.guard" >/dev/null 2>&1; then
    GUARD_CMD="python3 -m drift.guard"
    return 0
  fi

  local bundled="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/src"
  if [ -d "$bundled/drift/guard" ] && command -v python3 >/dev/null 2>&1 &&
    PYTHONPATH="$bundled" python3 -c "import drift.guard" >/dev/null 2>&1; then
    export PYTHONPATH="$bundled${PYTHONPATH:+:$PYTHONPATH}"
    GUARD_CMD="python3 -m drift.guard"
    return 0
  fi

  return 1
}

guard_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}
