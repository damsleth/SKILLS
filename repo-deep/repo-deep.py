#!/usr/bin/env python3
"""repo-deep — tier resolution + repo selection for ONE deep code-quality pass.

The SELECTION half of /repo-deep. This is the *most expensive* routine in the
repo-routine family, so it is strictly one repo at a time and never batched. The
script does the cheap, deterministic part: resolve the target's tier from
`.repo-tiers.json`, refuse the out-of-scope tiers, detect the stack, and — when
called with no arg — nominate the next candidate from REPO-HEALTH.md.

Everything with judgement — the ponytail-audit, the code-review sweep, the
test-gap read, deciding WHICH findings to apply, and the writes — is done by
Claude per SKILL.md, exactly like repo-groom/repo-deps split the script (facts)
from the skill (writes). This script never touches a target repo.

Usage:
    ./repo-deep.py <repo>          # tier key (CLI/mytool), bare name (mytool), or path
    ./repo-deep.py <repo> --json   # machine-readable
    ./repo-deep.py                 # no arg -> nominate from REPO-HEALTH.md
    ./repo-deep.py --root ~/code   # or set REPO_ROOT
"""

import argparse
import json
import os
import pathlib
import re
import sys

# ponytail: constants, not a config file. Refuse-set mirrors repo-groom.py.
REFUSE_TIERS = {"W-ro", "archive", "external"}


# ponytail: load_tiers/resolve/detect_stack copied verbatim from repo-groom.py.
# Style is per-skill duplication, not a shared import — each skill symlinks
# individually into ~/.claude/skills, so a cross-skill import would dangle.
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
    if arg in tiers:
        return arg, tiers[arg], root / arg
    p = pathlib.Path(arg).expanduser()
    if not p.is_absolute():
        p = root / arg
    if p.is_dir():
        try:
            key = str(p.resolve().relative_to(root))
        except ValueError:
            key = None
        return key, (tiers.get(key) if key else None), p
    hits = [k for k in tiers if k == arg or k.endswith("/" + arg)]
    if len(hits) == 1:
        return hits[0], tiers[hits[0]], root / hits[0]
    if len(hits) > 1:
        sys.exit(f"'{arg}' is ambiguous: {', '.join(hits)}. Use the full key.")
    return arg, None, root / arg


def detect_stack(repo):
    """First matching stack wins; a repo can be mixed but we deep-pass the primary."""
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


def has_tests(repo):
    """Cheap heuristic: does a test suite exist at all? (depth-limited walk)."""
    names = ("test", "tests", "__tests__", "spec")
    for d in repo.rglob("*"):
        # ponytail: stop descending into vendored/build dirs, they blow up the walk
        parts = set(d.parts)
        if parts & {"node_modules", ".git", "target", "dist", "build", ".venv"}:
            continue
        low = d.name.lower()
        if d.is_dir() and low in names:
            return True
        if d.is_file() and (low.startswith("test_") or low.endswith(("_test.py",
                "_test.go", ".test.ts", ".test.js", ".spec.ts", ".spec.js"))):
            return True
    return False


def suggest_effort(repo):
    """Scale the code-review effort by rough repo size. Default medium."""
    # ponytail: count source files, not lines — good enough to pick an effort tier.
    exts = (".py", ".rs", ".ts", ".tsx", ".js", ".jsx", ".go", ".cs")
    n = 0
    for f in repo.rglob("*"):
        if f.is_file() and f.suffix in exts and not (
                set(f.parts) & {"node_modules", ".git", "target", "dist", "build", ".venv"}):
            n += 1
            if n > 400:
                break
    if n <= 40:
        return "low"
    if n <= 200:
        return "medium"
    return "high"


def nominate(root, tiers):
    """No-arg mode: pick the next repo for a deep pass.

    Prefer an explicit `/repo-deep <repo>` line in REPO-HEALTH.md's Top actions.
    If none (repo-health only nominates repo-deep for clean-baseline repos, so
    the Top 5 often has none), DERIVE one: a tiered, non-refused repo — flagged
    for the user to confirm, never auto-run.
    """
    report = root / "REPO-HEALTH.md"
    if report.is_file():
        try:
            text = report.read_text()
        except OSError:
            text = ""
        m = re.search(r"/repo-deep\s+([^\s`*]+)", text)
        if m:
            key = m.group(1)
            return {"nominee": key, "tier": tiers.get(key),
                    "source": "REPO-HEALTH.md Top actions (explicit /repo-deep line)",
                    "confirm": True}
    # ponytail: no full parse of the findings table — just fall back to the first
    # non-refused tiered repo as a *suggestion*. Claude re-ranks with judgement.
    for key, tier in tiers.items():
        if tier not in REFUSE_TIERS:
            return {"nominee": key, "tier": tier,
                    "source": ("derived — REPO-HEALTH.md has no explicit /repo-deep "
                               "nomination; CONFIRM with user before running"),
                    "confirm": True}
    return {"nominee": None, "tier": None,
            "source": "no REPO-HEALTH.md and no tiered repos to nominate",
            "confirm": True}


COMMIT_POLICY = {
    "S-priv": "commit + push OK",
    "S-pub": "commit + push OK; releases/tags need approval",
    "W": "NEW BRANCH + local commits only — user pushes/PRs",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", help="tier key, bare name, or path; omit to nominate")
    ap.add_argument("--root", default=os.environ.get("REPO_ROOT", os.path.expanduser("~/code")))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = pathlib.Path(a.root).expanduser().resolve()
    tiers = load_tiers(root)

    if a.repo is None:
        nom = nominate(root, tiers)
        if a.json:
            print(json.dumps(nom, indent=2))
            return
        print("NO ARG — nominating the next repo for a deep pass:\n")
        if nom["nominee"]:
            print(f"  nominee: {nom['nominee']}  (tier {nom['tier']})")
        else:
            print("  nominee: none")
        print(f"  source:  {nom['source']}")
        print("\nConfirm with the user before running the deep pass.")
        return

    key, tier, repo = resolve(root, tiers, a.repo)
    plan = {"repo": key or str(repo), "path": str(repo), "tier": tier,
            "refuse": None, "stack": None, "has_tests": None,
            "suggested_effort": None, "commit_policy": None}

    if not repo.is_dir():
        plan["refuse"] = f"not a directory: {repo}"
    elif tier is None:
        plan["refuse"] = ("untiered — add it to .repo-tiers.json first "
                          "(pick S-priv/S-pub/W); untiered repos are scratch")
    elif tier in REFUSE_TIERS:
        plan["refuse"] = f"tier {tier} — NEVER deep-pass (report-only / out of scope)"

    if plan["refuse"] is None:
        plan["stack"] = detect_stack(repo)
        plan["has_tests"] = has_tests(repo)
        plan["suggested_effort"] = suggest_effort(repo)
        plan["commit_policy"] = COMMIT_POLICY.get(tier, "?")

    if a.json:
        print(json.dumps(plan, indent=2))
        return

    print(f"repo:  {plan['repo']}\npath:  {plan['path']}\ntier:  {plan['tier']}")
    if plan["refuse"]:
        print(f"\nREFUSE: {plan['refuse']}")
        return
    print(f"stack: {plan['stack']}")
    print(f"tests: {'present' if plan['has_tests'] else 'NONE FOUND — flag test gap'}")
    print(f"code-review effort (suggested): {plan['suggested_effort']}  (default medium; user may override)")
    print(f"commit: {plan['commit_policy']}")


if __name__ == "__main__":
    main()
