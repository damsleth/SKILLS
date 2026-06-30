#!/usr/bin/env bash
# todo — the world's most lightweight repo-scoped todo & plan tracker.
#
# Filesystem-first, so it works with hand-maintained .plans/ dirs too:
#   <repo>/.plans/TODO.md    — open one-line todos (- [ ] checkboxes)
#   <repo>/.plans/DONE.md    — completed todos, archived with a date
#   <repo>/.plans/<name>.md  — one file per plan (the file *is* the unit of work)
#   <repo>/.plans/done/      — completed plans (files moved here)
#
# Listing shows open todos + every plan file in .plans/. It deliberately does
# NOT turn prose bullets or numbered lists into todos, so narrative TODO.md
# files (an index/ordering of plan files) are left untouched.

set -euo pipefail

# ── colours (only when stdout is a tty) ──
if [ -t 1 ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
  CYAN=$'\033[36m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
  BOLD=''; DIM=''; GREEN=''; YELLOW=''; CYAN=''; RED=''; RESET=''
fi

die() { echo "${RED}error:${RESET} $*" >&2; exit 1; }

# ── global flag ──
# `todo g …`, `todo -g …`, `todo --global …`, or invoking as `todox` stores
# todos in one global dir instead of the current repo's .plans/.
GLOBAL=0
case "$(basename "$0")" in todox) GLOBAL=1 ;; esac
case "${1:-}" in
  g|-g|--global) GLOBAL=1; shift ;;
esac

CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/cj-todo/dir"

# The global todo dir: $TODO_GLOBAL_DIR, else the saved config, else ask once.
global_dir() {
  [ -n "${TODO_GLOBAL_DIR:-}" ] && { printf '%s' "${TODO_GLOBAL_DIR/#\~/$HOME}"; return; }
  [ -s "$CONFIG" ] && { head -n1 "$CONFIG"; return; }
  local def="$HOME/brain/todo" ans=""
  printf 'global todo location? [%s] ' "$def" >&2
  [ -r /dev/tty ] && read -r ans < /dev/tty
  ans="${ans:-$def}"; ans="${ans/#\~/$HOME}"
  mkdir -p "$(dirname "$CONFIG")"
  printf '%s\n' "$ans" > "$CONFIG"
  printf '%s' "$ans"
}

# ── locate repo root & storage ──
repo_root() { git rev-parse --show-toplevel 2>/dev/null || pwd; }

if [ "$GLOBAL" -eq 1 ]; then
  PLANS_DIR="$(global_dir)"          # used directly — no .plans/ suffix
  ROOT="$(dirname "$PLANS_DIR")"     # only for relative-path display
else
  ROOT="$(repo_root)"
  PLANS_DIR="$ROOT/.plans"
fi
TODO_FILE="$PLANS_DIR/TODO.md"
DONE_FILE="$PLANS_DIR/DONE.md"
DONE_DIR="$PLANS_DIR/done"

ensure_store() {
  mkdir -p "$PLANS_DIR"
  [ -f "$TODO_FILE" ] || printf '# TODO\n\n' > "$TODO_FILE"
  [ -f "$DONE_FILE" ] || printf '# Done\n\n' > "$DONE_FILE"
}

today() { date +%Y-%m-%d; }

unique_archive_path() {
  local src="$1"
  local base stem ext dest n
  base="$(basename "$src")"
  stem="${base%.md}"
  ext=".md"
  dest="$DONE_DIR/$base"
  n=2
  while [ -e "$dest" ]; do
    dest="$DONE_DIR/${stem}-$(today)-$n$ext"
    n=$((n + 1))
  done
  printf '%s' "$dest"
}

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
    | cut -c1-50
}

# Strip leading "- [ ] " / "- [x] " checkbox markup from a line.
strip_box() { sed -E 's/^- \[[ xX]\] //'; }

# A plan's display title: its first "# " heading, else the filename.
plan_title() {
  local f="$1" t
  t="$(grep -m1 -E '^#+ ' "$f" 2>/dev/null | sed -E 's/^#+ +//')"
  [ -n "$t" ] || t="$(basename "$f" .md)"
  printf '%s' "$t"
}

