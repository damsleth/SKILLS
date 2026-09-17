#!/usr/bin/env python3
"""
now — one canonical view of what is open, across every task surface.

A projection, not a store. Nothing is written, nothing is synced, so nothing can
drift. Three adapters read their source on demand:

  plans   <repo>/.plans/TODO.md + <repo>/.plans/*.md   (filesystem, instant)
  things  things all --json                            (local sqlite, instant)
  ado     owa-ado wi --agent --mine                    (network, cached)
  loops   ledger loops --json                          (local files, instant)

Everything is keyed on the owa-piggy profile (une / nc / swon / brkh / dno),
which is the one axis all three sources share.

  now                      open work, grouped by profile
  now --profile une        one profile
  now --source plans       one source
  now --all                include non-work areas (brkh, dno, fdep)
  now --agent              JSON for machines

ponytail: no config file until the baked-in mappings actually stop fitting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "cj-now"
ADO_TTL = 900  # seconds

# Everything below is personal wiring, not tool logic: which profiles count as
# work, which repo path belongs to which, what a Things area is called. It ships
# generic and empty so the tool runs anywhere, and is overridden wholesale by
# ~/.config/cj-now/config.json. See SKILL.md for the shape.
CONFIG_PATH = Path(
    os.environ.get("XDG_CONFIG_HOME", HOME / ".config")
) / "cj-now" / "config.json"

# With no config every profile is work, so nothing is hidden from someone who
# has not told us what their work is.
WORK_PROFILES: set[str] = set()
REPO_PROFILES: list[tuple[str, str]] = []
AREA_PROFILES: dict[str, str] = {}
REPO_FALLBACK = "local"
# owa-ado is configured against exactly one owa-piggy profile, so every work
# item it returns belongs to that one.
ADO_PROFILE = "work"


def load_config() -> None:
    """Fold ~/.config/cj-now/config.json over the built-in defaults."""
    global WORK_PROFILES, REPO_PROFILES, AREA_PROFILES, REPO_FALLBACK, ADO_PROFILE
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        if CONFIG_PATH.exists():
            WARNINGS.append(f"config: {CONFIG_PATH} ignorert, {type(e).__name__}")
        return
    WORK_PROFILES = set(cfg.get("work_profiles") or [])
    # A list of pairs, not a dict: first match wins, so order is meaning.
    REPO_PROFILES = [tuple(pair) for pair in cfg.get("repo_profiles") or []]
    AREA_PROFILES = dict(cfg.get("area_profiles") or {})
    REPO_FALLBACK = cfg.get("fallback_profile") or REPO_FALLBACK
    ADO_PROFILE = cfg.get("ado_profile") or ADO_PROFILE


SOURCES = ("plans", "things", "ado", "loops")

# Rows shown per profile before the tail is folded away. --full shows everything.
DEFAULT_LIMIT = 10

# A source that is down must never look like a source that is empty. Adapters
# append here and the renderers surface it.
WARNINGS: list[str] = []


# ---------------------------------------------------------------- helpers


def run(cmd: list[str], timeout: int = 60) -> str | None:
    """Run a command, return stdout, or None if it fails. Never raises.

    owa-* tools exit 0 and print an ERROR banner on auth failure, so treat any
    output that is not JSON as a failure at the call site.
    """
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        WARNINGS.append(f"{cmd[0]}: {type(e).__name__}")
        return None
    if p.returncode != 0:
        WARNINGS.append(f"{cmd[0]}: exit {p.returncode} {(p.stderr or '').strip()[:120]}")
        return None
    if p.stdout.lstrip().startswith("ERROR"):
        WARNINGS.append(f"{cmd[0]}: {p.stdout.strip().splitlines()[0][:160]}")
        return None
    return p.stdout


def iso(ts, naive_is_local: bool = False) -> str | None:
    """Normalise whatever a source hands us into an ISO-8601 UTC string.

    Things writes naive local wall-clock ("2026-09-12 14:54:53"). Tagging that
    UTC put every Things row up to a timezone offset into the future, which
    showed as "-1d" and handed Things a free win in the sort_key recency
    tiebreak. Sources that hand us naive local time pass naive_is_local=True.
    """
    if not ts:
        return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")
    s = str(ts).strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.fromisoformat(s) if fmt is None else datetime.strptime(s, fmt)
        except ValueError:
            continue
        # A date-only value is a calendar date, not an instant. Shifting it by a
        # timezone offset moved every deadline a day earlier.
        date_only = len(s) == 10
        if d.tzinfo is None:
            local = naive_is_local and not date_only
            d = d.astimezone() if local else d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    return None


def age_days(ts: str | None) -> int | None:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(ts)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - d).days


def item(
    *, id, source, title, profile, status, updated=None, deadline=None, url=None, **extra
) -> dict:
    """The one record shape every adapter normalises into."""
    rec = {
        "id": id,
        "source": source,
        "title": " ".join((title or "").split()),
        "profile": profile,
        "status": status,
        "updated": updated,
        "deadline": deadline,
        "url": url,
    }
    rec.update(extra)
    return rec


# ---------------------------------------------------------------- adapters


def profile_for_repo(path: Path) -> str:
    try:
        rel = path.relative_to(HOME).as_posix()
    except ValueError:
        rel = path.as_posix()
    for prefix, profile in REPO_PROFILES:
        if rel.startswith(prefix):
            return profile
    return REPO_FALLBACK


def plan_ado_ids(f: Path) -> list[str]:
    """Work item ids from a plan's `ado:` frontmatter, e.g. "ado: 16167, 16168"."""
    try:
        head = f.read_text(encoding="utf-8", errors="replace")[:400]
    except OSError:
        return []
    m = re.search(r"^ado:([^\n#]*)", head, re.MULTILINE)
    return re.findall(r"\d+", m.group(1)) if m else []


