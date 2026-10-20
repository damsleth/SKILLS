#!/usr/bin/env python3
"""teams-captions — mirror Microsoft Teams live captions into a transcript file.

The CAPTURE half of the /cj-meetings skill. Polls the popped-out Teams
"Captions" window through the macOS accessibility API and keeps a markdown
transcript in sync with it. Read-only with respect to Teams: it never clicks,
types, or focuses anything.

One prerequisite the user must satisfy, in the meeting, before this runs:
  ... More -> Language and speech -> Turn on live captions

The panel may stay docked in the meeting window or be popped out; the same
container is read either way.

Stdlib only — the accessibility API is plain C, so ctypes reaches it without
pyobjc and this runs on the /usr/bin/python3 every Mac already has. Nothing to
install.

Three things about Teams shape the whole design, all found the hard way
against a live meeting:

  * Teams is a WebView2 (Chromium) app and materialises its accessibility tree
    LAZILY, tearing it down when no assistive technology has asked for a while.
    A cold read returns a window with zero children. Nothing can force this on
    demand — AXManualAccessibility, the documented Electron opt-in, is
    unsupported here (-25205). What keeps the tree alive is simply asking
    repeatedly, which the poll loop does; a cold start just needs a few
    seconds, hence the retry in check().

  * The caption backlog is MUTABLE. Teams revises entries after showing them
    as recognition catches up ("Yes perfect testing" becomes "Yes, perfect
    testing, testing." several lines later). So the transcript cannot be
    append-only: each poll re-merges the visible window and rewrites the file.
    See merge().

  * The window mixes caption entries with transient chrome (the tenant name,
    "Window is pinned" tooltips), so entries are located by their structure
    rather than by reading every static text in order. See read_pairs().
"""

import argparse
import ctypes
import ctypes.util
import difflib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime

_cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
_ax = ctypes.CDLL(ctypes.util.find_library("ApplicationServices"))
_P = ctypes.c_void_p
_UTF8 = 0x08000100

