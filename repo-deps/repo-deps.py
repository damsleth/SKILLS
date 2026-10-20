#!/usr/bin/env python3
"""repo-deps — read-only security & dependency sweep over ~/code repos.

The ANALYSIS half of the /repo-deps skill. This script NEVER modifies a repo:
it only runs native audit tools in read-only modes and writes one report,
REPO-DEPS.md, at the root of the code dir (which is not itself a git repo).
Remediation (applying safe bumps as commits) is done interactively by Claude
per SKILL.md — it is deliberately NOT in this script, so the monthly cron can
never write to a repo.

Per repo it detects the stack(s) and runs, where the tool exists:
    Node     npm outdated --json + npm audit --json (pnpm/yarn per lockfile)
    Python   uvx pip-audit (uv.lock -> uv export --frozen, else requirements)
    Rust     cargo audit + cargo outdated (notes if the subcommand is missing)
    .NET     dotnet list package --outdated / --vulnerable (two calls)
    secrets  gitleaks --no-git if installed, else a regex fallback (report only)
    actions  GitHub Actions pinned-by-SHA vs mutable @v-tag hygiene check

Missing tools are noted and skipped — a missing tool never fails the run.

Usage:
    ./repo-deps.py                       # all active repos (skip archive/external)
    ./repo-deps.py CLI/mytool  # one or more specific repos
    ./repo-deps.py --analysis            # explicit no-op flag (cron reads clearly)
    ./repo-deps.py --stdout              # print instead of writing REPO-DEPS.md
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

# ponytail: every knob is a constant, not a config file. Edit in place.
SKIP_TIERS = {"archive", "external"}   # analysis covers S-priv/S-pub/W/W-ro
MAX_DEPTH = 3                          # tier keys are depth 1-2; 3 catches strays
CMD_TIMEOUT = 120                      # seconds per audit tool (npm audit hits net)
SECRET_MAX_BYTES = 512 * 1024          # skip files larger than this in regex scan
SECRET_MAX_FILES = 4000                # cap files scanned per repo
TOP_ITEMS = 40                         # cap list lengths in the report

# launchd runs with a bare PATH (/usr/bin:/bin:...) and no fnm/uv shims, so bake
# the real tool dirs in. Without this the monthly cron would report every Node
# repo as "npm not installed" and exit 0 — a clean-looking dead cron.
EXTRA_PATH = [
    "/opt/homebrew/bin",                                   # brew: node, dotnet, fnm
    os.path.expanduser("~/.local/bin"),                    # uv, uvx
    os.path.expanduser("~/.local/share/fnm/aliases/default/bin"),  # fnm default node
]
PATH = os.pathsep.join(EXTRA_PATH + [os.environ.get("PATH", "")])
ENV = {**os.environ, "PATH": PATH, "NO_COLOR": "1",
       "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}


def have(tool):
    """True if `tool` is on the baked PATH."""
    for d in PATH.split(os.pathsep):
        if d and os.access(os.path.join(d, tool), os.X_OK):
            return True
    return False


def run(cwd, *cmd, timeout=CMD_TIMEOUT):
    """Run a command read-only. Returns (rc, stdout, stderr); rc=-1 on timeout/OSError.

    Note: npm outdated/audit exit 1 *when they find things*, so callers must parse
    stdout regardless of rc and only treat empty/unparseable output as failure.
    """
    try:
        p = subprocess.run(list(cmd), cwd=str(cwd), capture_output=True,
                           text=True, env=ENV, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"
    except OSError as e:
        return -1, "", str(e)


# ── discovery (reused from repo-health, verbatim behaviour) ────────────────

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
            dirnames[:] = []
            continue
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if not d.startswith(".")
                       and d not in ("node_modules", "venv", "target", "dist")]
    return sorted(x for x in found if x != ".")


# ── stack detection ────────────────────────────────────────────────────────

def detect(repo):
    """Which stacks a repo uses + whether it's a deployed CF Worker."""
    s = {}
    s["node"] = (repo / "package.json").is_file()
    s["python"] = (repo / "pyproject.toml").is_file() or (repo / "requirements.txt").is_file()
    s["rust"] = (repo / "Cargo.toml").is_file()
    # ponytail: shallow glob, not a full walk — root/solution .NET projects only.
    s["dotnet"] = bool(list(repo.glob("*.csproj")) + list(repo.glob("*.sln"))
                       + list(repo.glob("*/*.csproj")))
    # deployed = a root-level wrangler config (CF Worker). Pages-only sites and
    # the cj-cloudflare-worker asset templates (under assets/) don't match.
    s["deployed"] = any((repo / n).is_file() for n in
                        ("wrangler.jsonc", "wrangler.json", "wrangler.toml"))
    return s


