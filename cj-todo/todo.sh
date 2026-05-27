#!/usr/bin/env bash
# todo — the world's most lightweight repo-scoped todo & plan tracker.
#
# Storage (per repo, under <repo-root>/.plans/):
#   TODO.md   — open work (todos + plan index lines)
#   DONE.md   — completed items, archived with a date
#   <slug>.md — one detail file per plan
#
# A plan index line looks like:  - [ ] <name> → .plans/<slug>.md
# Anything matching "→ .plans/" is treated as a plan for display.

set -euo pipefail

# ── colours (only when stdout is a tty) ──
if [ -t 1 ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
  CYAN=$'\033[36m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
  BOLD=''; DIM=''; GREEN=''; YELLOW=''; CYAN=''; RED=''; RESET=''
fi

die() { echo "${RED}error:${RESET} $*" >&2; exit 1; }

# ── locate repo root & storage ──
repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

ROOT="$(repo_root)"
PLANS_DIR="$ROOT/.plans"
TODO_FILE="$PLANS_DIR/TODO.md"
DONE_FILE="$PLANS_DIR/DONE.md"

ensure_store() {
  mkdir -p "$PLANS_DIR"
  [ -f "$TODO_FILE" ] || printf '# TODO\n\n' > "$TODO_FILE"
  [ -f "$DONE_FILE" ] || printf '# Done\n\n' > "$DONE_FILE"
}

today() { date +%Y-%m-%d; }

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
    | cut -c1-50
}

# Strip leading "- [ ] " / "- [x] " checkbox markup from a line.
strip_box() { sed -E 's/^- \[[ xX]\] //'; }

# ── commands ──

cmd_add() {
  [ "$#" -gt 0 ] || die "nothing to add. usage: todo add \"task text\""
  ensure_store
  local text="$*"
  printf -- '- [ ] %s\n' "$text" >> "$TODO_FILE"
  echo "${GREEN}+${RESET} $text"
}

cmd_plan() {
  [ "$#" -gt 0 ] || die "name the plan. usage: todo plan \"plan name\""
  ensure_store
  local name="$*"
  local slug; slug="$(slugify "$name")"
  [ -n "$slug" ] || die "could not derive a filename from \"$name\""
  local file="$PLANS_DIR/$slug.md"
  local rel=".plans/$slug.md"
  if [ -f "$file" ]; then
    echo "${YELLOW}plan already exists:${RESET} $rel"
  else
    {
      printf '# %s\n\n' "$name"
      printf '_Created %s_\n\n' "$(today)"
      printf '## Goal\n\n\n## Steps\n\n- [ ] \n\n## Notes\n\n'
    } > "$file"
    printf -- '- [ ] %s → %s\n' "$name" "$rel" >> "$TODO_FILE"
    echo "${GREEN}+${RESET} plan: $name ${DIM}($rel)${RESET}"
  fi
  echo "$file"
}

# List open items, numbered. Plans get a [plan] tag.
cmd_list() {
  ensure_store
  local n=0 found=0
  while IFS= read -r line; do
    n=$((n + 1)); found=1
    local text; text="$(printf '%s' "$line" | strip_box)"
    if printf '%s' "$text" | grep -q '→ .plans/'; then
      local title="${text%% → *}"
      local ref="${text##* → }"
      printf '  %s%2d.%s [ ] %s %s[plan]%s %s%s%s\n' \
        "$BOLD" "$n" "$RESET" "$title" "$CYAN" "$RESET" "$DIM" "$ref" "$RESET"
    else
      printf '  %s%2d.%s [ ] %s\n' "$BOLD" "$n" "$RESET" "$text"
    fi
  done < <(grep -E '^- \[ \] ' "$TODO_FILE" || true)
  if [ "$found" -eq 0 ]; then
    echo "${DIM}no open todos in ${TODO_FILE/#$HOME/\~}${RESET}"
  fi
}

# Resolve the Nth open item's line number in TODO_FILE.
nth_line_no() {
  local idx="$1"
  grep -nE '^- \[ \] ' "$TODO_FILE" | sed -n "${idx}p" | cut -d: -f1
}

