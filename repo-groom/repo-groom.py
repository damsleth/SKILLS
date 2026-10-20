#!/usr/bin/env python3
"""repo-groom — read-only gap analysis for ONE repo's quality baseline.

The DETECTOR half of /repo-groom. It resolves the repo's tier from
`.repo-tiers.json`, detects the stack, and prints what baseline files are
MISSING. It never writes to the target repo — Claude does the writes per
SKILL.md, so it can adapt CI templates, confirm the LICENSE choice, and check
README accuracy with judgement the script doesn't have.

Gap definitions here MUST match repo-health.py exactly, or the sweep nominates
repos this fixer then says are fine.

Usage:
    ./repo-groom.py <repo>            # tier key, bare name, or path
    ./repo-groom.py <repo> --json     # machine-readable plan
    ./repo-groom.py --root ~/code   # or set REPO_ROOT <repo>
"""

import argparse
import json
import os
import pathlib
import sys

# ponytail: constants, not a config file. Edit in place. Mirrors repo-health.py.
REFUSE_TIERS = {"W-ro", "archive", "external"}
CI_TEMPLATE = {  # stack -> which template note (see SKILL.md)
    "python": "a typical Python package repo",
    "rust": "a typical Rust crate repo",
    "node": "minimal conditional (see SKILL.md)",
}


def load_tiers(root):
    f = root / ".repo-tiers.json"
    if not f.is_file():
        return {}
    try:
        data = json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return {k: v.get("tier", "?") for k, v in data.get("tiers", {}).items()}


def resolve(root, tiers, arg):
    """Map the user's arg to a (tier_key, tier, abspath). Keys can hold spaces."""
    # exact tier key wins
    if arg in tiers:
        return arg, tiers[arg], root / arg
    # a path (absolute or relative to root)
    p = pathlib.Path(arg).expanduser()
    if not p.is_absolute():
        p = root / arg
    if p.is_dir():
        try:
            key = str(p.resolve().relative_to(root))
        except ValueError:
            key = None
        return key, (tiers.get(key) if key else None), p
    # bare name -> unique suffix match against tier keys (mytool -> CLI/mytool)
    hits = [k for k in tiers if k == arg or k.endswith("/" + arg)]
    if len(hits) == 1:
        return hits[0], tiers[hits[0]], root / hits[0]
    if len(hits) > 1:
        sys.exit(f"'{arg}' is ambiguous: {', '.join(hits)}. Use the full key.")
    return arg, None, root / arg


def detect_stack(repo):
    """First matching stack wins; a repo can be mixed but we groom the primary."""
    if (repo / "pyproject.toml").is_file() or (repo / "requirements.txt").is_file():
        return "python"
    if (repo / "Cargo.toml").is_file():
        return "rust"
    if (repo / "package.json").is_file():
        return "node"
    if list(repo.glob("*.csproj")) or list(repo.glob("*.sln")):
        return "dotnet"
    if list(repo.glob("*.sh")):
        return "shell"
    return "unknown"


def has_ci(repo):
    # ponytail: identical rule to repo-health so detector and fixer agree.
    return (repo / ".github/workflows").is_dir() or (repo / "azure-pipelines.yml").is_file()


def agents_state(repo):
    """Return one of: ok-agents, ok-claude-symlink, ok-claude-include, missing.

    AGENTS.md is the canonical file for every agent, regardless of harness.
    CLAUDE.md is at most a one-line pointer to it and is never created here —
    a symlink or an import shim is a second place to look for the same content.
    Existing pointers/symlinks are left alone; only the direction is enforced."""
    agents = repo / "AGENTS.md"
    claude = repo / "CLAUDE.md"
    if agents.is_file() and not agents.is_symlink():
        return "ok-agents"
    if agents.is_symlink():
        return "ok-agents-symlink"
    if claude.is_symlink():
        return "ok-claude-symlink"
    if claude.is_file():
        body = ""
        try:
            body = claude.read_text().strip()
        except OSError:
            pass
        if body in ("@AGENTS.md", "@./AGENTS.md"):
            return "ok-claude-include"
        return "claude-only"  # real CLAUDE.md content, needs AGENTS.md normalization
    return "missing"


