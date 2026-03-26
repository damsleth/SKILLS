#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# Skill installer/uninstaller with interactive checkbox UI
# Discovers skills (folders with SKILL.md) in this directory
# and symlinks them into Claude, Codex, and Copilot skill dirs.
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGETS=(
    "$HOME/.claude/skills"
    "$HOME/.codex/skills"
    "$HOME/.copilot/skills"
)

# ── Discover skills (subfolders containing SKILL.md) ──

SKILL_NAMES=()
SKILL_DESCS=()

for dir in "$SCRIPT_DIR"/*/; do
    [ -f "$dir/SKILL.md" ] || continue
    name="$(basename "$dir")"
    desc=$(sed -n 's/^description: *//p' "$dir/SKILL.md" | head -1)
    desc="${desc:-(no description)}"
    SKILL_NAMES+=("$name")
    SKILL_DESCS+=("$desc")
done

if [ ${#SKILL_NAMES[@]} -eq 0 ]; then
    echo "No skills found (folders with SKILL.md) in $SCRIPT_DIR"
    exit 1
fi

# ── Check install state ──

is_installed() {
    local name="$1"
    for target_base in "${TARGETS[@]}"; do
        if [ -L "$target_base/$name" ]; then
            return 0
        fi
    done
    return 1
}

# ── Terminal helpers ──

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
RED='\033[31m'
CYAN='\033[36m'
RESET='\033[0m'
CHECK='◉'
EMPTY='◯'
ARROW='▸'

# ── Interactive checkbox UI ──

interactive_menu() {
    local count=${#SKILL_NAMES[@]}
    local cursor=0

    # Track selected state — pre-select installed skills
    local selected=()
    local was_installed=()
    for i in $(seq 0 $((count - 1))); do
        if is_installed "${SKILL_NAMES[$i]}"; then
            selected+=("1")
            was_installed+=("1")
        else
            selected+=("0")
            was_installed+=("0")
        fi
    done

    # Hide cursor, restore on exit
    tput civis 2>/dev/null || true
    cleanup() { tput cnorm 2>/dev/null || true; }
    trap cleanup EXIT

    while true; do
        # Clear screen and draw
        printf '\033[H\033[2J'
        echo -e "${BOLD}Skill Manager${RESET}  ${DIM}($SCRIPT_DIR)${RESET}"
        echo -e "${DIM}↑/↓ navigate  ·  space toggle  ·  enter apply  ·  q quit${RESET}"
        echo ""

        for i in $(seq 0 $((count - 1))); do
            local name="${SKILL_NAMES[$i]}"
            local desc="${SKILL_DESCS[$i]}"
            # Truncate long descriptions
            if [ ${#desc} -gt 60 ]; then
                desc="${desc:0:57}..."
            fi

            local prefix=""
            if [ "$i" -eq "$cursor" ]; then
                prefix="${CYAN}${ARROW}${RESET} "
            else
                prefix="  "
            fi

            local checkbox=""
            if [ "${selected[$i]}" = "1" ]; then
                checkbox="${GREEN}${CHECK}${RESET}"
            else
                checkbox="${DIM}${EMPTY}${RESET}"
            fi

            # Show change indicator
            local indicator=""
            if [ "${selected[$i]}" != "${was_installed[$i]}" ]; then
                if [ "${selected[$i]}" = "1" ]; then
                    indicator=" ${GREEN}← install${RESET}"
                else
                    indicator=" ${RED}← uninstall${RESET}"
                fi
            fi

            echo -e "${prefix}${checkbox}  ${BOLD}${name}${RESET}${indicator}"
            echo -e "      ${DIM}${desc}${RESET}"
        done

        echo ""

        # Count pending changes
        local installs=0 uninstalls=0
        for i in $(seq 0 $((count - 1))); do
            if [ "${selected[$i]}" != "${was_installed[$i]}" ]; then
                if [ "${selected[$i]}" = "1" ]; then
                    installs=$((installs + 1))
                else
                    uninstalls=$((uninstalls + 1))
                fi
            fi
        done

        if [ $installs -gt 0 ] || [ $uninstalls -gt 0 ]; then
            local summary=""
            [ $installs -gt 0 ] && summary="${GREEN}${installs} to install${RESET}"
            [ $installs -gt 0 ] && [ $uninstalls -gt 0 ] && summary="$summary, "
            [ $uninstalls -gt 0 ] && summary="${summary}${RED}${uninstalls} to uninstall${RESET}"
            echo -e "  ${summary}  ${DIM}— press enter to apply${RESET}"
        else
            echo -e "  ${DIM}No changes${RESET}"
        fi

        # Read single keypress
        IFS= read -rsn1 key
        case "$key" in
            A|k)  # Up / k
                [ $cursor -gt 0 ] && cursor=$((cursor - 1))
                ;;
            B|j)  # Down / j
                [ $cursor -lt $((count - 1)) ] && cursor=$((cursor + 1))
                ;;
            ' ')  # Space — toggle
                if [ "${selected[$cursor]}" = "1" ]; then
                    selected[$cursor]="0"
                else
                    selected[$cursor]="1"
                fi
                ;;
            '')   # Enter — apply
                apply_changes
                return
                ;;
            q)    # Quit
                echo ""
                echo "No changes made."
                return
                ;;
            $'\x1b')  # Escape sequence — read the rest
                read -rsn2 rest
                case "$rest" in
                    '[A') [ $cursor -gt 0 ] && cursor=$((cursor - 1)) ;;
                    '[B') [ $cursor -lt $((count - 1)) ] && cursor=$((cursor + 1)) ;;
                esac
                ;;
        esac
    done
}