cmd_done() {
  [ "$#" -gt 0 ] || die "which one? usage: todo done <number>"
  ensure_store
  local idx="$1"
  [[ "$idx" =~ ^[0-9]+$ ]] || die "expected a number, got \"$idx\""
  local lineno; lineno="$(nth_line_no "$idx" || true)"
  [ -n "$lineno" ] || die "no open todo #$idx (run 'todo' to see the list)"

  local raw; raw="$(sed -n "${lineno}p" "$TODO_FILE")"
  local text; text="$(printf '%s' "$raw" | strip_box)"

  # archive
  printf -- '- [x] %s (%s)\n' "$text" "$(today)" >> "$DONE_FILE"
  # remove from TODO
  sed -i.bak "${lineno}d" "$TODO_FILE" && rm -f "$TODO_FILE.bak"
  echo "${GREEN}✓${RESET} done: ${text%% → *}"
}

cmd_rm() {
  [ "$#" -gt 0 ] || die "which one? usage: todo rm <number>"
  ensure_store
  local idx="$1"
  [[ "$idx" =~ ^[0-9]+$ ]] || die "expected a number, got \"$idx\""
  local lineno; lineno="$(nth_line_no "$idx" || true)"
  [ -n "$lineno" ] || die "no open todo #$idx"
  local raw; raw="$(sed -n "${lineno}p" "$TODO_FILE")"
  local text; text="$(printf '%s' "$raw" | strip_box)"
  sed -i.bak "${lineno}d" "$TODO_FILE" && rm -f "$TODO_FILE.bak"
  echo "${RED}✗${RESET} removed: ${text%% → *}"
}

cmd_log() {
  ensure_store
  if grep -qE '^- \[x\] ' "$DONE_FILE"; then
    grep -E '^- \[x\] ' "$DONE_FILE" | strip_box | while IFS= read -r l; do
      printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$l"
    done
  else
    echo "${DIM}nothing completed yet${RESET}"
  fi
}

cmd_where() {
  echo "$PLANS_DIR"
}

# Symlink this script onto PATH as `todo`.
cmd_install() {
  local self; self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  local bindir="${1:-$HOME/.local/bin}"
  local target="$bindir/todo"
  mkdir -p "$bindir"
  # Never clobber a real file living exactly where our link would go.
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "${YELLOW}note:${RESET} $target already exists and is not a symlink — leaving it alone."
    echo "      run this script as ./todo.sh, or remove that file and re-run 'todo install'."
    return 0
  fi
  local existing; existing="$(command -v todo 2>/dev/null || true)"
  if [ -n "$existing" ] && [ "$existing" != "$target" ]; then
    echo "${YELLOW}note:${RESET} another 'todo' is earlier on PATH at $existing — it will shadow this one."
  fi
  ln -sfn "$self" "$target"
  chmod +x "$self"
  echo "${GREEN}✓${RESET} linked ${BOLD}todo${RESET} → $target"
  case ":$PATH:" in
    *":$bindir:"*) ;;
    *) echo "${YELLOW}note:${RESET} $bindir is not on your PATH — add it to use 'todo' directly." ;;
  esac
}

cmd_help() {
  cat <<EOF
${BOLD}todo${RESET} — repo-scoped todos & plans (stored in ${DIM}<repo>/.plans/${RESET})

${BOLD}usage${RESET}
  todo                       list open todos & plans (default)
  todo add "<text>"          add a todo
  todo plan "<name>"         create a plan file + index it
  todo done <n>              complete item #n (archives to DONE.md)
  todo rm <n>                delete item #n without archiving
  todo log                   show completed items
  todo where                 print the .plans directory path
  todo install [bindir]      symlink this script as 'todo' (default ~/.local/bin)
  todo help                  this help
EOF
}

# ── dispatch ──
cmd="${1:-list}"; [ "$#" -gt 0 ] && shift || true
case "$cmd" in
  add)            cmd_add "$@" ;;
  plan)           cmd_plan "$@" ;;
  ls|list)        cmd_list "$@" ;;
  done|do|x)      cmd_done "$@" ;;
  rm|del|remove)  cmd_rm "$@" ;;
  log|done-log)   cmd_log "$@" ;;
  where|dir)      cmd_where "$@" ;;
  install)        cmd_install "$@" ;;
  help|-h|--help) cmd_help ;;
  *)              die "unknown command '$cmd' (try: todo help)" ;;
esac