# ── Node ─────────────────────────────────────────────────────────────────

def _ver(v):
    """'1.22.2' / '^19.3.0-rc.1' -> (1, 22, 2); prerelease tags ignored."""
    return tuple(int(x) for x in re.findall(r"\d+", v.split("-")[0])[:3])


def _split_bumps(outdated):
    """Group npm-style outdated entries into safe (minor/patch) vs breaking (major)."""
    safe, breaking = [], []
    for name, info in outdated.items():
        cur = info.get("current") or info.get("wanted") or ""
        latest = info.get("latest") or info.get("wanted") or ""
        if not latest or cur == latest:
            continue                       # no actual bump — npm lists these anyway
        if _ver(latest) <= _ver(cur):
            continue                       # dist-tag "latest" older than installed — not a bump
        cmaj = re.match(r"\D*(\d+)", cur)
        lmaj = re.match(r"\D*(\d+)", latest)
        line = f"{name} {cur or '—'} -> {latest or '?'}"
        if cmaj and lmaj and int(lmaj.group(1)) > int(cmaj.group(1)):
            breaking.append(line)
        else:
            safe.append(line)
    return sorted(safe), sorted(breaking)


def audit_node(repo, out):
    # pick the package manager the lockfile implies
    if (repo / "pnpm-lock.yaml").is_file():
        pm = "pnpm"
    elif (repo / "yarn.lock").is_file():
        pm = "yarn"
    else:
        pm = "npm"
    if not have(pm):
        out["notes"].append(f"Node: `{pm}` not installed — skipped")
        return

    # outdated (npm/pnpm share --json shape; yarn differs, so best-effort)
    rc, so, se = run(repo, pm, "outdated", "--json")
    if so.strip():
        try:
            data = json.loads(so)
            if isinstance(data, dict) and data:
                safe, breaking = _split_bumps(data)
                out["node_safe"], out["node_breaking"] = safe, breaking
        except json.JSONDecodeError:
            pass  # yarn's shape or noise; audit below still runs

    # audit. --package-lock-only audits straight from the lockfile so it works
    # without an installed node_modules (deployed repos rarely check theirs in).
    audit_cmd = [pm, "audit", "--json"]
    if pm in ("npm", "pnpm"):
        audit_cmd.append("--package-lock-only" if pm == "npm" else "--lockfile-only")
    rc, so, se = run(repo, *audit_cmd)
    if so.strip():
        try:
            data = json.loads(so)
            vulns = []
            # npm v7+ shape: {"vulnerabilities": {name: {severity, via:[...]}}}
            for name, v in (data.get("vulnerabilities") or {}).items():
                sev = v.get("severity", "?")
                cves = []
                for via in v.get("via", []):
                    if isinstance(via, dict):
                        title = via.get("title") or via.get("url") or ""
                        if title:
                            cves.append(title)
                out.setdefault("vulns", []).append(
                    f"[{sev}] {name}" + (f" — {cves[0]}" if cves else ""))
                vulns.append(name)
            meta = (data.get("metadata") or {}).get("vulnerabilities") or {}
            if meta:
                out["node_audit_summary"] = ", ".join(
                    f"{k}:{v}" for k, v in meta.items() if v)
        except json.JSONDecodeError:
            out["notes"].append("Node: audit output unparseable")
    elif se.strip() and "npm warn" not in se.lower():
        out["notes"].append(f"Node audit: {se.splitlines()[0][:120]}")