def plan_title(f: Path) -> str:
    """First markdown h1, else the filename."""
    try:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return f.stem


def adapter_plans(roots: list[Path]) -> list[dict]:
    """Mirrors todo.sh enumerate(): open TODO.md lines + top-level plan files."""
    out = []
    for plans_dir in roots:
        repo = plans_dir.parent
        name = repo.name if repo != HOME / "brain" else "global"
        profile = profile_for_repo(repo)

        todo_file = plans_dir / "TODO.md"
        if todo_file.is_file():
            try:
                lines = todo_file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                lines = []
            for n, line in enumerate(lines, 1):
                m = re.match(r"^- \[ \] (.+)$", line.strip())
                if not m or "→ .plans/" in m.group(1):
                    continue
                out.append(
                    item(
                        id=f"plans:{name}/todo#{n}",
                        source="plans",
                        title=m.group(1),
                        profile=profile,
                        status="todo",
                        updated=iso(todo_file.stat().st_mtime),
                        url=f"file://{todo_file}",
                        repo=name,
                        kind="todo",
                    )
                )

        for f in sorted(plans_dir.glob("*.md")):
            if f.name in ("TODO.md", "DONE.md", "README.md"):
                continue
            out.append(
                item(
                    id=f"plans:{name}/{f.stem}",
                    source="plans",
                    title=plan_title(f),
                    profile=profile,
                    status="plan",
                    updated=iso(f.stat().st_mtime),
                    url=f"file://{f}",
                    repo=name,
                    kind="plan",
                    ado_ids=plan_ado_ids(f),
                )
            )
    return out


