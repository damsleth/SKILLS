#!/usr/bin/env python3
"""repo-health — read-only weekly sweep over ~/code repos.

Never writes to any repo. Only output is REPO-HEALTH.md at the root of the
code dir (which is not itself a git repo).

Usage:
    ./repo-health.py [--root ~/code] [--out REPO-HEALTH.md] [--network]
                     [--jobs 12] [--stale-days 180] [--stdout]
"""

import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

# ponytail: every knob below is a constant, not a config file. Edit in place.
SKIP_TIERS = {"archive", "external"}
GIT_TIMEOUT = 25          # seconds per local git call
LSREMOTE_TIMEOUT = 6      # seconds, only with --network
MAX_DEPTH = 3             # tier keys are depth 1-2; 3 catches strays
TOP_FILES = 5             # dirty files shown per repo

# Agent identities in a Co-authored-by trailer. ponytail: match the identity,
# not the trailer key — real humans co-author too, and their trailers stay.
AGENT_RE = re.compile(
    r"noreply@anthropic\.com|\bcopilot\b|\bdevin\b|\bcursor\b|\bcodex\b",
    re.I)

# GIT_OPTIONAL_LOCKS=0 keeps `git status` from opportunistically rewriting
# .git/index — that is what makes this sweep genuinely read-only.
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}


def git(repo, *args, timeout=GIT_TIMEOUT, err=False):
    """Run a git command. Returns (ok, stdout) — or (ok, stderr) if err=True."""
    try:
        p = subprocess.run(
            ["git", "--no-optional-locks", "-c", "core.quotepath=off",
             "-C", str(repo), *args],
            capture_output=True, text=True, env=ENV, timeout=timeout,
        )
        return p.returncode == 0, (p.stderr if err else p.stdout).strip()
    except (subprocess.TimeoutExpired, OSError):
        return False, "timed out"


# ── discovery ────────────────────────────────────────────────────────────

def load_tiers(root):
    f = root / ".repo-tiers.json"
    if not f.is_file():
        return None
    try:
        data = json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return {k: v.get("tier", "?") for k, v in data.get("tiers", {}).items()}


def discover(root):
    """Relative paths of git repos under root, up to MAX_DEPTH deep."""
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        rel = pathlib.Path(dirpath).relative_to(root)
        depth = 0 if str(rel) == "." else len(rel.parts)
        if ".git" in dirnames:
            found.append(str(rel))
            dirnames[:] = []          # don't descend into a repo
            continue
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        # ponytail: one hardcoded ignore list beats a .gitignore parser.
        dirnames[:] = [d for d in dirnames if not d.startswith(".")
                       and d not in ("node_modules", "venv", "target", "dist")]
    return sorted(x for x in found if x != ".")


def unversioned(root, repos):
    """Top-level dirs that are neither repos nor inside one. Cheap heuristic."""
    inside = {r.split("/")[0] for r in repos}
    out = []
    for d in sorted(p.name for p in root.iterdir() if p.is_dir()):
        if d.startswith(".") or d in inside:
            continue
        # a container dir (e.g. WEB/) holding only repos is fine
        if any(r.startswith(d + "/") for r in repos):
            continue
        out.append(d)
    return out


# ── per-repo checks ──────────────────────────────────────────────────────

