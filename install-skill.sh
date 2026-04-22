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
SKILL_PATHS=()

# Scan both the repo root (public skills) and personal/ (gitignored).
# personal/ is optional - the repo is public and most clones won't have one.
shopt -s nullglob
for dir in "$SCRIPT_DIR"/*/ "$SCRIPT_DIR"/personal/*/; do
    [ -f "$dir/SKILL.md" ] || continue
    name="$(basename "$dir")"
    [ "$name" = "personal" ] && continue
    desc=$(sed -n 's/^description: *//p' "$dir/SKILL.md" | head -1)
    desc="${desc:-(no description)}"
    SKILL_NAMES+=("$name")
    SKILL_DESCS+=("$desc")
    SKILL_PATHS+=("${dir%/}")
done
shopt -u nullglob

# Lookup a skill's source path by name (returns empty if not found)
skill_path_by_name() {
    local want="$1" i
    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        if [ "${SKILL_NAMES[$i]}" = "$want" ]; then
            echo "${SKILL_PATHS[$i]}"
            return 0
        fi
    done
    return 1
}

if [ ${#SKILL_NAMES[@]} -eq 0 ]; then
    echo "No skills found (folders with SKILL.md) in $SCRIPT_DIR"
    exit 1
fi

# ── Check install state ──
#
# A skill can be in one of three states across the TARGETS dirs:
#   full    — symlink present in every target
#   partial — symlink present in some but not all targets
#   none    — no symlink anywhere
#
# The installer reconciles to the desired state on apply, so partial
# installs get repaired (missing symlinks get created) rather than
# silently preselected as "already installed".

install_count() {
    local name="$1"
    local c=0
    for target_base in "${TARGETS[@]}"; do
        [ -L "$target_base/$name" ] && c=$((c + 1))
    done
    echo "$c"
}

install_state() {
    local c
    c="$(install_count "$1")"
    if [ "$c" -eq "${#TARGETS[@]}" ]; then
        echo "full"
    elif [ "$c" -eq 0 ]; then
        echo "none"
    else
        echo "partial"
    fi
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
    local total=${#TARGETS[@]}
    local cursor=0

    # Track per-target install state.
    # Preselect ON when any target has the symlink (including partial
    # installs) so the user sees them as installed; on apply we
    # reconcile to the desired state across all targets.
    local selected=()
    local actual_count=()
    for i in $(seq 0 $((count - 1))); do
        local c
        c="$(install_count "${SKILL_NAMES[$i]}")"
        actual_count+=("$c")
        if [ "$c" -gt 0 ]; then
            selected+=("1")
        else
            selected+=("0")
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

            # Show change indicator based on reconciliation:
            #   selected=1, actual<total  → install (or repair if partial)
            #   selected=0, actual>0      → uninstall
            local indicator=""
            local c="${actual_count[$i]}"
            if [ "${selected[$i]}" = "1" ] && [ "$c" -lt "$total" ]; then
                if [ "$c" -eq 0 ]; then
                    indicator=" ${GREEN}← install${RESET}"
                else
                    indicator=" ${CYAN}← repair (${c}/${total})${RESET}"
                fi
            elif [ "${selected[$i]}" = "0" ] && [ "$c" -gt 0 ]; then
                indicator=" ${RED}← uninstall${RESET}"
            fi

            echo -e "${prefix}${checkbox}  ${BOLD}${name}${RESET}${indicator}"
            echo -e "      ${DIM}${desc}${RESET}"
        done

        echo ""

        # Count pending changes by comparing desired (selected) vs actual
        local installs=0 repairs=0 uninstalls=0
        for i in $(seq 0 $((count - 1))); do
            local c="${actual_count[$i]}"
            if [ "${selected[$i]}" = "1" ] && [ "$c" -lt "$total" ]; then
                if [ "$c" -eq 0 ]; then
                    installs=$((installs + 1))
                else
                    repairs=$((repairs + 1))
                fi
            elif [ "${selected[$i]}" = "0" ] && [ "$c" -gt 0 ]; then
                uninstalls=$((uninstalls + 1))
            fi
        done

        if [ $installs -gt 0 ] || [ $repairs -gt 0 ] || [ $uninstalls -gt 0 ]; then
            local parts=()
            [ $installs -gt 0 ]   && parts+=("${GREEN}${installs} to install${RESET}")
            [ $repairs -gt 0 ]    && parts+=("${CYAN}${repairs} to repair${RESET}")
            [ $uninstalls -gt 0 ] && parts+=("${RED}${uninstalls} to uninstall${RESET}")
            local summary=""
            local sep=""
            for p in "${parts[@]}"; do
                summary="${summary}${sep}${p}"
                sep=", "
            done
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
# Reconciles each target directory to the desired state
# (selected=1 → symlink present; selected=0 → symlink absent).
# Works for fresh installs, partial-install repairs, and cleanup.
apply_changes() {
    local changed=0

    echo ""

    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        local name="${SKILL_NAMES[$i]}"
        local src="${SKILL_PATHS[$i]}"
        local created=0
        local removed=0

        if [ "${selected[$i]}" = "1" ]; then
            for target_base in "${TARGETS[@]}"; do
                local link="$target_base/$name"
                if [ -L "$link" ] && [ ! -e "$link" ]; then
                    # Broken symlink (source moved/deleted) - repair
                    ln -sfn "$src" "$link"
                    created=$((created + 1))
                elif [ ! -e "$link" ] && [ ! -L "$link" ]; then
                    # Truly missing - create
                    mkdir -p "$target_base"
                    ln -sfn "$src" "$link"
                    created=$((created + 1))
                elif [ ! -L "$link" ]; then
                    # Real file/directory in the way - refuse to clobber
                    echo -e "  ${RED}!${RESET} $link ${DIM}(not a symlink - requires manual cleanup: ${RESET}rm -rf $link${DIM})${RESET}"
                fi
                # Working symlink (to us or an override): leave alone
            done
            if [ $created -gt 0 ]; then
                echo -e "  ${GREEN}✓${RESET} Installed ${BOLD}$name${RESET} ${DIM}(${created} target(s))${RESET}"
                changed=$((changed + 1))
            fi
        else
            for target_base in "${TARGETS[@]}"; do
                if [ -L "$target_base/$name" ]; then
                    rm -f "$target_base/$name"
                    removed=$((removed + 1))
                fi
            done
            if [ $removed -gt 0 ]; then
                echo -e "  ${RED}✗${RESET} Uninstalled ${BOLD}$name${RESET} ${DIM}(${removed} target(s))${RESET}"
                changed=$((changed + 1))
            fi
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
    local total=${#TARGETS[@]}
    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        local name="${SKILL_NAMES[$i]}"
        local c
        c="$(install_count "$name")"
        if [ "$c" -eq "$total" ]; then
            echo -e "  ${GREEN}${CHECK}${RESET}  $name"
        elif [ "$c" -eq 0 ]; then
            echo -e "  ${DIM}${EMPTY}${RESET}  $name"
        else
            echo -e "  ${CYAN}${CHECK}${RESET}  $name ${DIM}(partial: ${c}/${total})${RESET}"
        fi
    done
}

cmd_install() {
    local name="$1"
    local src
    src="$(skill_path_by_name "$name")" || true
    if [ -z "$src" ] || [ ! -f "$src/SKILL.md" ]; then
        echo "Unknown skill: $name" >&2; exit 1
    fi
    for target_base in "${TARGETS[@]}"; do
        mkdir -p "$target_base"
        local link="$target_base/$name"
        # Refuse to clobber a real directory/file. ln -sf would silently
        # nest the link inside a directory, which is almost never what we want.
        if [ -e "$link" ] && [ ! -L "$link" ]; then
            echo "  ! $link (not a symlink - requires manual cleanup: rm -rf $link)" >&2
            continue
        fi
        ln -sfn "$src" "$link"
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
