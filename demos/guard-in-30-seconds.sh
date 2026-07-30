#!/usr/bin/env bash
# Prove the guard in half a minute, on a repository built in front of you.
#
# Every line of drift output below comes from the real hook, invoked with the
# real payload Claude Code sends. Nothing here is a transcript or a mock: if
# the guard were broken, this script would print nothing and say so.
#
#   bash demos/guard-in-30-seconds.sh
#
# Needs nothing but bash, git and Python 3.11+. It writes to a temporary
# directory, uses a throwaway index cache, and removes both on exit.
set -uo pipefail

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; OFF=$'\033[0m'
step() { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$OFF"; }
note() { printf '%s%s%s\n' "$DIM" "$1" "$OFF"; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$HERE/.." && pwd)"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
export DRIFT_CACHE_HOME="$workdir/cache"   # never touch the real index cache

# Resolve the guard exactly the way the hooks do, so this demo proves the same
# code path a user gets — installed console script, installed package, or the
# copy that ships inside the plugin.
# shellcheck source=/dev/null
. "$PLUGIN_ROOT/hooks/_guard_lib.sh"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
if ! guard_resolve; then
  echo "Could not find a way to run the guard. Python 3.11+ on PATH is enough." >&2
  exit 1
fi

step "A repository with one function in it"
repo="$workdir/repo"
mkdir -p "$repo/src/auth" "$repo/src/api"
cat > "$repo/src/auth/tokens.py" <<'PY'
def validate_token(token, audience):
    """The one that already exists."""
    return True
PY
( cd "$repo" && git init -q . && git add -A &&
  git -c user.email=demo@example.com -c user.name=demo commit -qm init )
note "src/auth/tokens.py  ->  def validate_token(token, audience)"

step "Index it"
$GUARD_CMD --repo "$repo" build
note "That is the whole setup cost. It happens once, in the background, at session start."

step "Now your agent writes this — in a different language, in a different directory"
cat > "$repo/src/api/handler.go" <<'GO'
package api

func ValidateToken(token string, audience string) bool {
	return true
}
GO
printf '%s\n' '  src/api/handler.go'
printf '%s\n' '    func ValidateToken(token string, audience string) bool'

step "What drift tells the agent, the moment the file is written"
payload="$(printf '{"tool_input":{"file_path":"%s/src/api/handler.go"}}' "$repo")"
# From inside the repository, because that is where Claude Code runs its hooks:
# the hook derives the repository root from the working directory.
out="$(cd "$repo" && printf '%s' "$payload" | bash "$PLUGIN_ROOT/hooks/guard-post-edit.sh")"

if [ -z "$out" ]; then
  printf '%s(nothing — that means the guard did not fire, which is a bug)%s\n' "$YELLOW" "$OFF"
  exit 1
fi

# Pull additionalContext out of the hook envelope: that field, and only that
# field, is what actually reaches the model.
printf '%s' "$out" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
text = payload.get("hookSpecificOutput", {}).get("additionalContext", "")
print("\033[32m" + text + "\033[0m")
'

step "Why that is not a string match"
note "Go said ValidateToken. Python said validate_token. Neither name appears in the other."
note "The index normalises both to the same key, so a duplicate is found across the"
note "language boundary — which is exactly where nobody is looking for it."

printf '\n%sInstall it:%s\n' "$BOLD" "$OFF"
printf '  /plugin marketplace add mick-gsk/drift\n'
printf '  /plugin install drift@drift\n\n'