def adapter_things() -> list[dict]:
    raw = run(["things", "all", "--json"])
    if not raw:
        return []
    try:
        groups = json.loads(raw)
    except json.JSONDecodeError:
        return []

    # The Today bucket exists only as a group title: every item inside still
    # reports start=Anytime/Someday, so the item alone cannot tell you it is
    # committed for today. Collect the uuids up front rather than relying on
    # Today being iterated before Anytime.
    def bucket(name):
        return {
            t.get("uuid")
            for g in groups
            if g.get("title") == name
            for t in g.get("items", [])
        }

    today = bucket("Today")
    # Scheduled to start later. Things reports these as start=Someday, so
    # without the group they were indistinguishable from real Someday tasks and
    # could not be asked for at all. Labelling them does not promote them: the
    # relevance filter still wants a deadline or Today, and a task deliberately
    # scheduled for the 21st is not open work today.
    upcoming = bucket("Upcoming")

    out, seen = [], set()
    for group in groups:
        # Logbook is completed, Trash is gone. Neither is "now".
        if group.get("title") in ("Logbook", "Trash"):
            continue
        for t in group.get("items", []):
            uid = t.get("uuid")
            if not uid or uid in seen or t.get("trashed") or t.get("status") != 0:
                continue
            seen.add(uid)
            area = t.get("area_title") or t.get("project_title") or ""
            word = area.split()[-1].upper() if area.split() else ""
            out.append(
                item(
                    id=f"things:{uid[:8]}",
                    source="things",
                    title=t.get("title", ""),
                    profile=AREA_PROFILES.get(word, REPO_FALLBACK),
                    status=(
                        "today" if uid in today
                        else "upcoming" if uid in upcoming
                        else (t.get("start") or "anytime").lower()
                    ),
                    updated=iso(t.get("modified"), naive_is_local=True),
                    deadline=iso(t.get("deadline"), naive_is_local=True),
                    url=f"things:///show?id={uid}",
                    area=area,
                    uuid=uid,
                    starts=iso(t.get("start_date"), naive_is_local=True),
                )
            )
    return out


def adapter_loops() -> list[dict]:
    """Open loops from the cognitive ledger. Profile is the loop's scope
    (work / personal / dev / meta): the ledger has no notion of owa-piggy
    profiles and a loop is always yours, so the work-profile filter skips it."""
    raw = run(["ledger", "loops", "--json"])
    if not raw:
        return []
    try:
        loops = json.loads(raw).get("items", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    out = []
    for lp in loops:
        path = Path(lp.get("path", ""))
        fm = {}
        try:
            head = path.read_text().split("---", 2)[1]
            fm = dict(re.findall(r"^(\w+):\s*(.+)$", head, re.M))
        except (OSError, IndexError):
            pass
        out.append(
            item(
                id=f"loops:{path.stem.removeprefix('loop__')[:24]}",
                source="loops",
                title=lp.get("title", ""),
                profile=fm.get("scope", "work"),
                status=lp.get("status", "open"),
                updated=iso(fm.get("updated")),
                url=str(path) if path.name else None,
            )
        )
    return out


def _wi_url(w: dict) -> str | None:
    """Browser url for a work item, from the API url owa-ado already returns.

    Turns .../<org>/_apis/wit/workItems/<id> into .../<org>/_workitems/edit/<id>
    so the organisation comes from the data rather than a name baked in here.
    """
    api = w.get("url") or ""
    m = re.match(r"(https://dev\.azure\.com/[^/]+)/.*?/(\d+)$", api)
    return f"{m.group(1)}/_workitems/edit/{m.group(2)}" if m else api or None


def adapter_ado(no_cache: bool = False) -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "ado.json"
    payload = None

    if not no_cache and cache.is_file() and time.time() - cache.stat().st_mtime < ADO_TTL:
        try:
            payload = json.loads(cache.read_text())
        except (OSError, json.JSONDecodeError):
            payload = None

    if payload is None:
        raw = run(["owa-ado", "wi", "--agent", "--mine", "--top", "200"], timeout=90)
        if not raw:
            # Network or auth is down. Serve whatever we last had rather than
            # silently dropping a whole source from the view.
            if cache.is_file():
                try:
                    payload = json.loads(cache.read_text())
                    stale = int((time.time() - cache.stat().st_mtime) / 60)
                    WARNINGS.append(f"ado: bruker cache, {stale} min gammel")
                except (OSError, json.JSONDecodeError):
                    return []
            else:
                WARNINGS.append("ado: ingen data og ingen cache, kjør `owa-piggy reseed --profile nc`")
                return []
        else:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return []
            try:
                cache.write_text(json.dumps(payload))
            except OSError:
                pass

    out = []
    for w in payload.get("data", []):
        state = (w.get("state") or "").lower()
        # Resolved is not Closed: it means fixed but still sitting on the board
        # waiting to be verified and closed. That is exactly the item that needs
        # a last push, so it stays in the view.
        if state in ("closed", "removed", "done"):
            continue
        out.append(
            item(
                id=f"ado:{w.get('id')}",
                source="ado",
                title=w.get("title", ""),
                profile=ADO_PROFILE,
                status=state or "unknown",
                updated=iso(w.get("changed")),
                url=_wi_url(w),
                wi_type=w.get("type"),
                area=w.get("area"),
                iteration=w.get("iteration"),
            )
        )
    return out


# ---------------------------------------------------------------- rendering


URGENT_DAYS = 14


def mark_dupes(items: list[dict]) -> int:
    """Flag, never drop, a Things/plans row that names an ADO id in its title.

    The ids come from the ADO rows themselves rather than a five-digit guess, so an
    an order number (8 digits here) or a year can never be mistaken for a work
    item. Both rows stay visible on purpose: the duplicate is a leftover from
    tracking the same work in two places, and seeing it is what prompts closing
    the Things copy.
    """
    ado = {i["id"].split(":", 1)[1]: i for i in items if i["source"] == "ado"}
    if not ado:
        return 0
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, ado)) + r")\b")
    n = 0
    for rec in items:
        if rec["source"] == "ado":
            continue
        # A plan says which work item it belongs to; Things only says it in
        # the title. Trust the declaration before the regex.
        hit = next((i for i in rec.get("ado_ids") or [] if i in ado), None)
        if not hit:
            m = pattern.search(rec["title"])
            hit = m.group(1) if m else None
        if hit and ado[hit]["profile"] == rec["profile"]:
            rec["dupe_of"] = ado[hit]["id"]
            n += 1
    return n