# Emit one TSV record per open item, in display order:
#   todo<TAB><line-number-in-TODO.md><TAB><task text>
#   plan<TAB><relative path><TAB><plan title>
enumerate() {
  # read-only: never create the store (bare `todo` on a fresh dir is a noop)
  # Open todos: "- [ ]" lines, skipping legacy "→ .plans/" index lines
  # (the file scan below is the source of truth for plans).
  if [ -f "$TODO_FILE" ]; then
    grep -nE '^- \[ \] ' "$TODO_FILE" 2>/dev/null | while IFS=: read -r ln rest; do
      local text; text="$(printf '%s' "$rest" | strip_box)"
      case "$text" in *"→ .plans/"*) continue ;; esac
      printf 'todo\t%s\t%s\n' "$ln" "$text"
    done || true   # grep exits 1 when there are no todos; don't abort under set -e
  fi
  # Plans: top-level *.md files in .plans/ (not TODO.md/DONE.md, not subdirs).
  local f base
  for f in "$PLANS_DIR"/*.md; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    case "$base" in TODO.md|DONE.md) continue ;; esac
    printf 'plan\t%s\t%s\n' ".plans/$base" "$(plan_title "$f")"
  done
}

# The Nth enumerated record (1-based).
nth_record() { enumerate | sed -n "${1}p"; }

# ── commands ──

cmd_add() {
  [ "$#" -gt 0 ] || die "nothing to add. usage: todo add \"task text\""
  ensure_store
  printf -- '- [ ] %s\n' "$*" >> "$TODO_FILE"
  echo "${GREEN}+${RESET} $*"
}

cmd_plan() {
  [ "$#" -gt 0 ] || die "name the plan. usage: todo plan \"plan name\""
  ensure_store
  local name="$*"
  local slug; slug="$(slugify "$name")"
  [ -n "$slug" ] || die "could not derive a filename from \"$name\""
  local file="$PLANS_DIR/$slug.md"
  if [ -f "$file" ]; then
    echo "${YELLOW}plan already exists:${RESET} .plans/$slug.md"
  else
    {
      printf '# %s\n\n' "$name"
      printf '_Created %s_\n\n' "$(today)"
      printf '## Goal\n\n\n## Steps\n\n- [ ] \n\n## Notes\n\n'
    } > "$file"
    echo "${GREEN}+${RESET} plan: $name ${DIM}(.plans/$slug.md)${RESET}"
  fi
  echo "$file"
}

cmd_list() {
  local n=0 kind target display
  while IFS=$'\t' read -r kind target display; do
    n=$((n + 1))
    if [ "$kind" = plan ]; then
      printf '  %s%2d.%s [ ] %s %s[plan]%s %s%s%s\n' \
        "$BOLD" "$n" "$RESET" "$display" "$CYAN" "$RESET" "$DIM" "$target" "$RESET"
    else
      printf '  %s%2d.%s [ ] %s\n' "$BOLD" "$n" "$RESET" "$display"
    fi
  done < <(enumerate)
  if [ "$n" -eq 0 ]; then
    echo "${DIM}no open todos or plans in ${PLANS_DIR/#$HOME/\~}${RESET}"
  fi
}

cmd_done() {
  [ "$#" -gt 0 ] || die "which one? usage: todo done <number>"
  [[ "$1" =~ ^[0-9]+$ ]] || die "expected a number, got \"$1\""
  local rec; rec="$(nth_record "$1")"
  [ -n "$rec" ] || die "no open item #$1 (run 'todo' to see the list)"
  local kind target display
  IFS=$'\t' read -r kind target display <<<"$rec"
  if [ "$kind" = plan ]; then
    mkdir -p "$DONE_DIR"
    local src archive
    src="$PLANS_DIR/$(basename "$target")"
    archive="$(unique_archive_path "$src")"
    mv "$src" "$archive"
    echo "${GREEN}✓${RESET} done: $display ${DIM}(plan → ${archive#"$ROOT"/})${RESET}"
  else
    printf -- '- [x] %s (%s)\n' "$display" "$(today)" >> "$DONE_FILE"
    sed -i.bak "${target}d" "$TODO_FILE" && rm -f "$TODO_FILE.bak"
    echo "${GREEN}✓${RESET} done: $display"
  fi
}

cmd_rm() {
  [ "$#" -gt 0 ] || die "which one? usage: todo rm <number>"
  [[ "$1" =~ ^[0-9]+$ ]] || die "expected a number, got \"$1\""
  local rec; rec="$(nth_record "$1")"
  [ -n "$rec" ] || die "no open item #$1"
  local kind target display
  IFS=$'\t' read -r kind target display <<<"$rec"
  if [ "$kind" = plan ]; then
    rm -f "$PLANS_DIR/$(basename "$target")"
    echo "${RED}✗${RESET} removed plan file: $display ${DIM}($target)${RESET}"
  else
    sed -i.bak "${target}d" "$TODO_FILE" && rm -f "$TODO_FILE.bak"
    echo "${RED}✗${RESET} removed: $display"
  fi
}

cmd_log() {
  ensure_store
  local shown=0 l f
  while IFS= read -r l; do
    printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$l"; shown=1
  done < <(grep -E '^- \[x\] ' "$DONE_FILE" 2>/dev/null | strip_box)
  if [ -d "$DONE_DIR" ]; then
    for f in "$DONE_DIR"/*.md; do
      [ -e "$f" ] || continue
      printf '  %s✓%s %s %s[plan]%s\n' "$GREEN" "$RESET" "$(plan_title "$f")" "$CYAN" "$RESET"
      shown=1
    done
  fi
  [ "$shown" -eq 0 ] && echo "${DIM}nothing completed yet${RESET}"
}

cmd_where() { echo "$PLANS_DIR"; }

# Symlink this script onto PATH as `todo`.
cmd_install() {
  local self; self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  local bindir="${1:-$HOME/.local/bin}"
  local target="$bindir/todo"
  mkdir -p "$bindir"
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
  ln -sfn "$self" "$bindir/todox"   # todox = todo --global
  chmod +x "$self"
  echo "${GREEN}✓${RESET} linked ${BOLD}todo${RESET} & ${BOLD}todox${RESET} → $bindir"
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
  todo plan "<name>"         create a plan file (.plans/<slug>.md)
  todo done <n>              complete item #n (todo → DONE.md, plan → .plans/done/)
  todo rm <n>                delete item #n (todo line, or plan file)
  todo log                   show completed todos & plans
  todo where                 print the .plans directory path
  todo install [bindir]      symlink this script as 'todo' (default ~/.local/bin)
  todo help                  this help

${BOLD}global${RESET} (one shared store instead of the repo's .plans/)
  todo g add "<text>"        prefix any command with g / -g / --global
  todox add "<text>"         …or use the todox alias
  ${DIM}location is asked once, saved to ~/.config/cj-todo/dir; override w/ \$TODO_GLOBAL_DIR${RESET}

${DIM}Plans are just .md files in .plans/ — drop files in by hand and they show up.${RESET}
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
