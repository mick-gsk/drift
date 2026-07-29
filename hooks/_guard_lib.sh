#!/usr/bin/env bash
# Shared helpers for the drift guard hooks. Sourced, never executed directly.

# Resolve the guard entry point: prefer the console script, fall back to the
# module. Prints nothing and returns 1 when neither is available.
guard_cmd() {
  if command -v drift-guard >/dev/null 2>&1; then
    echo "drift-guard"
    return 0
  fi
  if python3 -c "import drift.guard" >/dev/null 2>&1; then
    echo "python3 -m drift.guard"
    return 0
  fi
  return 1
}

guard_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}
