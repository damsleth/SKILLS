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

# ── Extra skill folders (user config) ──
#
# ~/.agents/install-skill.json: {"folders": ["~/code/SKILLS-private", ...]}
# Each folder is scanned like this repo (dir/*/SKILL.md + dir/personal/*/)
# and shown as its own group. Added/removed from the interactive menu.

CONFIG_FILE="$HOME/.agents/install-skill.json"

# ponytail: flat {"folders":[...]} parsed with sed, no jq dependency.
# Paths containing a double quote are not supported.
config_folders() {
    [ -f "$CONFIG_FILE" ] || return 0
    tr -d '\n' < "$CONFIG_FILE" | sed 's/.*"folders"[^[]*\[//; s/\].*//' | grep -o '"[^"]*"' | tr -d '"' || true
}

write_config() {
    mkdir -p "$(dirname "$CONFIG_FILE")"
    local sep="" f
    {
        printf '{"folders": ['
        for f in "$@"; do printf '%s"%s"' "$sep" "$f"; sep=", "; done
        printf ']}\n'
    } > "$CONFIG_FILE"
}

CONFIG_FOLDERS=()
while IFS= read -r f; do [ -n "$f" ] && CONFIG_FOLDERS+=("$f"); done < <(config_folders)

# ── Discover skills (subfolders containing SKILL.md) ──
#
# One flat list of entries. Kinds:
#   group — a folder header row (path in SKILL_PATHS, no install state)
#   link  — repo/config-folder skill, symlinked into TARGETS
#   copy  — ~/.agents/skills library skill, copied into COPY_TARGETS
# SKILL_GROUP[i] is the index of the group header a skill belongs to
# (a header points at itself).

SKILL_NAMES=()
SKILL_DESCS=()
SKILL_PATHS=()
SKILL_KIND=()
SKILL_GROUP=()
CUR_GROUP=0

# Lookup a skill's source path by name (returns empty if not found).
skill_path_by_name() {
    local want="$1" i
    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        if [ "${SKILL_NAMES[$i]}" = "$want" ] && [ "${SKILL_KIND[$i]}" != "group" ]; then
            echo "${SKILL_PATHS[$i]}"
            return 0
        fi
    done
    return 1
}

skill_kind_by_name() {
    local want="$1" i
    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        if [ "${SKILL_NAMES[$i]}" = "$want" ] && [ "${SKILL_KIND[$i]}" != "group" ]; then
            echo "${SKILL_KIND[$i]}"
            return 0
        fi
    done
    return 1
}

