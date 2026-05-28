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
    RED='\033[31m'; GREEN='\033[32m'; DIM='\033[2m'; RESET='\033[0m'
else
    RED=''; GREEN=''; DIM=''; RESET=''
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
if ! list_output="$("$REPO_ROOT/install-skill.sh" --list 2>&1)"; then
    report "install-skill.sh --list exited nonzero"
fi
if grep -q $'\033' <<<"$list_output"; then
    report "install-skill.sh --list emits ANSI escapes when stdout is not a TTY"
fi

# ── Check 3: shell scripts ──

echo "• shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
    shell_files=("$REPO_ROOT/install-skill.sh" "$REPO_ROOT/scripts/lint.sh")
    shopt -s nullglob
    for f in "$REPO_ROOT"/scripts/*.sh; do
        shell_files+=("$f")
    done
    shopt -u nullglob
    [ -f "$REPO_ROOT/cj-todo/todo.sh" ] && shell_files+=("$REPO_ROOT/cj-todo/todo.sh")
    if ! shellcheck "${shell_files[@]}" 2>/tmp/skills-shellcheck.err; then
        report "shellcheck found issues"
        sed 's/^/      /' /tmp/skills-shellcheck.err >&2
    fi
    rm -f /tmp/skills-shellcheck.err
else
    detail "shellcheck not found; skipping"
fi

# ── Check 4: README skill table drift ──

echo "• README skill table"
expected_skills="$(
    for skill_file in "${skill_files[@]}"; do
        basename "$(dirname "$skill_file")"
    done | sort
)"
readme_skills="$(grep -E '^\| \*\*[^*]+\*\* \|' "$REPO_ROOT/README.md" | sed -E 's/^\| \*\*([^*]+)\*\*.*/\1/' | sort)"
if [ "$expected_skills" != "$readme_skills" ]; then
    report "README skill table does not match discovered */SKILL.md folders"
    detail "Discovered: $(tr '\n' ' ' <<<"$expected_skills" | sed 's/ $//')"
    detail "README:     $(tr '\n' ' ' <<<"$readme_skills" | sed 's/ $//')"
fi

# ── Check 5: agent YAML parses ──

echo "• agent YAML"
agent_yamls=()
shopt -s nullglob
for f in "$REPO_ROOT"/*/agents/*.yaml; do
    agent_yamls+=("$f")
done
shopt -u nullglob
if [ ${#agent_yamls[@]} -gt 0 ]; then
    if command -v ruby >/dev/null 2>&1; then
        if ! ruby -ryaml -e 'ARGV.each { |f| YAML.safe_load(File.read(f), permitted_classes: [], aliases: false) }' "${agent_yamls[@]}" 2>/tmp/skills-yaml.err; then
            report "agent YAML failed to parse"
            sed 's/^/      /' /tmp/skills-yaml.err >&2
        fi
        rm -f /tmp/skills-yaml.err
    else
        detail "ruby not found; skipping YAML parse"
    fi
fi

# ── Check 6: per-skill static checks ──

# Patterns that indicate hardcoded user paths
USER_PATH_RE='/Users/[A-Za-z][A-Za-z0-9_-]+|/home/[A-Za-z][A-Za-z0-9_-]+|~/Code/'

# Agent-specific tool names that won't port across Claude / Codex / Copilot.
# Listed as word-boundary regex alternatives.
BAD_TOOLS=(ask_user_input request_user_input web_search str_replace)

for skill_file in "${skill_files[@]}"; do
    rel="${skill_file#"$REPO_ROOT"/}"
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