def check(root, rel, tier, network, stale_days):
    repo = root / rel
    r = {"repo": rel, "tier": tier, "notes": [], "score": 0}

    ok, log = git(repo, "log", "-1", "--format=%H %ct")
    if not ok:
        # ponytail: no `git fsck` — too slow for a weekly sweep. The stderr
        # line already distinguishes "missing refs/" from "bad object".
        _, why = git(repo, "log", "-1", err=True)
        why = (why.splitlines() or ["unknown"])[0].removeprefix("fatal: ")
        r["broken"] = why
        r["notes"].append(f"**BROKEN** git state — {why}")
        r["score"] = 1000
        return r
    r["last_commit"] = int(log.split()[1]) if len(log.split()) > 1 else 0

    # One call: dirty files + ahead/behind + branch name.
    ok, st = git(repo, "status", "--porcelain=v2", "--branch")
    dirty = []
    if ok:
        for line in st.splitlines():
            if line.startswith("# branch.head"):
                r["branch"] = line.split(maxsplit=2)[-1]
            elif line.startswith("# branch.ab"):
                a, b = line.split()[2:4]
                r["ahead"], r["behind"] = int(a), abs(int(b))
            elif line.startswith("# branch.upstream"):
                r["upstream"] = True
            elif not line.startswith("#"):
                # porcelain v2 field counts are fixed per record type; paths can
                # contain spaces (`MIM Scripts`) so never rsplit on whitespace.
                tag = line[0]
                if tag == "1":
                    p = line.split(" ", 8)[8]
                elif tag == "2":                       # rename: path\torigPath
                    p = line.split(" ", 9)[9].split("\t")[0]
                elif tag == "u":
                    p = line.split(" ", 10)[10]
                else:                                  # ? untracked, ! ignored
                    p = line[2:]
                dirty.append(p.strip('"'))
    r["dirty"] = dirty
    if dirty:
        r["notes"].append(f"{len(dirty)} dirty: " +
                          ", ".join(f"`{f}`" for f in dirty[:TOP_FILES]) +
                          (" …" if len(dirty) > TOP_FILES else ""))
        r["score"] += min(len(dirty), 20) * 2
    if r.get("ahead"):
        r["notes"].append(f"{r['ahead']} unpushed")
        r["score"] += min(r["ahead"], 10) * 3
    if r.get("behind"):
        r["notes"].append(f"{r['behind']} unpulled")
        r["score"] += 1
    if not r.get("upstream") and r.get("branch", "").lower() != "(detached)":
        r["notes"].append("no upstream")
        r["score"] += 2

    # stale local branches: merged into HEAD, or untouched > stale_days
    cutoff = time.time() - stale_days * 86400
    ok, refs = git(repo, "for-each-ref", "refs/heads",
                   "--format=%(refname:short) %(committerdate:unix)")
    _, merged = git(repo, "branch", "--merged", "HEAD", "--format=%(refname:short)")
    merged = {b for b in merged.split() if b != r.get("branch")}
    stale = set(merged)
    for line in refs.splitlines() if ok else []:
        name, _, ts = line.rpartition(" ")
        if name != r.get("branch") and ts.isdigit() and int(ts) < cutoff:
            stale.add(name)
    if stale:
        r["stale_branches"] = sorted(stale)
        r["notes"].append(f"{len(stale)} stale branch(es): " +
                          ", ".join(sorted(stale)[:3]))
        r["score"] += len(stale)

    # Baseline files — only expected of tiered repos. ponytail: untiered repos
    # are scratch until the user tiers them; nagging them buries the real signal.
    missing = []
    if tier != "untiered":
        if not ((repo / ".github/workflows").is_dir() or
                (repo / "azure-pipelines.yml").is_file()):
            missing.append("CI")
            r["score"] += 5
        # AGENTS.md only: a lone CLAUDE.md is the wrong file, not a pass.
        if not (repo / "AGENTS.md").exists():
            missing.append("AGENTS.md")
            r["score"] += 3
        if tier == "S-pub" and not any(
                (repo / n).exists()
                for n in ("LICENSE", "LICENSE.md", "LICENSE.txt")):
            missing.append("LICENSE")
            r["score"] += 4
    if missing:
        r["missing"] = missing
        r["notes"].append("missing " + "/".join(missing))

    if network:
        ok, url = git(repo, "remote", "get-url", "origin")
        if ok and url:
            alive, _ = git(repo, "ls-remote", "--exit-code", "-h", "origin",
                           timeout=LSREMOTE_TIMEOUT)
            if not alive:
                r["dead_remote"] = url
                r["notes"].append(f"**dead remote** `{url}`")
                r["score"] += 20

    # agent co-author trailers. One pass gives both the count and how many
    # humans ever committed here — history is only safe to rewrite when nobody
    # else has a clone, and "one author ever" is the cheapest proxy for that.
    ok, log = git(repo, "log", "--format=%ae\t%(trailers:key="
                  "Co-authored-by,valueonly,separator=%x2C)")
    if ok:
        n_agent, authors = 0, set()
        for line in log.splitlines():
            ae, _, trailers = line.partition("\t")
            if not AGENT_RE.search(ae):
                authors.add(ae.lower())
            if AGENT_RE.search(trailers):
                n_agent += 1
        if n_agent:
            # ponytail: report the committers, don't rule on them. Two emails
            # are as often one person with a laptop typo as they are two people.
            r["agent_coauthors"] = n_agent
            r["authors"] = sorted(authors)
            r["notes"].append(f"{n_agent} agent co-author trailer(s), "
                              f"{len(authors)} committer(s)")
            r["score"] += 1

    # dependency manifest presence — feeds the /repo-deps nomination
    # ponytail: root-level manifests only, no recursive monorepo walk.
    r["deps"] = [n for n in ("package.json", "Cargo.toml", "requirements.txt",
                             "pyproject.toml", "go.mod")
                 if (repo / n).is_file()]
    return r