add_group() {  # <name> <path-as-displayed>
    CUR_GROUP=${#SKILL_NAMES[@]}
    SKILL_NAMES+=("$1"); SKILL_DESCS+=(""); SKILL_PATHS+=("$2")
    SKILL_KIND+=("group"); SKILL_GROUP+=("$CUR_GROUP")
}

add_skill() {  # <dir> <kind>
    local dir="${1%/}" name desc
    name="$(basename "$dir")"
    if skill_path_by_name "$name" >/dev/null 2>&1; then
        echo "Warning: $dir collides with an existing skill name - skipping" >&2
        return 0
    fi
    desc=$(sed -n 's/^description: *//p' "$dir/SKILL.md" | head -1)
    SKILL_NAMES+=("$name"); SKILL_DESCS+=("${desc:-(no description)}"); SKILL_PATHS+=("$dir")
    SKILL_KIND+=("$2"); SKILL_GROUP+=("$CUR_GROUP")
}

# Scan a skills folder: dir/*/ (public) and dir/personal/*/ (gitignored,
# optional - most clones won't have one).
scan_folder() {
    local d
    for d in "$1"/*/ "$1"/personal/*/; do
        [ "$(basename "$d")" = "personal" ] && continue
        [ -f "$d/SKILL.md" ] && add_skill "$d" link
    done
    return 0
}

shopt -s nullglob
add_group "$(basename "$SCRIPT_DIR")" "$SCRIPT_DIR"
scan_folder "$SCRIPT_DIR"

for f in "${CONFIG_FOLDERS[@]}"; do
    d="${f/#\~/$HOME}"
    add_group "$(basename "$d")" "$f"
    if [ -d "$d" ]; then scan_folder "$d"; else echo "Warning: skills folder $f not found" >&2; fi
done

# The "all skills" library: real directories in ~/.agents/skills (enabled)
# and ~/.agents/skills-unused (disabled). Symlinks inside ~/.agents/skills
# are repo skills mirrored there via TARGETS above — never listed here.
add_group "All skills" "$AGENTS_SKILLS_DIR"
for d in "$AGENTS_SKILLS_DIR"/*/; do
    [ -L "${d%/}" ] && continue
    [ -f "$d/SKILL.md" ] && add_skill "$d" copy
done
for d in "$AGENTS_UNUSED_DIR"/*/; do
    [ -f "$d/SKILL.md" ] && add_skill "$d" copy
done
# Hide the library header when the library is empty.
if [ "$CUR_GROUP" -eq $((${#SKILL_NAMES[@]} - 1)) ]; then
    unset "SKILL_NAMES[$CUR_GROUP]" "SKILL_DESCS[$CUR_GROUP]" "SKILL_PATHS[$CUR_GROUP]" "SKILL_KIND[$CUR_GROUP]" "SKILL_GROUP[$CUR_GROUP]"
fi
shopt -u nullglob

if [ "$(printf '%s\n' "${SKILL_KIND[@]}" | grep -vc group)" -eq 0 ]; then
    echo "No skills found (folders with SKILL.md) in $SCRIPT_DIR or $AGENTS_SKILLS_DIR"
    exit 1
fi

# Is this group header a user-configured folder (removable from the menu)?
is_config_group() {
    local f
    for f in "${CONFIG_FOLDERS[@]}"; do [ "$f" = "${SKILL_PATHS[$1]}" ] && return 0; done
    return 1
}

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

# Fuzzy (subsequence) match: every character of needle appears in haystack
# in order, not necessarily contiguous. Both args are expected lowercase
# already. Empty needle matches everything.
fuzzy_match() {
    local haystack="$1" needle="$2"
    [ -z "$needle" ] && return 0
    local i=0 hlen=${#haystack} nlen=${#needle} ni=0
    while [ "$i" -lt "$hlen" ] && [ "$ni" -lt "$nlen" ]; do
        [ "${haystack:$i:1}" = "${needle:$ni:1}" ] && ni=$((ni + 1))
        i=$((i + 1))
    done
    [ "$ni" -eq "$nlen" ]
}

# Match rule for one skill: true fuzzy (subsequence) against the name alone
# — good for typo/abbreviation search like "cjvd" -> cj-voice-dna — OR every
# whitespace-separated word of the query is a literal substring somewhere in
# the full haystack (name + description). Subsequence matching against a
# whole paragraph matches almost any short query, so description search
# needs literal word containment instead of fuzzy. Both args lowercase
# already; haystack is "name description".
filter_match() {
    local haystack="$1" query="$2"
    [ -z "$query" ] && return 0
    fuzzy_match "${haystack%% *}" "$query" && return 0
    local words word
    read -ra words <<< "$query"
    for word in "${words[@]}"; do
        case "$haystack" in
            *"$word"*) ;;
            *) return 1 ;;
        esac
    done
    return 0
}

# Recompute which skill indices match the current filter_query, and keep
# the cursor on the same skill if it's still visible (else clamp). Reads
# and writes locals from the calling interactive_menu frame.
recompute_filter() {
    local prev_idx=""
    [ "${#visible_indices[@]}" -gt 0 ] && prev_idx="${visible_indices[$cursor_pos]:-}"

    local q_lower
    q_lower="$(printf '%s' "$filter_query" | tr '[:upper:]' '[:lower:]')"
    visible_indices=()
    # Two passes: skills match on their own text; a group header is shown
    # when any of its skills match (or always, with no filter, so empty
    # folders can still be removed).
    local i matched=()
    for ((i = 0; i < count; i++)); do
        matched[i]=0
        if [ "${SKILL_KIND[$i]}" = "group" ]; then
            [ -z "$q_lower" ] && matched[i]=1
        elif filter_match "${SEARCH_HAYSTACK[$i]}" "$q_lower"; then
            matched[i]=1
            matched[${SKILL_GROUP[$i]}]=1
        fi
    done
    for ((i = 0; i < count; i++)); do
        [ "${matched[$i]}" = "1" ] && visible_indices+=("$i")
    done

    cursor_pos=0
    if [ -n "$prev_idx" ] && [ "${#visible_indices[@]}" -gt 0 ]; then
        # macOS/BSD `seq 0 -1` reverses instead of emitting nothing like
        # GNU seq, so this loop must never run against an empty array.
        local k
        for ((k = 0; k < ${#visible_indices[@]}; k++)); do
            if [ "${visible_indices[$k]}" = "$prev_idx" ]; then
                cursor_pos=$k
                break
            fi
        done
    fi
    local max_pos=$((${#visible_indices[@]} - 1))
    [ "$max_pos" -lt 0 ] && max_pos=0
    [ "$cursor_pos" -gt "$max_pos" ] && cursor_pos=$max_pos
    scroll_offset=0
}

# Group header checkbox state: 1 when the group has skills and all are
# selected. Reads `selected` from the calling interactive_menu frame.
group_all_selected() {
    local g="$1" j any=0
    for ((j = 0; j < count; j++)); do
        [ "${SKILL_GROUP[$j]}" = "$g" ] && [ "${SKILL_KIND[$j]}" != "group" ] || continue
        any=1
        [ "${selected[$j]}" = "1" ] || return 1
    done
    [ "$any" -eq 1 ]
}

# Set every skill in group g to value v (0/1).
set_group() {
    local g="$1" v="$2" j
    for ((j = 0; j < count; j++)); do
        [ "${SKILL_GROUP[$j]}" = "$g" ] && [ "${SKILL_KIND[$j]}" != "group" ] && selected[j]="$v"
    done
    return 0
}

# Add/remove a config folder, then re-exec so discovery runs again.
# Simpler than mutating every parallel array in place.
restart_with_folders() {
    write_config "$@"
    cleanup
    trap - EXIT
    exec "$0"
}

# Print one redraw line (same backslash color-code interpretation as
# `echo -e`), then clear to end of line. Redrawing in place without a full
# screen clear avoids flicker, but a shorter line doesn't erase whatever a
# longer line left behind at the same row in the previous frame — this
# does, per line, without blanking the whole screen first.
line() {
    printf '%b\033[K\n' "$1"
}

interactive_menu() {
    local count=${#SKILL_NAMES[@]}

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
    local SEARCH_HAYSTACK=()
    for ((i = 0; i < count; i++)); do
        local name="${SKILL_NAMES[$i]}"
        local kind="${SKILL_KIND[$i]}"
        if [ "$kind" = "group" ]; then
            # Headers have no install state; 0/0 keeps them out of the
            # change indicators and summary counts.
            actual_count+=("0"); actual_total+=("0"); selected+=("0")
            SEARCH_HAYSTACK[i]=""
            continue
        fi
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
        SEARCH_HAYSTACK[i]="$(printf '%s %s' "$name" "${SKILL_DESCS[$i]}" | tr '[:upper:]' '[:lower:]')"
    done

    # Switch to the alternate screen and hide the cursor; restore both on
    # exit. The alternate screen keeps the menu off the user's normal
    # scrollback, and combined with the home+redraw+trim approach below
    # (instead of clear-then-redraw every frame) avoids the blank-frame
    # flicker of erasing the whole screen before repainting it.
    tput smcup 2>/dev/null || true
    tput civis 2>/dev/null || true
    cleanup() { tput cnorm 2>/dev/null || true; tput rmcup 2>/dev/null || true; }
    trap cleanup EXIT

    # Scrolling viewport: only render as many items as fit the terminal
    # height, keeping the cursor inside the visible window. Without this,
    # a list taller than the terminal scrolls the terminal itself and the
    # cursor can end up above the visible area.
    local scroll_offset=0
    # "t" hides/shows description lines. "/" opens live fuzzy-filter typing
    # (matches name + description); enter commits it, esc clears it.
    local show_desc=1
    local filter_mode=0
    local filter_query=""
    local status_msg=""
    local visible_indices=()
    local cursor_pos=0
    recompute_filter

    # Wrapped descriptions are cached per terminal width: wrapping forks a
    # `fold` per skill, and doing that on every keypress made navigation lag.
    local wrapped_desc=() desc_lines=() cached_width=-1

    while true; do
        local term_rows=24 term_cols=80 size
        # One fork for both dimensions; needs the tty, not stdout.
        size="$(stty size </dev/tty 2>/dev/null)" && read -r term_rows term_cols <<< "$size"
        # Descriptions wrap to the full terminal width instead of being
        # truncated, so item height varies — a 6-char indent is reserved.
        local text_width=$((term_cols - 6))
        [ "$text_width" -lt 20 ] && text_width=20

        local i
        if [ "$text_width" -ne "$cached_width" ]; then
            for ((i = 0; i < count; i++)); do
                if [ "${SKILL_KIND[$i]}" = "group" ]; then
                    wrapped_desc[i]=""; desc_lines[i]=0
                    continue
                fi
                wrapped_desc[i]="$(printf '%s' "${SKILL_DESCS[$i]}" | fold -s -w "$text_width")"
                local nl="${wrapped_desc[$i]//[!$'\n']/}"
                desc_lines[i]=$((${#nl} + 1))
            done
            cached_width=$text_width
        fi

        local visible_count=${#visible_indices[@]}
        local cursor=-1
        [ "$visible_count" -gt 0 ] && cursor="${visible_indices[$cursor_pos]}"

        # Rows each visible item occupies: the name line, its wrapped
        # description lines (if shown), and a spacer above group headers.
        local item_height=()
        local vi
        for ((vi = 0; vi < visible_count; vi++)); do
            i="${visible_indices[$vi]}"
            local h=1
            [ "$show_desc" = "1" ] && h=$((h + desc_lines[i]))
            [ "${SKILL_KIND[$i]}" = "group" ] && [ "$vi" -gt 0 ] && h=$((h + 1))
            item_height[vi]=$h
        done

        # Fixed rows: header (4) + more-above/below (2) + blank + summary
        # (2) = 8, plus the trailing newline after the last line and one
        # row of slack. Overflowing the terminal scrolls the header away.
        local available=$((term_rows - 10))
        [ "$available" -lt 3 ] && available=3

        # Keep the cursor inside the window. Items have variable height,
        # so this is a greedy line-budget fit rather than fixed-size math.
        if [ "$visible_count" -eq 0 ]; then
            scroll_offset=0
        elif [ "$cursor_pos" -lt "$scroll_offset" ]; then
            scroll_offset=$cursor_pos
        else
            local used=0 j
            for ((j = scroll_offset; j <= cursor_pos; j++)); do
                used=$((used + item_height[j]))
            done
            if [ "$used" -gt "$available" ]; then
                # Anchor the cursor as the last visible item: walk backward
                # accumulating heights until the budget would be exceeded.
                local budget=0 start=$cursor_pos
                for ((j = cursor_pos; j >= 0; j--)); do
                    budget=$((budget + item_height[j]))
                    [ "$budget" -gt "$available" ] && break
                    start=$j
                done
                scroll_offset=$start
            fi
        fi
        [ "$scroll_offset" -lt 0 ] && scroll_offset=0

        # From scroll_offset, fit forward as many items as the budget allows.
        local window_end=$scroll_offset used=0
        for ((j = scroll_offset; j < visible_count; j++)); do
            used=$((used + item_height[j]))
            if [ "$used" -gt "$available" ] && [ "$j" -gt "$scroll_offset" ]; then
                break
            fi
            window_end=$j
        done

        # Redraw in place: move to home and overwrite in place rather than
        # clearing first — clearing then redrawing paints a blank frame in
        # between, which is what causes the visible flicker.
        printf '\033[H'
        line "${BOLD}Skill Manager${RESET}  ${DIM}($SCRIPT_DIR)${RESET}"
        if [ "$filter_mode" = "1" ]; then
            line "${DIM}type to filter  ·  enter confirm  ·  esc cancel${RESET}"
            line "${CYAN}/${RESET}${filter_query}${DIM}▌${RESET}"
        else
            line "${DIM}↑/↓ navigate  ·  space toggle  ·  t descriptions  ·  / filter  ·  enter apply  ·  q quit${RESET}"
            if [ -n "$status_msg" ]; then
                line "  ${RED}${status_msg}${RESET}"
                status_msg=""
            elif [ -n "$filter_query" ]; then
                line "  ${DIM}filter:${RESET} ${filter_query} ${DIM}(${visible_count} match(es) — esc to clear)${RESET}"
            else
                line "${DIM}a add skills folder  ·  ctrl+d remove folder (on a folder header)${RESET}"
            fi
        fi
        line ""

        if [ "$visible_count" -eq 0 ]; then
            line "  ${DIM}No matches${RESET}"
        fi

        if [ "$scroll_offset" -gt 0 ]; then
            line "  ${DIM}↑ ${scroll_offset} more above${RESET}"
        fi

        if [ "$visible_count" -gt 0 ]; then
            for ((vi = scroll_offset; vi <= window_end; vi++)); do
                i="${visible_indices[$vi]}"
                local name="${SKILL_NAMES[$i]}"

                local prefix=""
                if [ "$vi" -eq "$cursor_pos" ]; then
                    prefix="${CYAN}${ARROW}${RESET} "
                else
                    prefix="  "
                fi

                if [ "${SKILL_KIND[$i]}" = "group" ]; then
                    [ "$vi" -gt 0 ] && line ""
                    if group_all_selected "$i"; then selected[i]=1; else selected[i]=0; fi
                    local gbox="${DIM}${EMPTY}${RESET}"
                    [ "${selected[$i]}" = "1" ] && gbox="${GREEN}${CHECK}${RESET}"
                    line "${prefix}${gbox}  ${BOLD}${name}${RESET} ${DIM}(${SKILL_PATHS[$i]})${RESET}"
                    continue
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

                line "${prefix}${checkbox}  ${BOLD}${name}${RESET}${indicator}"
                if [ "$show_desc" = "1" ]; then
                    while IFS= read -r descline; do
                        line "      ${DIM}${descline}${RESET}"
                    done <<< "${wrapped_desc[$i]}"
                fi
            done
        fi

        if [ "$window_end" -lt $((visible_count - 1)) ]; then
            line "  ${DIM}↓ $((visible_count - 1 - window_end)) more below${RESET}"
        fi

        line ""

        # Count pending changes across ALL skills (not just the filtered
        # view) by comparing desired (selected) vs actual.
        local installs=0 repairs=0 uninstalls=0
        for ((i = 0; i < count; i++)); do
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
            line "  ${summary}  ${DIM}— press enter to apply${RESET}"
        else
            line "  ${DIM}No changes${RESET}"
        fi

        # Erase any leftover content below this frame (e.g. the previous
        # frame had more lines — toggling descriptions off, or a filter
        # narrowing the list, both shrink the frame).
        printf '\033[J'

        # Read single keypress
        IFS= read -rsn1 key

        if [ "$filter_mode" = "1" ]; then
            case "$key" in
                '')  # Enter — commit filter, resume navigation
                    filter_mode=0
                    ;;
                $'\x7f'|$'\x08')  # Backspace
                    filter_query="${filter_query%?}"
                    recompute_filter
                    ;;
                $'\x1b')  # Esc — cancel typing and clear the filter
                    filter_query=""
                    filter_mode=0
                    recompute_filter
                    ;;
                *)
                    if [ -n "$key" ]; then
                        filter_query+="$key"
                        recompute_filter
                    fi
                    ;;
            esac
            continue
        fi

        case "$key" in
            A|k)  # Up / k
                [ "$cursor_pos" -gt 0 ] && cursor_pos=$((cursor_pos - 1))
                ;;
            B|j)  # Down / j
                [ "$cursor_pos" -lt $((visible_count - 1)) ] && cursor_pos=$((cursor_pos + 1))
                ;;
            ' ')  # Space — toggle (a group header toggles all its skills)
                if [ "$cursor" -ge 0 ] && [ "${SKILL_KIND[$cursor]}" = "group" ]; then
                    if group_all_selected "$cursor"; then set_group "$cursor" 0; else set_group "$cursor" 1; fi
                elif [ "$cursor" -ge 0 ]; then
                    if [ "${selected[$cursor]}" = "1" ]; then
                        selected[cursor]="0"
                    else
                        selected[cursor]="1"
                    fi
                fi
                ;;
            a)    # Add a skills folder to the config, then rescan
                local newdir
                tput cnorm 2>/dev/null || true
                printf '\n'
                # Esc cancels: bind it to wipe the line and submit a lone
                # ESC char, which we treat as "nothing entered" below.
                bind '"\e": "\C-a\C-k\C-v\C-[\n"' 2>/dev/null || true
                IFS= read -rep "  skills folder to add (esc cancels): " newdir || newdir=""
                bind -r '\e' 2>/dev/null || true
                tput civis 2>/dev/null || true
                newdir="${newdir%/}"
                local expanded="${newdir/#\~/$HOME}"
                if [ -z "$newdir" ] || [ "$newdir" = $'\x1b' ]; then
                    :
                elif [ ! -d "$expanded" ]; then
                    status_msg="not a directory: $newdir"
                elif ! compgen -G "$expanded/*/SKILL.md" >/dev/null && ! compgen -G "$expanded/personal/*/SKILL.md" >/dev/null; then
                    status_msg="no skills (*/SKILL.md) found in $newdir"
                else
                    restart_with_folders "${CONFIG_FOLDERS[@]}" "$newdir"
                fi
                ;;
            $'\x04')  # Ctrl+D — remove a config folder reference (not the folder)
                if [ "$cursor" -ge 0 ] && [ "${SKILL_KIND[$cursor]}" = "group" ] && is_config_group "$cursor"; then
                    local yn
                    printf '\n  Remove %s from the skills-folder list? [y/N] ' "${SKILL_PATHS[$cursor]}"
                    IFS= read -rsn1 yn
                    if [ "$yn" = "y" ] || [ "$yn" = "Y" ]; then
                        local keep=() f
                        for f in "${CONFIG_FOLDERS[@]}"; do [ "$f" = "${SKILL_PATHS[$cursor]}" ] || keep+=("$f"); done
                        restart_with_folders "${keep[@]}"
                    fi
                elif [ "$cursor" -ge 0 ] && [ "${SKILL_KIND[$cursor]}" = "group" ]; then
                    status_msg="built-in folder, cannot be removed"
                fi
                ;;
            t)    # Toggle description visibility
                if [ "$show_desc" = "1" ]; then show_desc=0; else show_desc=1; fi
                ;;
            /)    # Enter filter mode (keeps any existing query to refine)
                filter_mode=1
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
            $'\x1b')  # Escape sequence — arrow key, or a lone Esc clears an active filter
                local rest1 rest2
                if IFS= read -rsn1 -t 0.05 rest1 2>/dev/null && [ "$rest1" = "[" ]; then
                    IFS= read -rsn1 -t 0.05 rest2 2>/dev/null || true
                    case "$rest2" in
                        A) [ "$cursor_pos" -gt 0 ] && cursor_pos=$((cursor_pos - 1)) ;;
                        B) [ "$cursor_pos" -lt $((visible_count - 1)) ] && cursor_pos=$((cursor_pos + 1)) ;;
                    esac
                elif [ -n "$filter_query" ]; then
                    filter_query=""
                    recompute_filter
                fi
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

        [ "${SKILL_KIND[$i]}" = "group" ] && continue
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
    echo ""
    echo "Extra skill folders are listed in $CONFIG_FILE and managed from the UI (a / backspace)."
}

cmd_list() {
    for i in $(seq 0 $((${#SKILL_NAMES[@]} - 1))); do
        local name="${SKILL_NAMES[$i]}"
        if [ "${SKILL_KIND[$i]}" = "group" ]; then
            [ "$i" -gt 0 ] && echo ""
            echo "$name (${SKILL_PATHS[$i]}):"
            continue
        fi
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