# ── Python ───────────────────────────────────────────────────────────────

def audit_python(repo, out):
    if not have("uvx"):
        out["notes"].append("Python: `uvx`/pip-audit not available — deps not audited")
        _declare_python(repo, out)
        return

    req = None
    tmp = None
    if (repo / "uv.lock").is_file() and have("uv"):
        # --frozen keeps uv from touching the lockfile (read-only guarantee).
        tmp = f"/tmp/repo-deps-{abs(hash(str(repo)))}.txt"
        rc, so, se = run(repo, "uv", "export", "--frozen", "--all-extras", "--no-emit-project",
                         "--no-dev", "--format", "requirements-txt", "-o", tmp)
        if rc == 0 and os.path.isfile(tmp):
            req = tmp
        else:
            out["notes"].append("Python: `uv export` failed — deps not audited")
    elif (repo / "requirements.txt").is_file():
        req = str(repo / "requirements.txt")

    if not req:
        _declare_python(repo, out)
        return

    # --no-deps: audit exactly the pinned set, don't build an ephemeral venv.
    # ponytail: flat 600s — pip-audit queries PyPI per package, ~5 min with extras.
    rc, so, se = run(repo, "uvx", "pip-audit", "--no-deps", "--format", "json",
                     "-r", req, timeout=600)
    if tmp:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    if so.strip():
        try:
            data = json.loads(so)
            deps = data.get("dependencies", data) if isinstance(data, dict) else data
            for dep in (deps if isinstance(deps, list) else []):
                for v in dep.get("vulns", []) or []:
                    ids = v.get("id", "?")
                    fix = ",".join(v.get("fix_versions", []) or []) or "no fix"
                    out.setdefault("vulns", []).append(
                        f"[py] {dep.get('name')} {dep.get('version','')} "
                        f"— {ids} (fix: {fix})")
            return
        except json.JSONDecodeError:
            pass
    if se.strip():
        out["notes"].append(f"Python audit: {se.splitlines()[0][:120]}")


def _declare_python(repo, out):
    """Fallback: just list declared deps so the report isn't empty. ponytail:
    no hardcoded stale-version map — that data rots and can't be verified."""
    py = repo / "pyproject.toml"
    if py.is_file():
        txt = py.read_text(errors="ignore")
        m = re.search(r"dependencies\s*=\s*\[(.*?)\]", txt, re.S)
        if m:
            deps = re.findall(r'["\']([^"\']+)["\']', m.group(1))
            if deps:
                out["py_declared"] = deps[:TOP_ITEMS]


# ── Rust ───────────────────────────────────────────────────────────────────

def audit_rust(repo, out):
    if not have("cargo"):
        out["notes"].append("Rust: `cargo` not installed — skipped")
        return
    # cargo-audit / cargo-outdated are separate binaries invoked as subcommands.
    if have("cargo-audit"):
        rc, so, se = run(repo, "cargo", "audit", "--json")
        if so.strip():
            try:
                data = json.loads(so)
                for v in (data.get("vulnerabilities") or {}).get("list", []):
                    adv = v.get("advisory", {})
                    out.setdefault("vulns", []).append(
                        f"[rust] {adv.get('package','?')} — "
                        f"{adv.get('id','?')} {adv.get('title','')[:80]}")
            except json.JSONDecodeError:
                out["notes"].append("Rust: cargo audit output unparseable")
    else:
        out["notes"].append("Rust: `cargo-audit` not installed "
                            "(`cargo install cargo-audit`) — vulns not checked")
    if have("cargo-outdated"):
        rc, so, se = run(repo, "cargo", "outdated", "--format", "json")
        if so.strip():
            try:
                data = json.loads(so)
                names = [d.get("name") for d in data.get("dependencies", [])
                         if d.get("latest") not in (None, "---", d.get("project"))]
                if names:
                    out["rust_outdated"] = sorted(set(n for n in names if n))[:TOP_ITEMS]
            except json.JSONDecodeError:
                pass
    else:
        out["notes"].append("Rust: `cargo-outdated` not installed — bumps not listed")