# ── report ───────────────────────────────────────────────────────────────

def nominate(results):
    """Top 5 actions. ponytail: a scored heuristic, not a planner. Claude re-ranks.

    Broken repos and dead remotes each collapse into ONE entry — 21 broken repos
    would otherwise eat every slot and the section would say nothing useful.
    """
    out = []
    broken = [r for r in results if r.get("broken")]
    dead = [r for r in results if r.get("dead_remote")]
    if broken:
        names = ", ".join(f"`{r['repo']}`" for r in broken[:3])
        out.append((None, "manual repair",
                    f"{len(broken)} repo(s) with broken git state ({names}"
                    f"{', …' if len(broken) > 3 else ''}) — no routine can run on "
                    f"them; the findings table has the per-repo cause"))
    if dead:
        out.append((None, "manual repair",
                    f"{len(dead)} unreachable origin(s): " +
                    ", ".join(f"`{r['repo']}`" for r in dead[:3])))

    for r in sorted((x for x in results
                     if not x.get("broken") and not x.get("dead_remote")),
                    key=lambda x: -x["score"]):
        if len(out) == 5:
            break
        if r["score"] < 3:
            continue
        # W-ro is report-only per tier policy, so no fixer routine may be
        # nominated for it. ponytail: silently skipped; it's still in the table.
        if r["tier"] == "W-ro":
            continue
        if r.get("missing"):
            cmd, why = "/repo-groom", "missing baseline: " + ", ".join(r["missing"])
        elif r.get("deps"):
            cmd, why = "/repo-deps", "has " + ", ".join(r["deps"]) + "; churn suggests drift"
        else:
            cmd, why = "/repo-deep", "clean baseline, active — good rotation candidate"
        if r.get("dirty"):
            why += f"; {len(r['dirty'])} dirty file(s) to triage first"
        out.append((r, cmd, why))
    return out