# ── Apply install/uninstall changes ──
# Uses $selected and $was_installed from interactive_menu's scope
apply_changes() {
    local changed=0

    echo ""

    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        local name="${SKILL_NAMES[$i]}"
        local src="$SCRIPT_DIR/$name"

        if [ "${selected[$i]}" = "1" ] && [ "${was_installed[$i]}" = "0" ]; then
            for target_base in "${TARGETS[@]}"; do
                mkdir -p "$target_base"
                ln -sf "$src" "$target_base/$name"
            done
            echo -e "  ${GREEN}✓${RESET} Installed ${BOLD}$name${RESET}"
            changed=$((changed + 1))

        elif [ "${selected[$i]}" = "0" ] && [ "${was_installed[$i]}" = "1" ]; then
            for target_base in "${TARGETS[@]}"; do
                rm -f "$target_base/$name"
            done
            echo -e "  ${RED}✗${RESET} Uninstalled ${BOLD}$name${RESET}"
            changed=$((changed + 1))
        fi
    done

    if [ $changed -eq 0 ]; then
        echo "No changes made."
    else
        echo ""
        echo -e "${DIM}Targets: ${TARGETS[*]}${RESET}"
        echo "Done. $changed skill(s) updated."
    fi
}

# ── CLI flags for non-interactive use ──

usage() {
    echo "Usage: $(basename "$0") [--install <name>] [--uninstall <name>] [--list]"
    echo ""
    echo "  (no args)          Interactive checkbox UI"
    echo "  --install <name>   Install a skill by name"
    echo "  --uninstall <name> Uninstall a skill by name"
    echo "  --list             List all skills and their install state"
}

cmd_list() {
    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        local name="${SKILL_NAMES[$i]}"
        if is_installed "$name"; then
            echo -e "  ${GREEN}${CHECK}${RESET}  $name"
        else
            echo -e "  ${DIM}${EMPTY}${RESET}  $name"
        fi
    done
}

cmd_install() {
    local name="$1"
    local src="$SCRIPT_DIR/$name"
    if [ ! -f "$src/SKILL.md" ]; then
        echo "Unknown skill: $name" >&2; exit 1
    fi
    for target_base in "${TARGETS[@]}"; do
        mkdir -p "$target_base"
        ln -sf "$src" "$target_base/$name"
    done
    echo "Installed: $name"
}

cmd_uninstall() {
    local name="$1"
    local removed=0
    for target_base in "${TARGETS[@]}"; do
        if [ -L "$target_base/$name" ]; then
            rm -f "$target_base/$name"
            removed=$((removed + 1))
        fi
    done
    if [ $removed -gt 0 ]; then
        echo "Uninstalled: $name"
    else
        echo "Not installed: $name"
    fi
}

# ── Main ──

case "${1:-}" in
    --install)   cmd_install "${2:?skill name required}" ;;
    --uninstall) cmd_uninstall "${2:?skill name required}" ;;
    --list)      cmd_list ;;
    --help|-h)   usage ;;
    "")          interactive_menu ;;
    *)           echo "Unknown option: $1" >&2; usage; exit 1 ;;
esac