def has_license(repo):
    return any((repo / n).exists() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt"))


def has_readme(repo):
    return any((repo / n).exists() for n in ("README.md", "README.rst", "README.txt", "README"))


def has_lint(repo, stack):
    if stack == "python":
        if (repo / "ruff.toml").is_file() or (repo / ".ruff.toml").is_file():
            return True
        try:
            return "[tool.ruff" in (repo / "pyproject.toml").read_text()
        except OSError:
            return False
    if stack == "node":
        for n in (".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js",
                  ".prettierrc", ".prettierrc.json", "prettier.config.js"):
            if (repo / n).exists():
                return True
        try:
            pkg = json.loads((repo / "package.json").read_text())
            return any(k in pkg.get("devDependencies", {}) for k in ("eslint", "prettier"))
        except (OSError, json.JSONDecodeError):
            return False
    # rust ships rustfmt/clippy with the toolchain; dotnet/shell: no standard
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="tier key (CLI/mytool), bare name (mytool), or path")
    ap.add_argument("--root", default=os.environ.get("REPO_ROOT", os.path.expanduser("~/code")))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = pathlib.Path(a.root).expanduser().resolve()
    tiers = load_tiers(root)
    key, tier, repo = resolve(root, tiers, a.repo)

    plan = {"repo": key or str(repo), "path": str(repo), "tier": tier,
            "refuse": None, "stack": None, "gaps": [], "already_ok": []}

    if not repo.is_dir():
        plan["refuse"] = f"not a directory: {repo}"
    elif tier is None:
        plan["refuse"] = ("untiered — add it to .repo-tiers.json first "
                          "(pick S-priv/S-pub/W); untiered repos are scratch")
    elif tier in REFUSE_TIERS:
        plan["refuse"] = f"tier {tier} — NEVER groom (report-only / out of scope)"

    if plan["refuse"] is None:
        stack = detect_stack(repo)
        plan["stack"] = stack

        if has_ci(repo):
            plan["already_ok"].append("CI")
        else:
            plan["gaps"].append({
                "item": "CI", "action": f"add {stack} workflow",
                "template": CI_TEMPLATE.get(stack, "no template — propose minimal or skip")})

        ast = agents_state(repo)
        if ast.startswith("ok"):
            plan["already_ok"].append(f"AGENTS.md ({ast})")
        elif ast == "claude-only":
            plan["gaps"].append({"item": "AGENTS.md",
                "action": "normalize: git mv CLAUDE.md AGENTS.md — no symlink, no replacement CLAUDE.md"})
        else:
            plan["gaps"].append({"item": "AGENTS.md", "action": "generate minimal AGENTS.md (/init-style, terse)"})

        if tier == "S-pub" and not has_license(repo):
            plan["gaps"].append({"item": "LICENSE",
                "action": "S-pub + missing: CONFIRM license (default MIT, copyright the repo owner) then write"})
        elif has_license(repo):
            plan["already_ok"].append("LICENSE")

        if has_readme(repo):
            plan["already_ok"].append("README (verify accuracy vs code; flag drift, don't rewrite)")
        else:
            plan["gaps"].append({"item": "README", "action": "add a minimal README"})

        if has_lint(repo, stack):
            plan["already_ok"].append("lint/format")
        else:
            plan["gaps"].append({"item": "lint",
                "action": "ruff (python) / eslint+prettier (node) — offer, don't force"})

        commit = {"S-priv": "commit + push OK",
                  "S-pub": "commit + push OK; releases/tags need approval",
                  "W": "NEW BRANCH + local commits only — user pushes/PRs"}
        plan["commit_policy"] = commit.get(tier, "?")

    if a.json:
        print(json.dumps(plan, indent=2))
        return

    print(f"repo:  {plan['repo']}\npath:  {plan['path']}\ntier:  {plan['tier']}")
    if plan["refuse"]:
        print(f"\nREFUSE: {plan['refuse']}")
        return
    print(f"stack: {plan['stack']}\ncommit: {plan['commit_policy']}\n")
    print("GAPS (to propose in the plan):")
    if plan["gaps"]:
        for g in plan["gaps"]:
            extra = f"  [template: {g['template']}]" if g.get("template") else ""
            print(f"  - {g['item']}: {g['action']}{extra}")
    else:
        print("  none — already at baseline")
    print("\nALREADY OK (leave untouched):")
    for x in plan["already_ok"]:
        print(f"  - {x}")


if __name__ == "__main__":
    main()