def epoch(ts: str | None) -> float:
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return 0.0


def sort_key(rec: dict):
    """How a human triages: what is due soon, then what you touched last.

    A deadline only jumps the queue when it is inside the horizon. A due date
    three months out should not outrank something you were working on an hour
    ago, which is what a plain deadline-first sort does.
    """
    dl = rec.get("deadline")
    soon = dl if dl and age_days(dl) is not None and age_days(dl) > -URGENT_DAYS else None
    return (0 if soon else 1, soon or "", -epoch(rec.get("updated")))


BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def shorten(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def render_table(items: list[dict], color: bool, limit: int | None) -> str:
    b, d, r = (BOLD, DIM, RESET) if color else ("", "", "")
    lines = []

    if not items:
        lines.append("ingenting åpent.")

    by_profile: dict[str, list[dict]] = {}
    for rec in items:
        by_profile.setdefault(rec["profile"], []).append(rec)

    for profile in sorted(by_profile):
        rows = sorted(by_profile[profile], key=sort_key)
        shown = rows if limit is None else rows[:limit]
        lines.append(f"\n{b}{profile.upper()}{r}  {d}({len(rows)}){r}")

        cells = []
        for rec in shown:
            age = age_days(rec.get("updated"))
            when = rec["deadline"][:10] if rec.get("deadline") else (f"{age}d" if age is not None else "")
            mark = "⧉ " if rec.get("dupe_of") else ""
            cells.append((shorten(rec["id"], 34), rec["status"], mark + shorten(rec["title"], 62), when))

        w_id = max(len(c[0]) for c in cells)
        w_st = max(len(c[1]) for c in cells)
        for cid, status, title, when in cells:
            lines.append(f"  {cid:<{w_id}}  {d}{status:<{w_st}}{r}  {title}  {d}{when}{r}")
        if len(rows) > len(shown):
            lines.append(f"  {d}… +{len(rows) - len(shown)} flere (--full){r}")

    for w in WARNINGS:
        lines.append(f"\n{d}! {w}{r}")
    return "\n".join(lines) + "\n"


def render_agent(items: list[dict], sources: list[str]) -> str:
    return json.dumps(
        {
            "_owa": {
                "suite": "cj-tools",
                "tool": "now",
                "version": "0.1.0",
                "schema_version": 1,
                "command": "list",
                "sources": sources,
                "warnings": WARNINGS,
                "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            "data": sorted(items, key=sort_key),
        },
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------- main


def find_plans_dirs() -> list[Path]:
    """Every .plans/ up to two levels under ~/code, plus the global one (todo -g)."""
    roots = {HOME / "brain" / "todos"}
    roots.update((HOME / "code").glob("*/.plans"))
    roots.update((HOME / "code").glob("*/*/.plans"))
    return sorted(
        d for d in roots if d.is_dir() and "node_modules" not in d.parts and ".bak" not in d.parent.name
    )


def selfcheck() -> int:
    """The three branches of iso() and the dupe matcher, which fail silently."""
    # date-only stays put: shifting it made every deadline a day early
    assert iso("2026-08-28", naive_is_local=True)[:10] == "2026-08-28"
    assert iso("2026-08-28")[:10] == "2026-08-28"
    # naive wall-clock from Things is local, and must never land in the future
    assert age_days(iso("2026-01-01 12:00:00", naive_is_local=True)) >= 0
    # an explicit offset is respected as given
    assert iso("2026-01-01T12:00:00+02:00") == "2026-01-01T10:00:00+00:00"

    rows = [
        item(id="ado:18520", source="ado", title="Payload too large", profile="nc", status="active"),
        item(id="things:a", source="things", title="WI 18520: payload limit", profile="nc", status="anytime"),
        item(id="things:b", source="things", title="order 90000001 is missing a tab", profile="nc", status="anytime"),
        item(id="things:c", source="things", title="WI 18520 in another profile", profile="une", status="anytime"),
        item(id="things:d", source="things", title="case 118520 is unrelated", profile="nc", status="anytime"),
        item(id="plans:x", source="plans", title="Payload-plan", profile="nc", status="plan",
             ado_ids=["18520"], kind="plan"),
        item(id="plans:y", source="plans", title="Urelatert plan", profile="nc", status="plan",
             ado_ids=["99999"], kind="plan"),
    ]
    assert mark_dupes(rows) == 2, "only the real duplicates are flagged"
    assert rows[5]["dupe_of"] == "ado:18520", "an ado: link counts without a title match"
    assert not rows[6].get("dupe_of"), "a link to a closed or unknown id is not a duplicate"
    assert rows[1]["dupe_of"] == "ado:18520"
    assert not rows[2].get("dupe_of"), "an 8-digit order number is not a work item id"
    assert not rows[3].get("dupe_of"), "a match in another profile does not count"
    assert not rows[4].get("dupe_of"), "word boundary: 118520 is not 18520"
    print("selfcheck ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="now",
        description="One canonical view of what is open, across .plans, Things and ADO.",
    )
    ap.add_argument("--profile", "-p", help="only this profile (une, nc, swon, brkh, dno)")
    ap.add_argument("--source", "-s", choices=SOURCES, action="append", help="repeatable")
    ap.add_argument("--all", "-a", action="store_true", help="include non-work profiles")
    ap.add_argument("--agent", action="store_true", help="JSON output for machines")
    ap.add_argument("--no-cache", action="store_true", help="force a fresh ADO fetch")
    ap.add_argument("--full", "-f", action="store_true", help="no per-profile row cap")
    ap.add_argument("--grep", "-g", help="substring filter on title or id")
    ap.add_argument("--dupes", action="store_true", help="only rows that duplicate an ADO work item")
    ap.add_argument("--upcoming", action="store_true", help="only Things tasks scheduled to start later")
    ap.add_argument("--selfcheck", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.selfcheck:
        return selfcheck()

    load_config()

    sources = args.source or list(SOURCES)
    items: list[dict] = []
    if "plans" in sources:
        items += adapter_plans(find_plans_dirs())
    if "things" in sources:
        items += adapter_things()
    if "ado" in sources:
        items += adapter_ado(no_cache=args.no_cache)
    if "loops" in sources:
        items += adapter_loops()

    if args.profile:
        items = [i for i in items if i["profile"] == args.profile.lower()]
    elif not (args.all or args.grep):
        # Naming a needle means look everywhere. Restricting a search to the
        # work profiles made `now --grep brygga` answer "ingenting åpent" while
        # the row sat in dno, and every documented search had to carry
        # --full --all to work at all.
        # Global todos (~/brain/todos, `todo -g`) are cross-cutting like loops:
        # the work-profile filter never hides them either.
        items = [i for i in items if not WORK_PROFILES or i["profile"] in WORK_PROFILES
                 or i["source"] == "loops" or i.get("repo") == "global"]

    if args.grep:
        needle = args.grep.lower()
        # Work item numbers live in the id, not the title, so "now -g 18520"
        # found the Things copy and missed ado:18520 itself.
        items = [i for i in items if needle in i["title"].lower() or needle in i["id"].lower()]
    # Before any filtering: a duplicate that gets filtered away cannot be
    # noticed, and noticing is the whole point of flagging it.
    mark_dupes(items)

    if not (args.full or args.upcoming or args.grep):
        # A Things task earns a place here by having a deadline, sitting in
        # Today, or duplicating a work item. Anything/Someday with no date is a
        # backlog Kim keeps in Things on purpose, and 90+ of them buried the
        # work items under NC.
        items = [
            i for i in items
            if i["source"] != "things"
            or i.get("deadline")
            or i["status"] == "today"
            or i.get("dupe_of")
        ]
        # A .plans/ directory is a document library as much as a task list, and
        # the two halves are not the same thing. TODO.md lines are tasks and
        # always stay. A plan file is the document *about* work, so it shows
        # when it declares the work item it belongs to, and otherwise waits for
        # --full or --grep. Across every repo that is 90 plan files against 76
        # todo lines, and it was burying both the work items and the todos.
        items = [
            i for i in items
            if i["source"] != "plans"
            or i.get("kind") == "todo"
            or i.get("dupe_of")
        ]
    if args.grep:
        needle = args.grep.lower()
        # Work item numbers live in the id, not the title, so "now -g 18520"
        # found the Things copy and missed ado:18520 itself.
        items = [i for i in items if needle in i["title"].lower() or needle in i["id"].lower()]

    if args.upcoming:
        # Ordering falls back to recency like everything else, so lead with the
        # arrival date: it is the only thing you actually scan this list for.
        items = [i for i in items if i["status"] == "upcoming"]
        for rec in items:
            when = (rec.get("starts") or "")[:10]
            rec["title"] = f"{when}  {rec['title']}" if when else rec["title"]

    if args.dupes:
        # The footer count alone made you grep for which ones. Name the pair in
        # the id column so the row says what to close and what it duplicates.
        items = [i for i in items if i.get("dupe_of")]
        for rec in items:
            # In the title, not the id: the id column clips at 34 and ate the
            # target on exactly the long plan rows that needed it most.
            rec["title"] = f"{rec['dupe_of']}  {rec['title']}"

    shown_dupes = sum(1 for i in items if i.get("dupe_of"))
    if shown_dupes:
        WARNINGS.append(
            f"{shown_dupes} ⧉ dublett(er): samme sak i Things og ADO, lukk Things-kopien"
        )

    if args.agent:
        print(render_agent(items, sources))
    else:
        limit = None if (args.full or args.profile or args.grep
                         or args.dupes or args.upcoming) else DEFAULT_LIMIT
        sys.stdout.write(render_table(items, color=sys.stdout.isatty(), limit=limit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