# ── .NET ─────────────────────────────────────────────────────────────────

def audit_dotnet(repo, out):
    if not have("dotnet"):
        out["notes"].append(".NET: `dotnet` not installed — skipped")
        return
    # --outdated and --vulnerable are mutually exclusive on recent SDKs -> two calls.
    for flag, key in (("--vulnerable", "vulns"), ("--outdated", "dotnet_outdated")):
        rc, so, se = run(repo, "dotnet", "list", "package", flag, "--format", "json")
        blob = so.strip() or se.strip()
        if "restore" in (so + se).lower() and rc != 0:
            out["notes"].append(".NET: project needs `dotnet restore` — skipped "
                               "(never auto-restored)")
            return
        if not so.strip():
            continue
        try:
            data = json.loads(so)
        except json.JSONDecodeError:
            continue
        for proj in data.get("projects", []):
            for fw in proj.get("frameworks", []) or []:
                bucket = (fw.get("vulnerablePackages") if flag == "--vulnerable"
                          else fw.get("topLevelPackages")) or []
                for pkg in bucket:
                    if flag == "--vulnerable":
                        for adv in pkg.get("vulnerabilities", []) or []:
                            out.setdefault("vulns", []).append(
                                f"[.net] {pkg.get('id')} {pkg.get('resolvedVersion','')} "
                                f"— {adv.get('severity','?')} {adv.get('advisoryUrl','')}")
                    else:
                        lat = pkg.get("latestVersion")
                        res = pkg.get("resolvedVersion")
                        if lat and lat != res:
                            out.setdefault("dotnet_outdated", []).append(
                                f"{pkg.get('id')} {res} -> {lat}")


# ── secret scan ────────────────────────────────────────────────────────────

# ponytail: a handful of high-signal patterns, not a full gitleaks ruleset.
SECRET_PATTERNS = [
    ("AWS access key",   re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("GitHub token",     re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("Slack token",      re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key",   re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Generic secret",   re.compile(r"(?i)(?:api[_-]?key|secret|passwd|password|token)"
                                    r"\s*[:=]\s*['\"][A-Za-z0-9/\+=_\-]{16,}['\"]")),
]
SECRET_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "target", "dist",
                    "build", ".next", ".serena", ".pytest_cache", ".ruff_cache",
                    "playwright-report", "test-results", ".doc",
                    "__pycache__", ".tui-test"}
SECRET_SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
                   ".zip", ".gz", ".tar", ".woff", ".woff2", ".ttf", ".mp4",
                   ".mov", ".db", ".sqlite", ".lock", ".map", ".min.js", ".pyc"}


def scan_secrets(repo, out):
    if have("gitleaks"):
        # --redact so matched values never land in our report or logs.
        rc, so, se = run(repo, "gitleaks", "detect", "--no-git", "--redact",
                         "-r", "/dev/stdout", "-f", "json", "--source", ".")
        if so.strip():
            try:
                for f in json.loads(so):
                    out.setdefault("secrets", []).append(
                        f"{f.get('RuleID','?')} in {f.get('File','?')}"
                        f":{f.get('StartLine','?')}")
            except json.JSONDecodeError:
                pass
        return

    # regex fallback — report pattern name + file:line ONLY, never the value.
    out.setdefault("secret_tool", "regex-fallback (gitleaks not installed)")
    seen = 0
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SECRET_SKIP_DIRS
                       and not (d == "worktrees" and os.path.basename(dirpath) == ".claude")]
        for fn in filenames:
            if seen >= SECRET_MAX_FILES:
                return
            ext = os.path.splitext(fn)[1].lower()
            if ext in SECRET_SKIP_EXT:
                continue
            fp = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(fp) > SECRET_MAX_BYTES:
                    continue
                with open(fp, "r", errors="ignore") as fh:
                    seen += 1
                    for lineno, line in enumerate(fh, 1):
                        if len(line) > 4000:
                            continue
                        for name, pat in SECRET_PATTERNS:
                            if pat.search(line):
                                rel = os.path.relpath(fp, repo)
                                out.setdefault("secrets", []).append(
                                    f"{name} in {rel}:{lineno}")
                                break
            except OSError:
                continue


