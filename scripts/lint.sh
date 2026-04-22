#!/usr/bin/env bash
# Static lint checks for SKILL.md files.
# Catches the bug classes we've seen: hardcoded user paths, agent-specific
# tool names in prose, and broken frontmatter.
#
# Usage:
#   ./scripts/lint.sh            # lint all tracked skills
#   ./scripts/lint.sh --all      # lint tracked + personal/ (gitignored)
#
# Exits nonzero on any finding so it works as a pre-commit hook.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

INCLUDE_PERSONAL=0
[ "${1:-}" = "--all" ] && INCLUDE_PERSONAL=1

# ── Colors ──
if [ -t 1 ]; then
    RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; DIM='\033[2m'; RESET='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; DIM=''; RESET=''
fi

fail=0
findings=0

report() {
    findings=$((findings + 1))
    fail=1
    echo -e "  ${RED}!${RESET} $1" >&2
}

detail() {
    echo -e "      ${DIM}$1${RESET}" >&2
}

# ── Discover skill files ──

skill_files=()
shopt -s nullglob
for f in "$REPO_ROOT"/*/SKILL.md; do
    skill_files+=("$f")
done
if [ $INCLUDE_PERSONAL -eq 1 ]; then
    for f in "$REPO_ROOT"/personal/*/SKILL.md; do
        skill_files+=("$f")
    done
fi
shopt -u nullglob

if [ ${#skill_files[@]} -eq 0 ]; then
    echo "No skills found (need */SKILL.md)" >&2
    exit 1
fi

echo "Linting ${#skill_files[@]} skill(s)..."

# ── Check 1: installer syntax ──

echo ""
echo "• install-skill.sh syntax"
if ! bash -n "$REPO_ROOT/install-skill.sh" 2>/dev/null; then
    report "install-skill.sh has syntax errors"
    bash -n "$REPO_ROOT/install-skill.sh" 2>&1 | sed 's/^/      /' >&2
fi

# ── Check 2: installer --list runs clean ──

echo "• install-skill.sh --list"
if ! "$REPO_ROOT/install-skill.sh" --list >/dev/null 2>&1; then
    report "install-skill.sh --list exited nonzero"
fi

# ── Check 3: per-skill static checks ──

# Patterns that indicate hardcoded user paths
USER_PATH_RE='/Users/[A-Za-z][A-Za-z0-9_-]+|/home/[A-Za-z][A-Za-z0-9_-]+|~/Code/'

# Agent-specific tool names that won't port across Claude / Codex / Copilot.
# Listed as word-boundary regex alternatives.
BAD_TOOLS=(ask_user_input request_user_input web_search str_replace)

for skill_file in "${skill_files[@]}"; do
    rel="${skill_file#"$REPO_ROOT"/}"
    skill_dir="$(dirname "$skill_file")"
    echo ""
    echo "• $rel"

    # 3a: frontmatter
    if ! head -1 "$skill_file" | grep -q '^---$'; then
        report "$rel: missing YAML frontmatter (first line is not '---')"
        continue
    fi
    fm="$(sed -n '2,/^---$/{/^---$/q;p;}' "$skill_file")"
    if ! grep -q '^name:' <<<"$fm"; then
        report "$rel: missing 'name' field in frontmatter"
    fi
    if ! grep -q '^description:' <<<"$fm"; then
        report "$rel: missing 'description' field in frontmatter"
    fi

    # 3b: hardcoded user paths
    if matches="$(grep -nE "$USER_PATH_RE" "$skill_file" || true)" && [ -n "$matches" ]; then
        report "$rel: contains hardcoded user paths"
        while IFS= read -r line; do detail "$line"; done <<<"$matches"
    fi

    # 3c: agent-specific tool names
    for tool in "${BAD_TOOLS[@]}"; do
        if matches="$(grep -nE "\b${tool}\b" "$skill_file" || true)" && [ -n "$matches" ]; then
            report "$rel: references agent-specific tool '$tool'"
            while IFS= read -r line; do detail "$line"; done <<<"$matches"
        fi
    done
done

echo ""
if [ $fail -eq 0 ]; then
    echo -e "${GREEN}✓${RESET} All checks passed"
else
    echo -e "${RED}✗${RESET} $findings finding(s)"
    exit 1
fi
