#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TODO="$REPO_ROOT/cj-todo/todo.sh"
INSTALLER="$REPO_ROOT/install-skill.sh"
TMP_ROOT="$(mktemp -d /private/tmp/skills-tests.XXXXXX)"

cleanup() {
    rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

pass() {
    echo "ok - $*"
}

test_todo_archive_collision() {
    local work="$TMP_ROOT/todo-collision"
    mkdir -p "$work"
    cd "$work"
    git init -q

    "$TODO" plan "Repeatable plan" >/dev/null
    "$TODO" "done" 1 >/dev/null
    "$TODO" plan "Repeatable plan" >/dev/null
    "$TODO" "done" 1 >/dev/null

    local count
    count="$(find .plans/done -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
    [ "$count" = "2" ] || fail "expected 2 archived plans, got $count"
    [ -f .plans/done/repeatable-plan.md ] || fail "missing first archived plan"
    find .plans/done -maxdepth 1 -type f -name 'repeatable-plan-*.md' | grep -q . || fail "missing collision-suffixed archived plan"
    pass "todo archives colliding plan slugs without overwrite"
}

test_installer_blocked_target_fails() {
    local home="$TMP_ROOT/blocked-home"
    mkdir -p "$home/.claude/skills/cj-todo" "$home/.codex/skills/cj-todo" "$home/.copilot/skills/cj-todo"

    if HOME="$home" "$INSTALLER" --install cj-todo >/tmp/skills-test-install.out 2>/tmp/skills-test-install.err; then
        fail "installer succeeded with blocked target directories"
    fi
    grep -q "Install incomplete" /tmp/skills-test-install.err || fail "installer did not explain incomplete install"
    [ ! -e "$home/.local/bin/todo" ] || fail "installer linked companion CLI after failed skill install"
    rm -f /tmp/skills-test-install.out /tmp/skills-test-install.err
    pass "installer fails nonzero when target paths are blocked"
}

test_installer_list_has_no_ansi() {
    local output
    output="$("$INSTALLER" --list)"
    if grep -q $'\033' <<<"$output"; then
        fail "installer --list emitted ANSI escapes without a TTY"
    fi
    pass "installer --list suppresses ANSI escapes when captured"
}

test_todo_archive_collision
test_installer_blocked_target_fails
test_installer_list_has_no_ansi
