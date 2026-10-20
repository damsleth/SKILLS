#!/usr/bin/python3
"""Print the Teams Facilitator notes of a meeting as text.

Facilitator writes its notes to a Loop page, "<subject> <date>.loop", in the
organizer's OneDrive and shares it with the attendees. Graph lists it under
sharedWithMe and serves the bytes, so the owa-piggy token the rest of the
skill already uses is enough. The container is a "Microsoft.Prague" tree with
gzip blobs of JSON: a snapshot (segmentTexts) plus the sequenced merge-tree
ops (insert/remove at a position). Both are printed, labelled with the
author Loop recorded ("AI-generated" is Facilitator).

    facilitator-recap.py --profile work "Team standup" 2026-10-15
    facilitator-recap.py --file notes.loop
    facilitator-recap.py --demo

Stdlib only, like teams-captions.py. Needs owa-graph on PATH for --profile.
"""
import argparse, gzip, io, json, re, subprocess, sys, urllib.request, zlib

DEC = json.JSONDecoder()


def graph(profile, path):
    out = subprocess.run(["owa-graph", "--profile", profile, "GET", path],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"owa-graph {path}: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout)


def fetch(profile, subject, date):
    want = f"{subject} {date}.loop".lower()
    for it in graph(profile, "/me/drive/sharedWithMe").get("value", []):
        if it.get("name", "").lower() == want:
            r = it["remoteItem"]
            item = graph(profile, f"/drives/{r['parentReference']['driveId']}/items/{r['id']}")
            return urllib.request.urlopen(item["@microsoft.graph.downloadUrl"], timeout=30).read()
    sys.exit(f"no '{want}' in sharedWithMe for profile {profile}; "
             "the meeting had no Facilitator, or the page was not shared with you")


def blobs(data):
    for m in re.finditer(rb"\x1f\x8b\x08", data):
        try:
            yield zlib.decompressobj(31).decompress(data[m.start():]).decode("utf-8", "replace")
        except zlib.error:
            pass


def objects(s):
    """Every JSON object in a blob, in file order (blobs are binary with JSON islands)."""
    i = 0
    while True:
        j = s.find("{", i)
        if j < 0:
            return
        try:
            obj, i = DEC.raw_decode(s, j)
            yield obj
        except ValueError:
            i = j + 1


def nested(x):
    """Ops are often JSON-encoded inside JSON strings; parse those too."""
    if isinstance(x, str) and x[:1] in "{[":
        try:
            return json.loads(x)
        except ValueError:
            return x
    return x


def seg_text(seg):
    if isinstance(seg, str):
        return seg, None
    if "text" in seg:
        return seg["text"], ((seg.get("props") or {}).get("attribution") or {}).get("name")
    return "\n", None  # marker = paragraph boundary


class Doc:
    """One merge-tree string: chars plus the author of each char."""

    def __init__(self):
        self.chars, self.who = [], []

    def apply(self, op):
        t = op.get("type")
        if t == 0 and "seg" in op:
            txt, who = seg_text(op["seg"])
            p = op["pos1"]
            self.chars[p:p] = list(txt)
            self.who[p:p] = [who] * len(txt)
        elif t == 1:
            del self.chars[op["pos1"]:op["pos2"]]
            del self.who[op["pos1"]:op["pos2"]]

    def lines(self):
        text = "".join(self.chars)
        out, run, cur = [], [], None
        for ch, w in zip(text, self.who):
            if w != cur and run:
                out.append((cur, "".join(run)))
                run = []
            cur = w
            run.append(ch)
        if run:
            out.append((cur, "".join(run)))
        return out


def parse(data):
    snapshot, msgs = [], {}

    def collect(x):
        x = nested(x)
        if isinstance(x, dict):
            if "segmentTexts" in x:
                for seg in x["segmentTexts"]:
                    txt, who = seg_text(seg)
                    if txt.strip() and (who, txt) not in snapshot:
                        snapshot.append((who, txt))
            if "sequenceNumber" in x and "contents" in x and "clientId" in x:
                msgs.setdefault(x["sequenceNumber"], x)  # the file holds every op twice
            for v in x.values():
                collect(v)
        elif isinstance(x, list):
            for v in x:
                collect(v)

    for s in blobs(data):
        for m in re.finditer(r'"segmentTexts":', s):  # chunks sit in binary, so parse at the key
            try:
                collect({"segmentTexts": DEC.raw_decode(s, m.end())[0]})
            except ValueError:
                pass
        for obj in objects(s):
            collect(obj)

    docs = {}

    def walk(x, addr):
        x = nested(x)
        if isinstance(x, dict):
            if "address" in x and "contents" in x:
                walk(x["contents"], addr + "/" + str(x["address"]))
            elif "pos1" in x and ("seg" in x or "pos2" in x):
                docs.setdefault(addr, Doc()).apply(x)
            else:
                for v in x.values():
                    walk(v, addr)
        elif isinstance(x, list):
            for v in x:
                walk(v, addr)

    # ponytail: plain positional replay. Positions drift where a human and
    # Facilitator edit the same paragraph concurrently (merge-tree refSeq/MSN
    # semantics are not modelled), so the snapshot section is the reconciled
    # view and the replay section is the delta. Upgrade path: full merge-tree.
    for sn in sorted(msgs):
        walk(msgs[sn], "")
    return snapshot, docs, (min(msgs), max(msgs)) if msgs else None


def render(snapshot, docs, span):
    out = ["## snapshot (reconciled state)"]
    out += [f"[{who}] {t}" for who, t in snapshot]
    out.append(f"\n## replay of ops {span[0]}..{span[1]}" if span else "\n## replay (no ops)")
    for addr, doc in docs.items():
        lines = [(w, t) for w, t in doc.lines() if t.strip()]
        if lines:
            out.append(f"### {addr}")
            out += [f"[{w}] {t.strip()}" for w, t in lines]
    return "\n".join(out)


def demo():
    def msg(seq, op):
        inner = {"address": "E", "contents": {"content": {"address": "text", "contents": op}, "type": "op"}}
        return {"clientId": "c", "sequenceNumber": seq, "timestamp": 0,
                "contents": json.dumps({"type": "component", "contents": inner})}
    ai = {"attribution": {"name": "AI-generated"}}
    ops = [msg(1, {"type": 0, "pos1": 0, "seg": {"text": "Hello wrold", "props": ai}}),
           msg(2, {"type": 1, "pos1": 6, "pos2": 11}),
           msg(3, {"type": 0, "pos1": 6, "seg": {"text": "world", "props": {"attribution": {"name": "Hansen, Sarah"}}}})]
    snap = {"segmentTexts": ["Agenda", {"marker": {"refType": 1}}]}
    body = json.dumps(snap).encode() + b"\x00junk\x00" + json.dumps(ops).encode()
    data = b"\x57\x8f\x1c\xd0Prague" + gzip.compress(body) + b"\x00" + gzip.compress(json.dumps(ops).encode())
    snapshot, docs, span = parse(data)
    assert snapshot == [(None, "Agenda")], snapshot
    assert span == (1, 3), span
    assert docs["/E/text"].lines() == [("AI-generated", "Hello "), ("Hansen, Sarah", "world")], docs["/E/text"].lines()
    print("demo OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("subject", nargs="?")
    ap.add_argument("date", nargs="?", help="YYYY-MM-DD, as in the Loop file name")
    ap.add_argument("--profile", help="owa-piggy profile that attended the meeting")
    ap.add_argument("--file", help="read a downloaded .loop file instead")
    ap.add_argument("--demo", action="store_true", help="self-check, no Teams needed")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if a.file:
        data = open(a.file, "rb").read()
    elif a.profile and a.subject and a.date:
        data = fetch(a.profile, a.subject, a.date)
    else:
        ap.error("need --file, or --profile SUBJECT DATE")
    print(render(*parse(data)))


if __name__ == "__main__":
    main()