def render(results, untiered, unversioned_dirs, root, network, elapsed):
    hits = [r for r in results if r["notes"]]
    n = lambda k: sum(1 for r in results if r.get(k))
    now = datetime.now(timezone.utc).astimezone()

    L = [f"# Repo health — {now:%Y-%m-%d}", ""]
    L += [f"Read-only sweep of `{root}` · {len(results)} repos in "
          f"{elapsed:.1f}s · network checks "
          f"{'on' if network else 'off (`--network` to enable)'}", ""]
    L += ["## Summary", "",
          "| Metric | Count |", "|---|---:|",
          f"| Repos swept | {len(results)} |",
          f"| Repos with findings | {len(hits)} |",
          f"| Broken git state | {n('broken')} |",
          f"| Dirty worktrees | {n('dirty')} |",
          f"| Unpushed commits | {n('ahead')} |",
          f"| Behind upstream | {n('behind')} |",
          f"| Stale local branches | {n('stale_branches')} |",
          f"| Missing baseline files | {n('missing')} |",
          f"| Dead remotes | {n('dead_remote')} |",
          f"| Agent co-author trailers | {n('agent_coauthors')} |",
          f"| Untiered repos | {len(untiered)} |",
          f"| Unversioned dirs | {len(unversioned_dirs)} |", ""]

    L += ["## Findings", ""]
    if hits:
        L += ["| Repo | Tier | Findings |", "|---|---|---|"]
        for r in sorted(hits, key=lambda x: -x["score"]):
            L.append(f"| `{r['repo']}` | {r['tier']} | " +
                     "; ".join(r["notes"]) + " |")
    else:
        L.append("Nothing to report — every swept repo is clean.")
    L.append("")

    if untiered:
        L += ["## Not in `.repo-tiers.json`", ""]
        L += [f"- `{u}`" for u in untiered] + [""]
    if unversioned_dirs:
        L += ["## Unversioned dirs under the code root", ""]
        L += [f"- `{u}`" for u in unversioned_dirs] + [""]

    scrub = sorted((r for r in results if r.get("agent_coauthors")),
                   key=lambda x: -x["agent_coauthors"])
    if scrub:
        L += ["## Agent co-author trailers", "",
              "Scrubbing rewrites every commit SHA from the first hit onward "
              "and needs a force-push, so it is safe only where every listed "
              "committer is you and nobody else holds a clone. Run it by hand, "
              "one repo at a time; no routine does this for you.", "",
              "| Repo | Commits | Committers |", "|---|---:|---|"]
        for r in scrub:
            who = (", ".join(f"`{a}`" for a in r["authors"])
                   if len(r["authors"]) <= 3 else f"{len(r['authors'])} people")
            L.append(f"| `{r['repo']}` | {r['agent_coauthors']} | {who} |")
        L += ["", "```bash", "git filter-repo --force --message-callback '",
              "return b\"\\n\".join(l for l in message.split(b\"\\n\")",
              "  if not (l.lower().startswith(b\"co-authored-by:\") and",
              "          any(a in l.lower() for a in "
              "(b\"anthropic.com\", b\"copilot\", b\"devin\", b\"cursor\"))))'",
              "```", ""]

    L += ["## Top 5 recommended actions", ""]
    picks = nominate(results)
    if picks:
        for i, (r, cmd, why) in enumerate(picks, 1):
            target = f" {r['repo']}" if r else ""
            L.append(f"{i}. **`{cmd}{target}`** — {why}")
    else:
        L.append("Nothing pressing. Skip a week.")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("REPO_ROOT", os.path.expanduser("~/code")))
    ap.add_argument("--out", default="REPO-HEALTH.md")
    ap.add_argument("--network", action="store_true",
                    help="also ls-remote each origin (slow-ish)")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--stale-days", type=int, default=180)
    ap.add_argument("--stdout", action="store_true", help="print instead of write")
    a = ap.parse_args()

    root = pathlib.Path(a.root).expanduser().resolve()
    t0 = time.time()
    tiers = load_tiers(root)
    repos = discover(root)
    untiered = []

    if tiers is None:
        targets = [(r, "?") for r in repos]
    else:
        targets = []
        for r in repos:
            tier = tiers.get(r)
            if tier is None:
                untiered.append(r)
                targets.append((r, "untiered"))
            elif tier not in SKIP_TIERS:
                targets.append((r, tier))

    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        results = list(ex.map(
            lambda t: check(root, t[0], t[1], a.network, a.stale_days), targets))

    md = render(results, untiered, unversioned(root, repos), root,
                a.network, time.time() - t0)
    if a.stdout:
        sys.stdout.write(md)
    else:
        out = pathlib.Path(a.out)
        if not out.is_absolute():
            out = root / out
        out.write_text(md)
        print(f"{out}  ({len(results)} repos, {time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