# ── GitHub Actions pinning ──────────────────────────────────────────────────

SHA_RE = re.compile(r"@[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^'\"\s]+)")


def check_actions(repo, out):
    wf = repo / ".github" / "workflows"
    if not wf.is_dir():
        return
    unpinned = []
    for f in list(wf.glob("*.yml")) + list(wf.glob("*.yaml")):
        try:
            for line in f.read_text(errors="ignore").splitlines():
                m = USES_RE.match(line)
                if not m:
                    continue
                ref = m.group(1)
                if ref.startswith("./") or ref.startswith("docker://"):
                    continue           # local/docker actions have no SHA to pin
                if "@" not in ref:
                    continue
                if not SHA_RE.search(ref):
                    unpinned.append(f"{f.name}: {ref}")
        except OSError:
            continue
    if unpinned:
        out["unpinned_actions"] = sorted(set(unpinned))[:TOP_ITEMS]


# ── per-repo driver ──────────────────────────────────────────────────────

def analyse(root, rel, tier):
    repo = root / rel
    out = {"repo": rel, "tier": tier, "notes": []}
    st = detect(repo)
    out["deployed"] = st["deployed"]
    out["stacks"] = [k for k in ("node", "python", "rust", "dotnet") if st[k]]
    try:
        if st["node"]:
            audit_node(repo, out)
        if st["python"]:
            audit_python(repo, out)
        if st["rust"]:
            audit_rust(repo, out)
        if st["dotnet"]:
            audit_dotnet(repo, out)
        scan_secrets(repo, out)
        check_actions(repo, out)
    except Exception as e:  # noqa: BLE001 — one bad repo must not kill the sweep
        out["notes"].append(f"analysis error: {type(e).__name__}: {e}")
    return out


# ── report ───────────────────────────────────────────────────────────────

TIER_RANK = {"S-pub": 1, "S-priv": 2, "W": 3, "W-ro": 4}


def sort_key(r):
    # deployed first, then S-pub, then private, then work.
    return (0 if r["deployed"] else 1, TIER_RANK.get(r["tier"], 9), r["repo"])


def has_findings(r):
    return any(r.get(k) for k in ("vulns", "secrets", "unpinned_actions",
                                  "node_safe", "node_breaking", "rust_outdated",
                                  "dotnet_outdated")) or r["notes"]


