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

# Try the copy that ships inside the plugin. Sets GUARD_CMD and returns 0 on
# success, so both callers below stay one line.
_guard_try_bundled() {
  local root="$1"
  [ -d "$root/src/drift/guard" ] || return 1
  command -v python3 >/dev/null 2>&1 || return 1
  PYTHONPATH="$root/src" python3 -c "import drift.guard" >/dev/null 2>&1 || return 1
  export PYTHONPATH="$root/src${PYTHONPATH:+:$PYTHONPATH}"
  GUARD_CMD="python3 -m drift.guard"
  return 0
}

guard_resolve() {
  # Inside a plugin invocation the bundled copy wins, and it wins first.
  #
  # Preferring PATH here cost correctness for anyone who also has
  # `drift-analyzer` installed from PyPI — which is this tool's existing
  # audience, not a hypothetical one. If their venv precedes the plugin's
  # `bin/`, every hook ran their pip guard at whatever version they installed,
  # regardless of the commit the plugin is pinned to. An older guard fails the
  # index schema check, every hook exits 0 with no output, and the guard goes
  # quiet in a way that is indistinguishable from having found nothing (#801).
  #
  # CLAUDE_PLUGIN_ROOT is set only by Claude Code, so this branch cannot
  # affect anyone running `drift-guard` directly.
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && _guard_try_bundled "$CLAUDE_PLUGIN_ROOT"; then
    GUARD_SOURCE="bundled"
    return 0
  fi

  if command -v drift-guard >/dev/null 2>&1; then
    GUARD_CMD="drift-guard"
    GUARD_SOURCE="path"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1 && python3 -c "import drift.guard" >/dev/null 2>&1; then
    GUARD_CMD="python3 -m drift.guard"
    GUARD_SOURCE="installed"
    return 0
  fi

  # No plugin root — running from a checkout. Resolve relative to this script.
  if _guard_try_bundled "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; then
    GUARD_SOURCE="bundled"
    return 0
  fi

  return 1
}

guard_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}
