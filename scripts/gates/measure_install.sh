#!/usr/bin/env bash
# Gate G5: measure clean checkout to a working guard, in seconds.
#
# Installed with --no-deps on purpose. The guard imports nothing but the
# standard library, so if this script needs a single third-party package to
# reach a green `drift-guard doctor`, that claim is false and the gate fails.
set -euo pipefail

BUDGET_S=60

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

start="$(date +%s)"

python3 -m venv "$workdir/venv"
"$workdir/venv/bin/pip" install --quiet -e . --no-deps

cp -R tests/guard/fixtures/sample_repo "$workdir/repo"
"$workdir/venv/bin/drift-guard" --repo "$workdir/repo" build >/dev/null
"$workdir/venv/bin/drift-guard" --repo "$workdir/repo" doctor

end="$(date +%s)"
elapsed=$(( end - start ))
echo "install_to_first_value_seconds=$elapsed"

if [ "$elapsed" -gt "$BUDGET_S" ]; then
  echo "G5 FAILED: ${elapsed}s > ${BUDGET_S}s"
  exit 1
fi
echo "G5 passed"