def render(results, root, elapsed, scope):
    now = datetime.now(timezone.utc).astimezone()
    n = lambda k: sum(1 for r in results if r.get(k))
    tot = lambda k: sum(len(r.get(k, [])) for r in results)
    L = [f"# Repo deps & security — {now:%Y-%m-%d}", "",
         f"Read-only sweep of `{root}` · {len(results)} repos in {elapsed:.1f}s · "
         f"scope: {scope}", "",
         "This report never modifies a repo. Safe bumps are applied only "
         "interactively via `/repo-deps <repo>` (remediation), per tier policy.", ""]

    L += ["## Summary", "", "| Metric | Count |", "|---|---:|",
          f"| Repos analysed | {len(results)} |",
          f"| Repos with findings | {sum(1 for r in results if has_findings(r))} |",
          f"| Deployed (CF Worker) repos | {n('deployed')} |",
          f"| Total vulnerabilities | {tot('vulns')} |",
          f"| Repos with secret hits | {n('secrets')} |",
          f"| Repos with unpinned Actions | {n('unpinned_actions')} |",
          f"| Safe (minor/patch) bumps | {tot('node_safe') + tot('dotnet_outdated') + tot('rust_outdated')} |",
          f"| Breaking (major) bumps flagged | {tot('node_breaking')} |", ""]

    L += ["## Per-repo findings", "",
          "Order: deployed workers first, then public (S-pub), then private "
          "(S-priv), then work (W/W-ro). W-ro/archive/external are never "
          "remediated — analysis only.", ""]

    any_repo = False
    for r in sorted(results, key=sort_key):
        if not has_findings(r):
            continue
        any_repo = True
        tags = []
        if r["deployed"]:
            tags.append("DEPLOYED CF Worker")
        tags.append(r["tier"])
        if r["stacks"]:
            tags.append("/".join(r["stacks"]))
        L += [f"### `{r['repo']}` — {' · '.join(tags)}", ""]

        if r.get("vulns"):
            L += ["**Vulnerabilities**", ""]
            L += [f"- {v}" for v in r["vulns"][:TOP_ITEMS]]
            if r.get("node_audit_summary"):
                L.append(f"- _npm audit: {r['node_audit_summary']}_")
            L.append("")
        if r.get("node_safe") or r.get("dotnet_outdated") or r.get("rust_outdated"):
            safe = (r.get("node_safe", []) + r.get("dotnet_outdated", [])
                    + r.get("rust_outdated", []))
            L += ["**Safe bumps (minor/patch — auto-bumpable)**", ""]
            L += [f"- {x}" for x in safe[:TOP_ITEMS]] + [""]
        if r.get("node_breaking"):
            L += ["**Breaking bumps (major — manual review, NOT auto-bumped)**", ""]
            L += [f"- {x}" for x in r["node_breaking"][:TOP_ITEMS]] + [""]
        if r.get("py_declared"):
            L += ["**Declared Python deps (pip-audit unavailable — not audited)**", "",
                  "- " + ", ".join(f"`{d}`" for d in r["py_declared"]), ""]
        if r.get("secrets"):
            tool = r.get("secret_tool", "gitleaks")
            L += [f"**Secret hits ({tool}) — REVIEW MANUALLY, never auto-remediated**", ""]
            L += [f"- {s}" for s in r["secrets"][:TOP_ITEMS]] + [""]
        if r.get("unpinned_actions"):
            L += ["**Unpinned GitHub Actions (mutable @tag — pin to SHA)**", ""]
            L += [f"- {a}" for a in r["unpinned_actions"][:TOP_ITEMS]] + [""]
        if r["notes"]:
            L += ["_Notes:_ " + "; ".join(r["notes"]), ""]

    if not any_repo:
        L += ["Nothing to report — no vulnerabilities, outdated deps, secret "
              "hits, or unpinned actions across the swept repos.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="read-only dep & security sweep")
    ap.add_argument("repos", nargs="*", help="specific repos (default: all active)")
    ap.add_argument("--root", default=os.environ.get("REPO_ROOT", os.path.expanduser("~/code")))
    ap.add_argument("--out", default="REPO-DEPS.md")
    ap.add_argument("--analysis", action="store_true",
                    help="analysis-only (default & only mode; documents cron intent)")
    ap.add_argument("--all-active", action="store_true",
                    help="all active repos (default when no repos given)")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--stdout", action="store_true", help="print instead of write")
    a = ap.parse_args()

    root = pathlib.Path(a.root).expanduser().resolve()
    t0 = time.time()
    tiers = load_tiers(root)

    if a.repos:
        targets = [(r, (tiers or {}).get(r, "untiered")) for r in a.repos]
        scope = f"{len(targets)} named repo(s)"
    else:
        discovered = discover(root)
        targets = []
        for r in discovered:
            tier = (tiers or {}).get(r)
            if tiers is None:
                targets.append((r, "?"))
            elif tier is None:
                continue                     # untiered: not audited by default
            elif tier not in SKIP_TIERS:
                targets.append((r, tier))
        scope = "all active repos (S-priv/S-pub/W/W-ro)"

    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        results = list(ex.map(lambda t: analyse(root, t[0], t[1]), targets))

    md = render(results, root, time.time() - t0, scope)
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