_cf.CFStringCreateWithCString.restype = _P
_cf.CFStringCreateWithCString.argtypes = [_P, ctypes.c_char_p, ctypes.c_uint32]
_cf.CFStringGetCString.argtypes = [_P, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
_cf.CFStringGetLength.restype = ctypes.c_long
_cf.CFStringGetLength.argtypes = [_P]
_cf.CFStringGetTypeID.restype = ctypes.c_ulong
_cf.CFGetTypeID.restype = ctypes.c_ulong
_cf.CFGetTypeID.argtypes = [_P]
_cf.CFArrayGetCount.restype = ctypes.c_long
_cf.CFArrayGetCount.argtypes = [_P]
_cf.CFArrayGetValueAtIndex.restype = _P
_cf.CFArrayGetValueAtIndex.argtypes = [_P, ctypes.c_long]
_cf.CFRelease.argtypes = [_P]
_cf.CFRetain.restype = _P
_cf.CFRetain.argtypes = [_P]
_ax.AXUIElementCreateApplication.restype = _P
_ax.AXUIElementCreateApplication.argtypes = [ctypes.c_int]
_ax.AXUIElementCopyAttributeValue.argtypes = [_P, _P, ctypes.POINTER(_P)]
_ax.AXIsProcessTrusted.restype = ctypes.c_bool
_ax.AXValueGetValue.restype = ctypes.c_bool
_ax.AXValueGetValue.argtypes = [_P, ctypes.c_int, _P]

_CFSTRING = _cf.CFStringGetTypeID()

PROCESS = "MSTeams"


class Elem:
    """An accessibility element whose CF lifetime follows this object's.

    Elements come out of CF arrays as BORROWED references, valid only while
    the array is alive. Retaining on the way in and releasing in __del__ hands
    the problem to Python's refcounting, so callers can hold and return
    elements freely instead of tracking array lifetimes by hand.
    """

    __slots__ = ("ref",)

    def __init__(self, ref):
        self.ref = _cf.CFRetain(ref)

    def __del__(self):
        _cf.CFRelease(self.ref)


def die(msg):
    print(f"teams-captions: {msg}", file=sys.stderr)
    sys.exit(1)


def teams_app(wait=False):
    """AXUIElement for the running Teams process, or None when `wait` and it
    is not running yet."""
    if not _ax.AXIsProcessTrusted():
        die(
            "no Accessibility permission. Grant it to the terminal running "
            "your agent in System Settings > Privacy & Security > Accessibility, "
            "then rerun."
        )
    try:
        pid = int(subprocess.check_output(["pgrep", "-x", PROCESS]).split()[0])
    except (subprocess.CalledProcessError, IndexError):
        if wait:
            return None
        die(f"{PROCESS} is not running")
    ref = _ax.AXUIElementCreateApplication(pid)
    app = Elem(ref)
    _cf.CFRelease(ref)  # Create gave us +1; Elem holds its own
    return app


def _copy(elem, name):
    """Raw AX attribute fetch. Returns (err, ref); the caller releases ref."""
    key, out = _cf.CFStringCreateWithCString(None, name.encode(), _UTF8), _P()
    err = _ax.AXUIElementCopyAttributeValue(elem.ref, key, ctypes.byref(out))
    _cf.CFRelease(key)
    return err, out


def attr(elem, name):
    """A string-valued AX attribute, or None."""
    err, val = _copy(elem, name)
    if err or not val:
        return None
    text = None
    if _cf.CFGetTypeID(val) == _CFSTRING:
        size = _cf.CFStringGetLength(val) * 4 + 8
        buf = ctypes.create_string_buffer(size)
        if _cf.CFStringGetCString(val, buf, size, _UTF8):
            text = buf.value.decode("utf-8", "replace")
    _cf.CFRelease(val)
    return text


def each(elem, name):
    """Elements of an array-valued AX attribute, as owned `Elem`s."""
    err, arr = _copy(elem, name)
    if err or not arr:
        return []
    out = [Elem(_cf.CFArrayGetValueAtIndex(arr, i))
           for i in range(_cf.CFArrayGetCount(arr))]
    _cf.CFRelease(arr)
    return out


def caption_root(app, anchor):
    """The element containing the caption entries, in any Teams window.

    Anchored on the caption container's accessibility description rather than
    on a popped-out window's title, because the same container exists whether
    captions are docked inside the meeting window or popped out — so neither
    layout needs special handling, and the user does not have to pop the panel
    out at all.

    Anchoring on *something* is necessary: caption entries are groups of two
    static texts, and chat message lists produce that same shape, so a blind
    window-wide scan would happily transcribe the wrong pane.
    """
    # ponytail: the description is Teams-UI-language dependent. Localise with
    # --anchor rather than enumerating every language here.
    needle = anchor.casefold()

    # ponytail: depth cap, because the WebView2 tree can hold a cycle and a
    # plain recursion died at depth 1000. The caption container
    # sits well above 60; raise it if a Teams update nests it deeper.
    def find(elem, depth=0):
        if needle in (attr(elem, "AXDescription") or "").casefold():
            return elem
        if depth >= 60:
            return None
        for kid in each(elem, "AXChildren"):
            hit = find(kid, depth + 1)
            if hit is not None:
                return hit
        return None

    for win in each(app, "AXWindows"):
        hit = find(win)
        if hit is not None:
            return hit
    return None


def read_pairs(root):
    """Visible caption entries as [(speaker, text), ...], oldest first.

    Each entry is an AXGroup holding exactly two AXStaticText children —
    speaker name, then caption text. Matching on that shape is what makes
    this robust: the window also contains loose static texts (the tenant
    name, and transient tooltips like "Window is pinned") which appear and
    disappear, and any scheme that just collected every static text in order
    would have its speaker/text alternation shifted by one every time a
    tooltip came or went, silently swapping attribution on every line.
    """
    out = []

    def walk(elem):
        kids = each(elem, "AXChildren")
        if len(kids) == 2 and all(attr(k, "AXRole") == "AXStaticText" for k in kids):
            speaker = (attr(kids[0], "AXValue") or "").strip()
            text = (attr(kids[1], "AXValue") or "").strip()
            if speaker and text:
                out.append((speaker, text))
            return
        for kid in kids:
            walk(kid)

    walk(root)
    return out


SAME = 0.7  # text similarity above which two entries are the same utterance
TAIL = 3    # newest transcript lines Teams may rewrite past recognition, see merge()


def _norm(text):
    return " ".join(re.sub(r"[^\w\s]", " ", text.casefold()).split())


def same_entry(a, b):
    """Is `b` the same caption entry as `a`, allowing for Teams' revisions?

    Teams rewrites entries after showing them, in two shapes seen live: the
    newest line grows as recognition catches up ("It is" -> "It is a nice
    day."), and settled lines get repunctuated ("Yes perfect testing" ->
    "Yes, perfect testing, testing."). Growth scores too low to catch by
    similarity alone (0.45), hence the prefix test; repunctuation scores 0.78
    to 0.95. Distinct short utterances score below 0.35, so they stay distinct.
    """
    if a[0] != b[0]:
        return False
    # Compare without case and punctuation: the newest line grows AND gets
    # repunctuated in the same revision ("ta nå så jeg" -> "ta nå, så jeg
    # bare..."), and the comma alone broke the prefix test. One failed pair
    # fails every overlap width, so merge() appended the whole ~30-line window
    # again; that is what duplicated whole transcripts.
    x, y = _norm(a[1]), _norm(b[1])
    if x == y:
        return True
    # ponytail: 4 chars, so "So" cannot prefix-swallow "So I don't have a clue"
    if min(len(x), len(y)) >= 4 and (x.startswith(y) or y.startswith(x)):
        return True
    # autojunk off: from 200 chars on, SequenceMatcher's default treats every
    # common letter and the space as junk, and a repunctuated 250-char caption
    # scored 0.42 instead of 0.92. Long captions are routine, and
    # one such failed pair re-appended a whole window four times.
    return difflib.SequenceMatcher(None, x, y, autojunk=False).ratio() > SAME


def merge(hist, visible, stamp):
    """Fold the visible caption window into `hist` (list of [ts, speaker, text]).

    Entries scroll off the top, get appended at the bottom, AND get revised in
    place. So this finds the longest overlap between the END of the transcript
    and the START of the window, then replaces that overlap with the window's
    authoritative text. Unrevised lines keep their original timestamp.

    Anchoring on the tail specifically — rather than the best match anywhere in
    `hist` — is what makes a repeated utterance safe. A bare "OK." after a
    silence matches some "OK." from twenty minutes ago, and treating that as
    the anchor would delete everything said in between.

    The overlap may stop up to TAIL lines short of the transcript's end. Those
    newest lines are interim captions, and Teams rewrites them past any fuzzy
    match: "SO yeah" becomes "SO.", "Basically three end." becomes a 240-char
    line, a fragment is reattributed to whoever kept talking, or three short
    interims collapse into other utterances. Demanding that the overlap reach
    the very last line meant no width anchored, so the whole window was
    appended again; that is what duplicated a whole standup eight times.
    """
    if not visible:
        return hist
    keys = [(s, t) for _, s, t in hist]
    k = 0
    for width in range(min(len(keys), len(visible) + TAIL), 0, -1):
        for slack in range(TAIL + 1):
            n = width - slack  # pairs that must match; the rest are replaced
            # ponytail: slack needs 3 matched lines AND new lines after them,
            # so a short window after a silence (["Yeah.", "OK."]) cannot
            # anchor a few lines up and delete what came after.
            if n > len(visible) or slack and (n < 3 or n == len(visible)):
                continue
            if all(same_entry(a, b) for a, b in zip(keys[len(keys) - width:], visible[:n])):
                k = width
                break
        if k:
            break
    old = hist[len(hist) - k:] if k else []
    hist[len(hist) - k:] = [
        old[n] if n < k and old[n][2] == text else [stamp, speaker, text]
        for n, (speaker, text) in enumerate(visible)
    ]
    return hist


LINE = re.compile(r"^\*\*(\d\d:\d\d) (.+?):\*\* (.*)$")


def load(path):
    """Existing transcript as (started, hist), so a restart RESUMES it.

    Capture dies for boring reasons mid-meeting — a stray signal, a laptop
    sleeping, the operator restarting it after Teams tore its a11y tree down.
    Starting fresh on the same --out would truncate everything said so far, and
    a meeting cannot be replayed. So the file is read back instead: parse the
    lines we wrote, keep their timestamps, and let merge() anchor the visible
    window onto that tail exactly as if the process had never stopped.

    Anything unparseable (a hand-added note, a stray heading) is skipped rather
    than treated as a caption, so the file survives being edited between runs.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (FileNotFoundError, IsADirectoryError):
        return None, []
    head = re.search(r"<!-- teams-captions, started (.+?) -->", text)
    hist = [[m.group(1), m.group(2), m.group(3)]
            for m in (LINE.match(ln) for ln in text.splitlines()) if m]
    return (head.group(1).strip() if head else None), hist


def write(path, hist, started):
    """Rewrite the transcript atomically — a crash must not truncate it."""
    body = [f"<!-- teams-captions, started {started} -->\n\n"]
    body += [f"**{ts} {s}:** {t}\n" for ts, s, t in hist]
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(body)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def rect(elem):
    """(x, y, w, h) of a window in global screen points, or None."""
    out = []
    for name, kind in (("AXPosition", 1), ("AXSize", 2)):  # kAXValueCGPoint/CGSizeType
        err, val = _copy(elem, name)
        if err or not val:
            return None
        pair = (ctypes.c_double * 2)()
        ok = _ax.AXValueGetValue(val, kind, pair)
        _cf.CFRelease(val)
        if not ok:
            return None
        out += [int(v) for v in pair]
    return tuple(out)


def meeting_window(wins):
    """Pick the meeting window from [(title, rect), ...].

    The popped-out captions window is titled "Captions | <meeting title>", so
    the meeting window is the one carrying that title. Without captions, fall
    back to the largest window: the meeting stage is wider than the chat pane.
    """
    # ponytail: largest-window fallback misfires if the main Teams window is
    # bigger than the meeting; turn captions on and it never gets used.
    titles = {t for t, _ in wins}
    for t, r in wins:
        if t and t.startswith("Captions | ") and t[11:] in titles:
            return next(r2 for t2, r2 in wins if t2 == t[11:])
    rest = [(r[2] * r[3], r) for t, r in wins
            if r and not (t or "").startswith("Captions | ")]
    return max(rest)[1] if rest else None


def shot_target(notes, stamp):
    """(png path, embed line) for a screenshot belonging to the notes file.

    Inside an Obsidian vault the vault's own attachment setting decides where
    it goes and the embed is a wikilink; anywhere else the image lands next to
    the notes and gets a plain relative markdown link. No paths are baked in,
    so the skill works in anyone's folder layout.
    """
    notes = os.path.abspath(notes)
    here = os.path.dirname(notes)
    name = f"{os.path.splitext(os.path.basename(notes))[0]}-{stamp}.png"
    vault = here
    while not os.path.isdir(os.path.join(vault, ".obsidian")):
        if os.path.dirname(vault) == vault:
            return os.path.join(here, name), f"![]({name})"
        vault = os.path.dirname(vault)
    try:
        with open(os.path.join(vault, ".obsidian", "app.json")) as f:
            folder = json.load(f).get("attachmentFolderPath") or "./"
    except (OSError, ValueError):
        folder = "./"
    # "./x" is relative to the note, anything else to the vault root
    base = here if folder.startswith("./") or folder == "." else vault
    return os.path.join(base, folder.lstrip("./") if base == here else folder,
                        name), f"![[{name}]]"


def shot(app, target):
    """Screenshot the Teams meeting window, whichever display it is on.

    `target` is the meeting notes file (placement and embed are derived from
    it, see shot_target) or an explicit .png path. Prints the png path, a
    downscaled preview path for reading, and the embed line.
    """
    wins = [(attr(w, "AXTitle"), rect(w)) for w in each(app, "AXWindows")]
    r = meeting_window([(t, r) for t, r in wins if r])
    if r is None:
        die("no Teams meeting window found")
    stamp = datetime.now().strftime("%H%M%S")
    if target.endswith(".png"):
        path, embed = target, f"![]({os.path.basename(target)})"
    else:
        path, embed = shot_target(target, stamp)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    subprocess.run(["screencapture", "-x", "-R", ",".join(map(str, r)), path],
                   check=True)
    preview = os.path.join(tempfile.gettempdir(), "preview-" + os.path.basename(path))
    subprocess.run(["sips", "-Z", "1400", path, "--out", preview],
                   check=True, stdout=subprocess.DEVNULL)
    print(f"png: {path}\npreview: {preview}\nembed: {embed}")
    return 0


def check(app, anchor, tries=4):
    root = caption_root(app, anchor)
    if root is None:
        print(f"NOT FOUND: no caption panel (looked for '{anchor}')", file=sys.stderr)
        print("Open Teams windows:", file=sys.stderr)
        for w in each(app, "AXWindows"):
            print(f"  - {attr(w, 'AXTitle') or '?'}", file=sys.stderr)
        print(
            "\nIn the meeting: '... More' > 'Language and speech' > 'Turn on "
            "live captions'. The panel may stay docked in the meeting window; "
            "it does not need popping out. If the Teams UI is not in English, "
            "pass the localised panel name with --anchor.",
            file=sys.stderr,
        )
        return 1
    # A cold Chromium a11y tree reads as an empty window, and asking again is
    # the only thing that wakes it — so never judge emptiness on one read.
    for attempt in range(tries):
        pairs = read_pairs(root)
        if pairs:
            break
        if attempt < tries - 1:
            time.sleep(1.5)
    print(f"OK: caption panel found, {len(pairs)} line(s) currently visible")
    for speaker, text in pairs[-5:]:
        print(f"  {speaker}: {text}")
    if not pairs:
        print("  (nothing captioned yet — either nobody has spoken recently, "
              "or Teams is still waking its accessibility tree; capture will "
              "pick lines up as they appear)")
    return 0


def blind_step(blind, seen_any, pairs, limit):
    """Advance the cold-a11y-tree counter for one poll of a *found* panel.

    Returns (blind, seen_any, stop). Split out of capture() only so demo() can
    exercise it without a live accessibility tree.
    """
    if pairs:
        return 0, True, False
    if seen_any and limit:
        blind += 1
        return blind, seen_any, blind >= limit
    return blind, seen_any, False


def frozen_step(frozen, last, pairs, limit):
    """Advance the frozen-panel counter for one poll of a *found* panel.
    Returns (frozen, last, stop).

    A minimized Teams window keeps its caption panel in the a11y tree but
    stops updating it, so every read returns the same non-empty lines: neither
    `gone` nor `blind` rises, and capture rewrites an unchanged file. That
    once ate 12 of a 15-minute standup. Empty reads are left to
    blind_step; a live meeting changes the panel well within the limit.
    """
    if not pairs or pairs != last:
        return 0, pairs, False
    frozen += 1
    return frozen, last, bool(limit) and frozen >= limit


def gone_step(gone, seen_panel, found, limit):
    """Advance the panel-missing counter for one poll. Returns (gone,
    seen_panel, stop).

    Only counts once the panel has been seen, so capture can be started BEFORE
    the meeting and simply wait. Gating it on an early check, made before
    Teams was running, once lost the first 19 minutes of a standup.
    """
    if found:
        return 0, True, False
    if not seen_panel:
        return 0, False, False
    gone += 1
    return gone, True, gone >= limit


def capture(app, anchor, path, interval, gone_limit, blind_limit, frozen_limit):
    started, hist = load(path)
    if hist:
        print(f"teams-captions: resuming {path} — {len(hist)} line(s) already there")
    started = started or datetime.now().strftime("%Y-%m-%d %H:%M")
    gone, root, reason = 0, None, "interrupted"

    # The failure this exists for: the panel is still there, so `gone` never
    # rises, but the WebView2 a11y tree has gone cold and every read comes back
    # empty. Capture looks healthy and writes nothing. That once ate 18
    # of a 32-minute meeting, undetected until wrap-up, when it was too late to
    # recover. Exiting is what makes it visible: the caller is notified when this
    # process ends, where a warning on stdout would sit unread.
    #
    # `blind` only counts polls where the panel was FOUND but yielded nothing,
    # and only after the panel has produced at least one entry — a meeting where
    # nobody has spoken yet reads empty for legitimate reasons.
    blind, seen_any = 0, False
    frozen, last = 0, None
    seen_panel, waiting_said = False, False

    # SIGTERM/SIGHUP unwind through the same path as ctrl-c, so a kill or a
    # closing terminal still reports how far it got instead of vanishing.
    def stop(signum, frame):
        raise KeyboardInterrupt

    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, stop)

    print(f"teams-captions: mirroring to {path} every {interval}s (ctrl-c to stop)")
    write(path, hist, started)
    try:
        while True:
            # ponytail: waits for Teams and the panel indefinitely before the
            # first sighting; the caller stops it with pkill like any capture.
            if app is None:
                app = teams_app(wait=True)
            # The cached root survives re-renders, so only re-scan when it
            # stops yielding — a full tree walk every poll would be wasteful.
            pairs = read_pairs(root) if root is not None else []
            if not pairs and app is not None:
                root = caption_root(app, anchor)
                pairs = read_pairs(root) if root is not None else []
            gone, seen_panel, stop = gone_step(gone, seen_panel, root is not None,
                                               gone_limit)
            if stop:
                reason = "caption panel gone"
                break
            if root is None:
                if not seen_panel and not waiting_said:
                    print("teams-captions: waiting for Teams and the caption panel "
                          "(turn on live captions in the meeting)")
                    waiting_said = True
            else:
                blind, seen_any, cold = blind_step(blind, seen_any, pairs, blind_limit)
                if cold:
                    reason = "panel found but reading empty"
                    break
                frozen, last, stuck = frozen_step(frozen, last, pairs, frozen_limit)
                if stuck:
                    reason = "panel frozen"
                    break
                merge(hist, pairs, datetime.now().strftime("%H:%M"))
                write(path, hist, started)
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
    print(f"teams-captions: stopped ({reason}) — {len(hist)} line(s) in {path}")
    print("teams-captions: rerun with the same --out to resume; it will not truncate")
    if reason == "panel found but reading empty":
        secs = int(blind_limit * interval)
        print(f"teams-captions: WARNING — nothing captured for {secs}s while the "
              f"caption panel was still open. Usually the a11y tree went cold.")
        print("teams-captions: ask the user to close and re-pop the captions "
              "panel, then rerun with the same --out.")
        print("teams-captions: if the meeting was simply silent, rerun with a "
              "larger --stop-after-blind (or 0 to disable).")
        return 2
    if reason == "panel frozen":
        secs = int(frozen_limit * interval)
        print(f"teams-captions: WARNING: the caption panel showed the same lines "
              f"for {secs}s. Teams stops updating a minimized window.")
        print("teams-captions: ask the user to restore the meeting and captions "
              "windows, then rerun with the same --out.")
        print("teams-captions: if the meeting was simply silent, rerun with a "
              "larger --stop-after-frozen (or 0 to disable).")
        return 3
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="transcript file to keep in sync")
    ap.add_argument("--shot", metavar="NOTES_OR_PNG",
                    help="screenshot the Teams meeting window next to the notes "
                         "file (or the vault's attachment folder), then exit; a "
                         ".png path saves exactly there (needs Screen Recording "
                         "permission)")
    ap.add_argument("--check", action="store_true",
                    help="verify the caption window is readable, then exit")
    ap.add_argument("--interval", type=float, default=5.0,
                    help="seconds between polls (default: 5)")
    ap.add_argument("--anchor", default="Live Captions",
                    help="caption panel's accessibility name, for non-English "
                         "Teams UIs (default: 'Live Captions')")
    ap.add_argument("--stop-after-missing", type=int, default=12, metavar="N",
                    help="stop after N polls with no caption panel (default: "
                         "12, so a docked panel re-rendering does not end it)")
    ap.add_argument("--stop-after-blind", type=int, default=36, metavar="N",
                    help="stop after N polls where the panel is present but "
                         "reads empty, the signature of a cold a11y tree "
                         "(default: 36, so 3 min at the default interval; "
                         "0 disables the check)")
    ap.add_argument("--stop-after-frozen", type=int, default=36, metavar="N",
                    help="stop after N polls where the panel shows the same "
                         "lines, the signature of a minimized Teams window "
                         "(default: 36, so 3 min at the default interval; "
                         "0 disables the check)")
    args = ap.parse_args()

    if args.shot:
        return shot(teams_app(), args.shot)
    if args.check:
        return check(teams_app(), args.anchor)
    if not args.out:
        ap.error("--out is required unless --check is given")
    # Capture waits for Teams and the panel instead of bailing, so it can be
    # started before the meeting (see gone_step).
    return capture(teams_app(wait=True), args.anchor, args.out, args.interval,
                   args.stop_after_missing,
                   args.stop_after_blind, args.stop_after_frozen)


def demo():
    """Self-check for the two pieces of non-obvious logic."""
    # a caption entry is a group of exactly two static texts; loose static
    # texts and tooltips around it must not shift attribution
    class Fake:
        def __init__(self, role, value=None, kids=(), desc=""):
            self.role, self.value, self.kids, self.desc = role, value, kids, desc

    def txt(v):
        return Fake("AXStaticText", v)

    def entry(speaker, text):
        return Fake("AXGroup", kids=[txt(speaker), txt(text)])

    # the meeting window is found by the captions window's title, even when
    # the main window is bigger; without captions, the largest window wins
    m, c, big = (0, 0, 9, 9), (0, 0, 1, 1), (0, 0, 99, 99)
    assert meeting_window([("Chat | X | Teams", big), ("Mtg | Teams", m),
                           ("Captions | Mtg | Teams", c)]) == m
    assert meeting_window([("Chat | X", (0, 0, 2, 2)), ("Mtg", m)]) == m
    assert meeting_window([]) is None

    # screenshot placement: vault attachment setting, else next to the notes
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "v", ".obsidian"))
    os.makedirs(os.path.join(root, "v", "work"))
    os.makedirs(os.path.join(root, "plain"))
    cfg = os.path.join(root, "v", ".obsidian", "app.json")
    note = os.path.join(root, "v", "work", "m.md")
    with open(cfg, "w") as f:
        json.dump({"attachmentFolderPath": "att"}, f)
    assert shot_target(note, "1000") == (
        os.path.join(root, "v", "att", "m-1000.png"), "![[m-1000.png]]")
    with open(cfg, "w") as f:
        json.dump({"attachmentFolderPath": "./img"}, f)
    assert shot_target(note, "1000")[0] == os.path.join(root, "v", "work", "img", "m-1000.png")
    with open(cfg, "w") as f:
        json.dump({}, f)
    assert shot_target(note, "1000")[0] == os.path.join(root, "v", "work", "m-1000.png")
    assert shot_target(os.path.join(root, "plain", "m.md"), "1000") == (
        os.path.join(root, "plain", "m-1000.png"), "![](m-1000.png)")

    global attr, each
    real_attr, real_each = attr, each
    attr = lambda e, n: {"AXRole": e.role, "AXValue": e.value,
                         "AXDescription": e.desc, "AXTitle": e.desc}[n]
    each = lambda e, n: list(e.kids)
    win = Fake("AXWindow", kids=[
        txt("Contoso"),                       # tenant label
        Fake("AXGroup", kids=[entry("Kari", "Hei."), entry("Ola", "Hei selv.")]),
        txt("Window is pinned."),                  # transient tooltip
    ])
    assert read_pairs(win) == [("Kari", "Hei."), ("Ola", "Hei selv.")]
    # ...and identically with the tooltip absent (the parity flip that bit us)
    win.kids = [txt("Contoso"),
                Fake("AXGroup", kids=[entry("Kari", "Hei."), entry("Ola", "Hei selv.")])]
    assert read_pairs(win) == [("Kari", "Hei."), ("Ola", "Hei selv.")]

    # the anchor is what keeps a chat pane from being transcribed: chat
    # messages are the same two-static-text shape as caption entries
    chat = Fake("AXWindow", kids=[Fake("AXGroup", kids=[entry("Kari", "hei"),
                                                       entry("Ola", "hei")])])
    captions = Fake("AXWindow", kids=[
        Fake("AXGroup", desc="Live Captions",
             kids=[Fake("AXGroup", kids=[entry("Kari", "Hei.")])])])
    app = Fake("AXApp", kids=[chat, captions])
    each = lambda e, n: list(e.kids)  # AXWindows and AXChildren alike
    assert read_pairs(caption_root(app, "Live Captions")) == [("Kari", "Hei.")]
    assert caption_root(Fake("AXApp", kids=[chat]), "Live Captions") is None
    attr, each = real_attr, real_each

    def texts(h):
        return [t for _, _, t in h]

    h = []
    merge(h, [("K", "a"), ("K", "b")], "10:00")
    assert texts(h) == ["a", "b"]
    # plain append
    merge(h, [("K", "a"), ("K", "b"), ("K", "c")], "10:01")
    assert texts(h) == ["a", "b", "c"]
    assert h[0][0] == "10:00" and h[2][0] == "10:01"  # old timestamps preserved
    # entries scrolling off the top do not resurrect or duplicate
    merge(h, [("K", "b"), ("K", "c"), ("K", "d")], "10:02")
    assert texts(h) == ["a", "b", "c", "d"], texts(h)
    # genuine repeats are kept — a dedupe-by-value scheme would drop one
    merge(h, [("K", "d"), ("K", "Ja."), ("K", "Ja.")], "10:03")
    assert texts(h) == ["a", "b", "c", "d", "Ja.", "Ja."], texts(h)
    # captions clearing on silence must not wipe the transcript
    merge(h, [], "10:04")
    assert len(h) == 6
    # ...nor may resuming with a line said earlier truncate back to it
    merge(h, [("K", "c")], "10:05")
    assert texts(h) == ["a", "b", "c", "d", "Ja.", "Ja.", "c"], texts(h)

    # the two revision shapes observed in a live meeting
    r = []
    merge(r, [("K", "Hei."), ("K", "It is")], "11:00")
    merge(r, [("K", "Hei."), ("K", "It is a nice day.")], "11:01")
    assert texts(r) == ["Hei.", "It is a nice day."], texts(r)
    merge(r, [("K", "Hei."), ("K", "It is a nice day."),
              ("K", "Yes perfect testing")], "11:02")
    merge(r, [("K", "Hei."), ("K", "It is a nice day."),
              ("K", "Yes, perfect testing, testing.")], "11:03")
    assert texts(r) == ["Hei.", "It is a nice day.",
                        "Yes, perfect testing, testing."], texts(r)
    assert r[0][0] == "11:00"  # an untouched line keeps its timestamp
    # front-drop: "Hei." scrolls out of the window as a new line arrives
    merge(r, [("K", "It is a nice day."), ("K", "Yes, perfect testing, testing."),
              ("K", "Are recording the memo they were not")], "11:04")
    assert texts(r) == ["Hei.", "It is a nice day.",
                        "Yes, perfect testing, testing.",
                        "Are recording the memo they were not"], texts(r)
    # front-drop AND a repunctuation of an already-written line, same poll
    merge(r, [("K", "Yes, perfect testing, testing."),
              ("K", "Are recording the memo. They were not."), ("K", "Two B.")], "11:05")
    assert texts(r) == ["Hei.", "It is a nice day.",
                        "Yes, perfect testing, testing.",
                        "Are recording the memo. They were not.",
                        "Two B."], texts(r)
    # cold-a11y-tree detection: the panel is found but reads empty, which is
    # what silently ate 18 of a 32-minute meeting
    b, seen = 0, False
    # empty reads before anyone has spoken are legitimate and must not count
    for _ in range(99):
        b, seen, stop = blind_step(b, seen, [], 3)
        assert (b, seen, stop) == (0, False, False)
    b, seen, stop = blind_step(b, seen, [("K", "Hei.")], 3)   # first real entry
    assert (b, seen, stop) == (0, True, False)
    b, seen, stop = blind_step(b, seen, [], 3)
    assert (b, stop) == (1, False)
    b, seen, stop = blind_step(b, seen, [], 3)
    assert (b, stop) == (2, False)
    b, seen, stop = blind_step(b, seen, [], 3)
    assert (b, stop) == (3, True)                             # trips at the limit
    # a single good read rearms it, so ordinary pauses never accumulate
    b, seen, stop = blind_step(2, True, [("K", "Ja.")], 3)
    assert (b, stop) == (0, False)
    # limit 0 disables the check outright
    b, seen, stop = blind_step(99, True, [], 0)
    assert stop is False

    # frozen-panel detection: a minimized window keeps returning the same
    # lines, which ate 12 of a 15-minute standup
    w1, w2 = [("K", "Hei.")], [("K", "Hei."), ("O", "Hallo.")]
    f, last, stop = frozen_step(0, None, w1, 3)
    assert (f, stop) == (0, False)
    for n in (1, 2):
        f, last, stop = frozen_step(f, last, list(w1), 3)
        assert (f, stop) == (n, False)
    f, last, stop = frozen_step(f, last, list(w1), 3)
    assert (f, stop) == (3, True)                              # trips at the limit
    f, last, stop = frozen_step(2, w1, w2, 3)                  # a new line rearms it
    assert (f, last, stop) == (0, w2, False)
    f, last, stop = frozen_step(2, w1, [], 3)                  # empty is blind_step's job
    assert (f, stop) == (0, False)
    f, last, stop = frozen_step(99, w1, list(w1), 0)           # limit 0 disables it
    assert stop is False

    # distinct short utterances must not fuzzy-merge into one another
    assert not same_entry(("K", "OK."), ("K", "No."))
    assert not same_entry(("K", "Ja."), ("K", "Nei."))
    assert not same_entry(("K", "Hei."), ("O", "Hei."))  # different speaker

    # a restart must RESUME the transcript, never truncate it — the bug that
    # ate the first 12 minutes of a real meeting
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.md")
        assert load(path) == (None, [])            # no file yet
        write(path, [["13:08", "Kari", "Hei."],
                     ["13:09", "Ola", "Hei: selv."]], "2026-08-24 13:08")
        started, back = load(path)
        assert started == "2026-08-24 13:08", started
        assert back == [["13:08", "Kari", "Hei."],
                        ["13:09", "Ola", "Hei: selv."]], back   # colon in text survives
        # resuming and merging an overlapping window appends, keeps old stamps
        merge(back, [("Ola", "Hei: selv."), ("Kari", "Og hei igjen.")], "13:20")
        assert texts(back) == ["Hei.", "Hei: selv.", "Og hei igjen."], texts(back)
        assert back[0][0] == "13:08"
        # non-caption lines in the file are ignored rather than transcribed
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n## en overskrift noen limte inn\n")
        assert len(load(path)[1]) == 2

    # a growing newest line that is also repunctuated is the SAME entry; each
    # of these pairs is a real boundary where a whole window got duplicated
    for old, new in [
        ("Ja det kan du bare ta nå så jeg bare",
         "Ja det kan du bare ta nå, så jeg bare nevne et. Jeg var avlyse denne."),
        ("Oh OK that's", "Oh, OK."),
        ("Thank you just to can answer the custom",
         "Thank you. Just to can answer the customers and see they asked about it."),
    ]:
        assert same_entry(("K", old), ("K", new)), old
    # ...so merging the revised window no longer re-appends it
    w = [("B", "We should keep test and prod in sync."), ("S", "Absolutely."),
         ("B", "Thank you just to can answer the custom")]
    d = []
    merge(d, w, "09:07")
    merge(d, w[:2] + [("B", "Thank you. Just to can answer the customers."),
                      ("B", "Have a good day everyone.")], "09:08")
    assert texts(d) == ["We should keep test and prod in sync.", "Absolutely.",
                        "Thank you. Just to can answer the customers.",
                        "Have a good day everyone."], texts(d)

    # every window one live meeting re-appended, by shape. Real strings.
    # (1) a long line repunctuated inside the overlap; SequenceMatcher's
    # autojunk scored this 0.42, which failed every width
    a = ("B", "Well, then I'm after. I'm definitely down for that. I I went with "
              "that suggestion because I thought, you know what it it makes sense "
              "to me. But I initially I kind of leaned towards a script that would "
              "just populate, create a group associated to the role.")
    b = ("B", "Well then, I'm definitely down for that. I went with that suggestion "
              "because I thought, you know what, it makes sense to me, but initially "
              "I kind of leaned towards a script that would just populate, create a "
              "group associated to the role and make all sites equal.")
    assert same_entry(a, b)
    d = []
    merge(d, [("C", "Yes."), ("B", "Sure."), a], "09:19")
    merge(d, [("B", "Sure."), b, ("B", "Let's do it then.")], "09:20")
    assert texts(d) == ["Yes.", "Sure.", b[1], "Let's do it then."], texts(d)
    # (2) the window's front has scrolled on AND the transcript's newest
    # line, an interim, was rewritten past any fuzzy match
    d = []
    merge(d, [("B", "Maybe once, right?"), ("M", "It shouldn't."), ("B", "Per site."),
              ("B", "Right, like it shouldn't."), ("B", "SO yeah")], "08:54")
    merge(d, [("M", "It shouldn't."), ("B", "Per site."), ("B", "Right, like it shouldn't."),
              ("B", "SO."), ("K", "Do you call this updates?")], "08:55")
    assert texts(d) == ["Maybe once, right?", "It shouldn't.", "Per site.",
                        "Right, like it shouldn't.", "SO.",
                        "Do you call this updates?"], texts(d)
    # ...also when Teams hands the interim to whoever kept talking
    merge(d, [("B", "Right, like it shouldn't."), ("B", "SO."),
              ("K", "Do you call this updates?"), ("S", "SO probably.")], "09:02")
    merge(d, [("B", "Right, like it shouldn't."), ("B", "SO."),
              ("K", "Do you call this updates?"),
              ("B", "That there was no runs in the portal."), ("S", "Yeah.")], "09:03")
    assert texts(d)[-3:] == ["Do you call this updates?",
                             "That there was no runs in the portal.", "Yeah."], texts(d)
    assert texts(d).count("SO.") == 1 and "SO probably." not in texts(d)
    # (3) a long newest line that grows and is repunctuated in one revision
    grow = ("C", "So internal priority would be to harmonize the SPF versions. So "
                 "'cause. Right now we have like 3-4 different versions which kinda "
                 "sucks. So having all on on Hefts build pack on 23 something is also "
                 "makes it a lot easier to to streamline the the pipeline, so might do "
                 "that at the same time as I I.")
    full = ("C", "So internal priority would be to harmonize the SPFX for versions. So "
                 "because right now we have like 3, four different versions, which kind "
                 "of sucks. So having all on heft build back on 23 something is also "
                 "makes it a lot easier to streamline the pipeline. So it might do that.")
    lead = [("B", "Yeah."), ("C", "Right."), ("B", "Cool.")]
    d = []
    merge(d, lead + [grow], "09:22")
    merge(d, lead + [full, ("C", "at the same time as I fix the...")], "09:23")
    assert texts(d) == ["Yeah.", "Right.", "Cool.", full[1],
                        "at the same time as I fix the..."], texts(d)
    # the slack stays near the tail: a short window after a silence that
    # repeats two earlier lines must not anchor there and delete the rest
    d = [["10:00", "K", "Yeah."], ["10:00", "K", "OK."], ["10:00", "O", "Then we ship it."]]
    merge(d, [("K", "Yeah."), ("K", "OK.")], "10:10")
    merge(d, [("K", "Yeah."), ("K", "OK."), ("O", "Agreed.")], "10:11")
    assert "Then we ship it." in texts(d), texts(d)
    # no overlap at all (the window scrolled clean past the tail): plain append
    d = [["10:00", "K", "Hei."]]
    merge(d, [("O", "Something new."), ("O", "And more.")], "10:20")
    assert texts(d) == ["Hei.", "Something new.", "And more."], texts(d)

    # capture started before the meeting waits for the panel instead of quitting
    g, seen_p = 0, False
    for _ in range(99):
        g, seen_p, stop = gone_step(g, seen_p, False, 3)
        assert (g, seen_p, stop) == (0, False, False)
    g, seen_p, stop = gone_step(g, seen_p, True, 3)            # panel appears
    assert (g, seen_p, stop) == (0, True, False)
    for n in (1, 2):
        g, seen_p, stop = gone_step(g, seen_p, False, 3)
        assert (g, stop) == (n, False)
    g, seen_p, stop = gone_step(g, seen_p, False, 3)
    assert stop is True                                        # meeting over

    print("demo: ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        sys.exit(main())
