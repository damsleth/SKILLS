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

# Optional targets: only added when the parent dir already exists.
# Avoids creating tool dirs for tools the user hasn't installed.
for optional in "$HOME/.agents" "$HOME/.pi"; do
    [ -d "$optional" ] && TARGETS+=("$optional/skills")
done

# "All skills" library: real (non-symlink) skill folders kept in
# ~/.agents/skills, copied (not symlinked) into Claude/Codex/Copilot.
# Disabling moves the folder out to skills-unused instead of deleting it.
AGENTS_SKILLS_DIR="$HOME/.agents/skills"
AGENTS_UNUSED_DIR="$HOME/.agents/skills-unused"
COPY_TARGETS=(
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

# Lookup a skill's source path by name (returns empty if not found).
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

# All repo/personal skills use kind "link" (symlinked). Skills discovered
# below in the ~/.agents/skills library use kind "copy" (copied, not linked).
SKILL_KIND=()
for _ in "${SKILL_NAMES[@]}"; do SKILL_KIND+=("link"); done
REPO_SKILL_COUNT=${#SKILL_NAMES[@]}

skill_kind_by_name() {
    local want="$1" i
    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        if [ "${SKILL_NAMES[$i]}" = "$want" ]; then
            echo "${SKILL_KIND[$i]}"
            return 0
        fi
    done
    return 1
}

# Scan the "all skills" library: real directories in ~/.agents/skills
# (enabled) and ~/.agents/skills-unused (disabled). Symlinks inside
# ~/.agents/skills are repo skills mirrored there via TARGETS above —
# those stay link-only and are never listed here.
shopt -s nullglob
if [ -d "$AGENTS_SKILLS_DIR" ]; then
    for dir in "$AGENTS_SKILLS_DIR"/*/; do
        entry="${dir%/}"
        [ -L "$entry" ] && continue
        [ -f "$dir/SKILL.md" ] || continue
        name="$(basename "$dir")"
        if skill_path_by_name "$name" >/dev/null 2>&1; then
            echo "Warning: ~/.agents/skills/$name collides with an existing skill name - skipping" >&2
            continue
        fi
        desc=$(sed -n 's/^description: *//p' "$dir/SKILL.md" | head -1)
        desc="${desc:-(no description)}"
        SKILL_NAMES+=("$name")
        SKILL_DESCS+=("$desc")
        SKILL_PATHS+=("$entry")
        SKILL_KIND+=("copy")
    done
fi
if [ -d "$AGENTS_UNUSED_DIR" ]; then
    for dir in "$AGENTS_UNUSED_DIR"/*/; do
        entry="${dir%/}"
        [ -f "$dir/SKILL.md" ] || continue
        name="$(basename "$dir")"
        if skill_path_by_name "$name" >/dev/null 2>&1; then
            echo "Warning: ~/.agents/skills-unused/$name collides with an existing skill name - skipping" >&2
            continue
        fi
        desc=$(sed -n 's/^description: *//p' "$dir/SKILL.md" | head -1)
        desc="${desc:-(no description)}"
        SKILL_NAMES+=("$name")
        SKILL_DESCS+=("$desc")
        SKILL_PATHS+=("$entry")
        SKILL_KIND+=("copy")
    done
fi
shopt -u nullglob

if [ ${#SKILL_NAMES[@]} -eq 0 ]; then
    echo "No skills found (folders with SKILL.md) in $SCRIPT_DIR or $AGENTS_SKILLS_DIR"
    exit 1
fi

# ── Per-skill companion-CLI hooks ──
#
# A few skills ship a companion CLI that belongs on PATH; symlinking the
# skill folder isn't enough. These hooks run the skill's own installer on
# install and tear the CLI link down on uninstall. Keyed by skill name.
# No-op for skills without a CLI.

CLI_BIN_DIR="$HOME/.local/bin"

skill_cli_install() {
    local name="$1" src="$2"
    case "$name" in
        cj-todo) bash "$src/todo.sh" install "$CLI_BIN_DIR" 2>/dev/null || true ;;
    esac
}

skill_cli_uninstall() {
    local name="$1"
    case "$name" in
        cj-todo)
            # Only remove the link if it actually points at our script.
            local link="$CLI_BIN_DIR/todo"
            if [ -L "$link" ] && [ "$(readlink "$link")" = "$(skill_path_by_name cj-todo)/todo.sh" ]; then
                rm -f "$link"
                echo "  Unlinked todo CLI ($link)"
            fi
            ;;
    esac
}

# ── Check install state ──
#
# A skill can be in one of three states across its targets:
#   full    — present in every target
#   partial — present in some but not all targets
#   none    — absent everywhere
#
# The installer reconciles to the desired state on apply, so partial
# installs get repaired (missing copies/symlinks get created) rather than
# silently preselected as "already installed".
#
# "link" kind skills (this repo) symlink into TARGETS. "copy" kind skills
# (~/.agents/skills library) copy into the fixed COPY_TARGETS, and treat
# living in ~/.agents/skills-unused as zero targets (fully disabled).

target_count_for_kind() {
    if [ "$1" = "copy" ]; then
        echo "${#COPY_TARGETS[@]}"
    else
        echo "${#TARGETS[@]}"
    fi
}

install_count_link() {
    local name="$1"
    local c=0
    for target_base in "${TARGETS[@]}"; do
        [ -L "$target_base/$name" ] && c=$((c + 1))
    done
    echo "$c"
}

install_count_copy() {
    local name="$1"
    if [ -d "$AGENTS_UNUSED_DIR/$name" ]; then
        echo 0
        return
    fi
    local c=0
    for target_base in "${COPY_TARGETS[@]}"; do
        [ -d "$target_base/$name" ] && c=$((c + 1))
    done
    echo "$c"
}

install_count() {
    local name="$1"
    local kind
    kind="$(skill_kind_by_name "$name")"
    if [ "$kind" = "copy" ]; then
        install_count_copy "$name"
    else
        install_count_link "$name"
    fi
}

install_state() {
    local c total
    c="$(install_count "$1")"
    total="$(target_count_for_kind "$(skill_kind_by_name "$1")")"
    if [ "$c" -eq "$total" ]; then
        echo "full"
    elif [ "$c" -eq 0 ]; then
        echo "none"
    else
        echo "partial"
    fi
}

# ── Terminal helpers ──

if [ -t 1 ]; then
    BOLD='\033[1m'
    DIM='\033[2m'
    GREEN='\033[32m'
    RED='\033[31m'
    CYAN='\033[36m'
    RESET='\033[0m'
else
    BOLD=''
    DIM=''
    GREEN=''
    RED=''
    CYAN=''
    RESET=''
fi
CHECK='◉'
EMPTY='◯'
ARROW='▸'

# ── Interactive checkbox UI ──

interactive_menu() {
    local count=${#SKILL_NAMES[@]}
    local cursor=0

    # Track per-target install state.
    # Preselect ON when any target has the symlink (including partial
    # installs) so the user sees them as installed; on apply we
    # reconcile to the desired state across all targets.
    # For "copy" kind skills, the source location is the ground truth for
    # enabled/disabled instead — a freshly-enabled skill with zero copies
    # yet should still show checked (it'll be synced on apply).
    local selected=()
    local actual_count=()
    local actual_total=()
    for i in $(seq 0 $((count - 1))); do
        local name="${SKILL_NAMES[$i]}"
        local kind="${SKILL_KIND[$i]}"
        local c
        c="$(install_count "$name")"
        actual_count+=("$c")
        actual_total+=("$(target_count_for_kind "$kind")")
        if [ "$kind" = "copy" ]; then
            if [ -d "$AGENTS_UNUSED_DIR/$name" ]; then
                selected+=("0")
            else
                selected+=("1")
            fi
        elif [ "$c" -gt 0 ]; then
            selected+=("1")
        else
            selected+=("0")
        fi
    done

    # Hide cursor, restore on exit
    tput civis 2>/dev/null || true
    cleanup() { tput cnorm 2>/dev/null || true; }
    trap cleanup EXIT

    # Scrolling viewport: only render as many items as fit the terminal
    # height, keeping the cursor inside the visible window. Without this,
    # a list taller than the terminal scrolls the terminal itself and the
    # cursor can end up above the visible area.
    local scroll_offset=0

    while true; do
        local term_rows
        term_rows="$(tput lines 2>/dev/null || echo 24)"
        # Each item is 2 lines (name + desc). Reserve rows for the header,
        # footer, and scroll indicators; a little slack is fine.
        local visible=$(( (term_rows - 9) / 2 ))
        [ "$visible" -lt 3 ] && visible=3
        [ "$visible" -gt "$count" ] && visible=$count

        [ "$cursor" -lt "$scroll_offset" ] && scroll_offset=$cursor
        [ "$cursor" -ge $((scroll_offset + visible)) ] && scroll_offset=$((cursor - visible + 1))
        local max_offset=$((count - visible))
        [ "$max_offset" -lt 0 ] && max_offset=0
        [ "$scroll_offset" -gt "$max_offset" ] && scroll_offset=$max_offset
        [ "$scroll_offset" -lt 0 ] && scroll_offset=0
        local window_end=$((scroll_offset + visible - 1))
        [ "$window_end" -gt $((count - 1)) ] && window_end=$((count - 1))

        # Clear screen and draw
        printf '\033[H\033[2J'
        echo -e "${BOLD}Skill Manager${RESET}  ${DIM}($SCRIPT_DIR)${RESET}"
        echo -e "${DIM}↑/↓ navigate  ·  space toggle  ·  enter apply  ·  q quit${RESET}"
        echo ""

        if [ "$scroll_offset" -gt 0 ]; then
            echo -e "  ${DIM}↑ ${scroll_offset} more above${RESET}"
        fi

        for i in $(seq "$scroll_offset" "$window_end"); do
            if [ "$i" -eq "$REPO_SKILL_COUNT" ] && [ "$REPO_SKILL_COUNT" -lt "$count" ]; then
                echo -e "${BOLD}All skills${RESET} ${DIM}(~/.agents/skills)${RESET}"
            fi

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
            local t="${actual_total[$i]}"
            if [ "${selected[$i]}" = "1" ] && [ "$c" -lt "$t" ]; then
                if [ "$c" -eq 0 ]; then
                    indicator=" ${GREEN}← install${RESET}"
                else
                    indicator=" ${CYAN}← repair (${c}/${t})${RESET}"
                fi
            elif [ "${selected[$i]}" = "0" ] && [ "$c" -gt 0 ]; then
                indicator=" ${RED}← uninstall${RESET}"
            fi

            echo -e "${prefix}${checkbox}  ${BOLD}${name}${RESET}${indicator}"
            echo -e "      ${DIM}${desc}${RESET}"
        done

        if [ "$window_end" -lt $((count - 1)) ]; then
            echo -e "  ${DIM}↓ $((count - 1 - window_end)) more below${RESET}"
        fi

        echo ""

        # Count pending changes by comparing desired (selected) vs actual
        local installs=0 repairs=0 uninstalls=0
        for i in $(seq 0 $((count - 1))); do
            local c="${actual_count[$i]}"
            local t="${actual_total[$i]}"
            if [ "${selected[$i]}" = "1" ] && [ "$c" -lt "$t" ]; then
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
                if [ "${selected[cursor]}" = "1" ]; then
                    selected[cursor]="0"
                else
                    selected[cursor]="1"
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

# Enable/disable a "copy" kind skill (~/.agents/skills library).
# Enable: move skills-unused → skills (if needed), then sync copies out
# to COPY_TARGETS. Disable: delete the copies, move skills → skills-unused.
# Copies are re-synced on every apply (diffed first) so source edits
# propagate without requiring an explicit toggle.
apply_copy_skill() {
    local i="$1"
    local name="${SKILL_NAMES[$i]}"
    local any_change=0

    if [ "${selected[$i]}" = "1" ]; then
        if [ -d "$AGENTS_UNUSED_DIR/$name" ]; then
            mkdir -p "$AGENTS_SKILLS_DIR"
            mv "$AGENTS_UNUSED_DIR/$name" "$AGENTS_SKILLS_DIR/$name"
            echo -e "  ${GREEN}✓${RESET} Enabled ${BOLD}$name${RESET} ${DIM}(moved to ~/.agents/skills)${RESET}"
            any_change=1
        fi
        local src="$AGENTS_SKILLS_DIR/$name"
        local synced=0
        for target_base in "${COPY_TARGETS[@]}"; do
            mkdir -p "$target_base"
            if [ ! -d "$target_base/$name" ] || ! diff -rq "$src" "$target_base/$name" >/dev/null 2>&1; then
                rm -rf "${target_base:?}/${name:?}"
                cp -R "$src" "$target_base/$name"
                synced=$((synced + 1))
            fi
        done
        if [ $synced -gt 0 ]; then
            echo -e "  ${GREEN}✓${RESET} Synced ${BOLD}$name${RESET} ${DIM}(${synced} target(s))${RESET}"
            any_change=1
        fi
    else
        local removed=0
        for target_base in "${COPY_TARGETS[@]}"; do
            if [ -d "$target_base/$name" ]; then
                rm -rf "${target_base:?}/${name:?}"
                removed=$((removed + 1))
            fi
        done
        if [ -d "$AGENTS_SKILLS_DIR/$name" ]; then
            mkdir -p "$AGENTS_UNUSED_DIR"
            mv "$AGENTS_SKILLS_DIR/$name" "$AGENTS_UNUSED_DIR/$name"
            any_change=1
        fi
        if [ $removed -gt 0 ]; then
            echo -e "  ${RED}✗${RESET} Disabled ${BOLD}$name${RESET} ${DIM}(${removed} copy/copies removed, moved to ~/.agents/skills-unused)${RESET}"
            any_change=1
        fi
    fi

    [ "$any_change" -eq 1 ]
}

# ── Apply install/uninstall changes ──
# Reconciles each target directory to the desired state
# (selected=1 → symlink present; selected=0 → symlink absent).
# Works for fresh installs, partial-install repairs, and cleanup.
apply_changes() {
    local changed=0
    local total_blocked=0

    echo ""

    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        local name="${SKILL_NAMES[$i]}"

        if [ "${SKILL_KIND[$i]}" = "copy" ]; then
            if apply_copy_skill "$i"; then
                changed=$((changed + 1))
            fi
            continue
        fi

        local src="${SKILL_PATHS[$i]}"
        local created=0
        local removed=0
        local blocked=0

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
                    blocked=$((blocked + 1))
                fi
                # Working symlink (to us or an override): leave alone
            done
            total_blocked=$((total_blocked + blocked))
            if [ $created -gt 0 ]; then
                if [ $blocked -eq 0 ]; then
                    echo -e "  ${GREEN}✓${RESET} Installed ${BOLD}$name${RESET} ${DIM}(${created} target(s))${RESET}"
                    skill_cli_install "$name" "$src"
                else
                    echo -e "  ${CYAN}◐${RESET} Partially installed ${BOLD}$name${RESET} ${DIM}(${created} target(s))${RESET}"
                fi
                changed=$((changed + 1))
            fi
            if [ $blocked -gt 0 ]; then
                echo -e "  ${RED}!${RESET} Install incomplete for ${BOLD}$name${RESET} ${DIM}(${blocked} blocked target(s))${RESET}"
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
                skill_cli_uninstall "$name"
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
    if [ $total_blocked -gt 0 ]; then
        return 1
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
        if [ "$i" -eq "$REPO_SKILL_COUNT" ] && [ "$REPO_SKILL_COUNT" -lt "${#SKILL_NAMES[@]}" ]; then
            echo ""
            echo "All skills (~/.agents/skills):"
        fi
        local name="${SKILL_NAMES[$i]}"
        local total
        total="$(target_count_for_kind "${SKILL_KIND[$i]}")"
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

cmd_install_link() {
    local name="$1"
    local src
    local created=0
    local blocked=0
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
            blocked=$((blocked + 1))
            continue
        fi
        if [ ! -L "$link" ] || [ "$(readlink "$link")" != "$src" ]; then
            ln -sfn "$src" "$link"
            created=$((created + 1))
        fi
    done
    if [ "$blocked" -gt 0 ]; then
        echo "Install incomplete: $name blocked in $blocked target(s)" >&2
        exit 1
    fi
    if [ "$created" -eq 0 ] && [ "$(install_count "$name")" -lt "${#TARGETS[@]}" ]; then
        echo "Install incomplete: $name is not installed in all targets" >&2
        exit 1
    fi
    skill_cli_install "$name" "$src"
    echo "Installed: $name"
}

# Enable a "copy" kind skill: move it out of skills-unused (if needed),
# then sync it into COPY_TARGETS. See apply_copy_skill for the same logic
# used by the interactive UI.
cmd_install_copy() {
    local name="$1"
    if [ ! -d "$AGENTS_SKILLS_DIR/$name" ] && [ ! -d "$AGENTS_UNUSED_DIR/$name" ]; then
        echo "Unknown skill: $name" >&2; exit 1
    fi
    if [ -d "$AGENTS_UNUSED_DIR/$name" ]; then
        mkdir -p "$AGENTS_SKILLS_DIR"
        mv "$AGENTS_UNUSED_DIR/$name" "$AGENTS_SKILLS_DIR/$name"
    fi
    local src="$AGENTS_SKILLS_DIR/$name"
    for target_base in "${COPY_TARGETS[@]}"; do
        mkdir -p "$target_base"
        if [ ! -d "$target_base/$name" ] || ! diff -rq "$src" "$target_base/$name" >/dev/null 2>&1; then
            rm -rf "${target_base:?}/${name:?}"
            cp -R "$src" "$target_base/$name"
        fi
    done
    echo "Installed: $name"
}

cmd_install() {
    local name="$1"
    local kind
    kind="$(skill_kind_by_name "$name")" || kind=""
    if [ "$kind" = "copy" ]; then
        cmd_install_copy "$name"
    else
        cmd_install_link "$name"
    fi
}

cmd_uninstall_link() {
    local name="$1"
    local removed=0
    for target_base in "${TARGETS[@]}"; do
        if [ -L "$target_base/$name" ]; then
            rm -f "$target_base/$name"
            removed=$((removed + 1))
        fi
    done
    skill_cli_uninstall "$name"
    if [ $removed -gt 0 ]; then
        echo "Uninstalled: $name"
    else
        echo "Not installed: $name"
    fi
}

# Disable a "copy" kind skill: delete the copies, move the folder from
# ~/.agents/skills to ~/.agents/skills-unused (creating it if needed).
cmd_uninstall_copy() {
    local name="$1"
    local removed=0
    for target_base in "${COPY_TARGETS[@]}"; do
        if [ -d "$target_base/$name" ]; then
            rm -rf "${target_base:?}/${name:?}"
            removed=$((removed + 1))
        fi
    done
    local moved=0
    if [ -d "$AGENTS_SKILLS_DIR/$name" ]; then
        mkdir -p "$AGENTS_UNUSED_DIR"
        mv "$AGENTS_SKILLS_DIR/$name" "$AGENTS_UNUSED_DIR/$name"
        moved=1
    fi
    if [ $removed -gt 0 ] || [ $moved -gt 0 ]; then
        echo "Uninstalled: $name"
    else
        echo "Not installed: $name"
    fi
}

cmd_uninstall() {
    local name="$1"
    local kind
    kind="$(skill_kind_by_name "$name")" || kind=""
    if [ "$kind" = "copy" ]; then
        cmd_uninstall_copy "$name"
    else
        cmd_uninstall_link "$name"
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
