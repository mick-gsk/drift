#!/usr/bin/env bash
# List all skills under .github/skills/ with their dependency classification.
# Skills that declare `dependency: hard|soft` in YAML frontmatter are shown
# under the matching group. Skills without the field are listed as "unclassified".
#
# Usage:
#   ./scripts/list-skills.sh
#   ./scripts/list-skills.sh --filter hard

set -euo pipefail

FILTER="all"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --filter)
            FILTER="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SKILLS_DIR="$ROOT_DIR/.github/skills"

hard=()
soft=()
none=()

while IFS= read -r -d '' skill_file; do
    skill_name="$(basename "$(dirname "$skill_file")")"

    # Parse YAML frontmatter (--- ... ---)
    dep=""
    if awk '/^---/{p=!p; next} p{print}' "$skill_file" 2>/dev/null \
        | grep -qm1 "^dependency:"; then
        dep=$(awk '/^---/{p=!p; next} p{print}' "$skill_file" \
            | grep "^dependency:" | head -1 | sed 's/dependency:[[:space:]]*//' | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    fi

    case "$dep" in
        hard) hard+=("$skill_name") ;;
        soft) soft+=("$skill_name") ;;
        *)    none+=("$skill_name") ;;
    esac
done < <(find "$SKILLS_DIR" -name "SKILL.md" -print0 | sort -z)

RED='\033[0;31m'
YELLOW='\033[1;33m'
GRAY='\033[0;90m'
CYAN='\033[0;36m'
NC='\033[0m'

print_group() {
    local label="$1"
    local color="$2"
    shift 2
    local items=("$@")
    echo -e "\n${color}${label} (${#items[@]})${NC}"
    if [[ ${#items[@]} -eq 0 ]]; then
        echo -e "  ${GRAY}(none)${NC}"
    else
        for item in "${items[@]}"; do
            echo "  $item"
        done
    fi
}

if [[ "$FILTER" == "all" || "$FILTER" == "hard" ]]; then
    print_group "HARD dependency" "$RED" "${hard[@]+"${hard[@]}"}"
fi
if [[ "$FILTER" == "all" || "$FILTER" == "soft" ]]; then
    print_group "SOFT dependency" "$YELLOW" "${soft[@]+"${soft[@]}"}"
fi
if [[ "$FILTER" == "all" || "$FILTER" == "unclassified" ]]; then
    print_group "UNCLASSIFIED (no dependency: field)" "$GRAY" "${none[@]+"${none[@]}"}"
fi

total=$(( ${#hard[@]} + ${#soft[@]} + ${#none[@]} ))
echo -e "\n${CYAN}Total: $total skills${NC}"
