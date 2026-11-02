"""Caption files: read SRT or VTT, find the dead air and fillers, re-chunk for vertical video.

Works on the transcript you already have (CapCut, Descript, YouTube Studio and most
editors export SRT). Output is a cut list you apply in your editor and a caption file
you can import back.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .util import ToolError, ffmpeg_ts, fmt_ts, words

TS = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")
TS_SHORT = re.compile(r"(\d{1,2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2})[,.](\d{1,3})")

DEFAULT_FILLERS = [
    "um", "umm", "uh", "uhh", "hmm", "er", "ah", "you know", "i mean", "kind of", "sort of",
    "basically", "literally", "actually", "like", "right", "so yeah", "okay so", "matlab",
]


def _sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse(text: str) -> List[Dict[str, Any]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    cues: List[Dict[str, Any]] = []
    for block in re.split(r"\n{2,}", text.strip()):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        for i, ln in enumerate(lines):
            m = TS.search(ln)
            if m:
                start = _sec(*m.groups()[0:4])
                end = _sec(*m.groups()[4:8])
            else:
                m2 = TS_SHORT.search(ln)
                if not m2:
                    continue
                g = m2.groups()
                start, end = _sec("0", g[0], g[1], g[2]), _sec("0", g[3], g[4], g[5])
            body = " ".join(lines[i + 1:])
            body = re.sub(r"<[^>]+>", "", body).strip()
            if body:
                cues.append({"start": start, "end": end, "text": body})
            break
    if not cues:
        raise ToolError("No cues found. Expected SRT or VTT with 00:00:01,000 --> 00:00:03,000 style timings.")
    cues.sort(key=lambda c: c["start"])
    return cues


def to_srt(cues: List[Dict[str, Any]]) -> str:
    def ts(sec: float) -> str:
        ms = int(round(sec * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return "%02d:%02d:%02d,%03d" % (h, m, s, ms)

    out = []
    for i, c in enumerate(cues, 1):
        out.append("%d\n%s --> %s\n%s\n" % (i, ts(c["start"]), ts(c["end"]), c["text"]))
    return "\n".join(out)


def analyze(text: str, pause: float = 0.7, fillers: Optional[List[str]] = None) -> Dict[str, Any]:
    cues = parse(text)
    fl = [f.lower() for f in (fillers or DEFAULT_FILLERS)]
    spoken = sum(max(0.0, c["end"] - c["start"]) for c in cues)
    wc = sum(len(words(c["text"])) for c in cues)
    wpm = wc / (spoken / 60.0) if spoken > 0 else 0.0

    gaps = []
    for a, b in zip(cues, cues[1:]):
        g = b["start"] - a["end"]
        if g >= pause:
            gaps.append({"at": a["end"], "length": g})

    filler_hits: List[Dict[str, Any]] = []
    cuts: List[Dict[str, Any]] = []
    only_filler = re.compile(r"^(" + "|".join(re.escape(f) for f in fl) + r")[\s,.!?]*$", re.I)
    inline = re.compile(r"(?<![\w'])(" + "|".join(re.escape(f) for f in sorted(fl, key=len, reverse=True)) + r")(?![\w'])", re.I)
    for c in cues:
        if only_filler.match(c["text"].strip()):
            cuts.append({"start": c["start"], "end": c["end"], "action": "cut", "reason": "filler only: '%s'" % c["text"].strip()})
            continue
        found = [m.group(1).lower() for m in inline.finditer(c["text"]) if m.group(1).lower() not in ("like", "right", "actually", "literally", "basically", "kind of", "sort of")]
        if found:
            filler_hits.append({"at": c["start"], "fillers": found, "text": c["text"]})
    for g in gaps:
        if g["length"] >= max(pause, 0.9):
            cuts.append({"start": g["at"] + 0.25, "end": g["at"] + g["length"] - 0.1, "action": "tighten", "reason": "%.1fs of dead air" % g["length"]})
    cuts.sort(key=lambda c: c["start"])

    saved = sum(c["end"] - c["start"] for c in cuts)
    total = cues[-1]["end"] - cues[0]["start"]
    notes = []
    if wpm and wpm < 120:
        notes.append("Pace is %.0f wpm. That is slow for short-form. Tighten pauses or speed the clip 5 to 10 percent." % wpm)
    elif wpm > 190:
        notes.append("Pace is %.0f wpm. Fast enough that captions may be hard to read." % wpm)
    if filler_hits:
        notes.append("%d lines have filler words inside them. Word-level timing is not in an SRT, so they are listed for you to trim by ear." % len(filler_hits))
    return {
        "cues": len(cues), "duration": round(total, 1), "words": wc, "wpm": round(wpm),
        "gaps": [{"at": round(g["at"], 2), "length": round(g["length"], 2)} for g in gaps],
        "filler_lines": filler_hits, "cuts": [{**c, "start": round(c["start"], 2), "end": round(c["end"], 2)} for c in cuts],
        "time_saved": round(saved, 1), "notes": notes,
    }


def _word_stream(cues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every word with an interpolated start and end. Time is shared out inside each cue by character count."""
    stream: List[Dict[str, Any]] = []
    for c in cues:
        ws = c["text"].split()
        if not ws:
            continue
        total = float(sum(len(w) + 1 for w in ws))
        span = max(c["end"] - c["start"], 0.01)
        acc = 0.0
        for w in ws:
            a = c["start"] + span * acc / total
            acc += len(w) + 1
            b = c["start"] + span * acc / total
            stream.append({"w": w, "s": a, "e": b})
    return stream


def _split_even(words_: List[Dict[str, Any]], wpc: int, max_chars: int) -> List[List[Dict[str, Any]]]:
    """Cut one run of words into near-equal chunks, nudging each cut onto a comma when one is next to it."""
    n = len(words_)
    chars = sum(len(x["w"]) + 1 for x in words_)
    k = max(1, -(-n // wpc), -(-chars // (max_chars + 1)))
    while True:
        base, extra = divmod(n, k)
        sizes = [base + (1 if i < extra else 0) for i in range(k)]
        cuts, acc = [], 0
        for sz in sizes[:-1]:
            acc += sz
            cuts.append(acc)
        for ci, cut in enumerate(cuts):
            lo = (cuts[ci - 1] if ci else 0) + 1
            hi = (cuts[ci + 1] if ci + 1 < len(cuts) else n) - 1
            for cand in (cut, cut + 1, cut - 1):
                if lo <= cand <= hi and words_[cand - 1]["w"].endswith((",", ";", ":")):
                    cuts[ci] = cand
                    break
        bounds = [0] + cuts + [n]
        chunks = [words_[bounds[i]:bounds[i + 1]] for i in range(k)]
        if all(len(" ".join(x["w"] for x in ch)) <= max_chars or len(ch) == 1 for ch in chunks) or k >= n:
            return [ch for ch in chunks if ch]
        k += 1


def rechunk(text: str, words_per_chunk: int = 4, max_chars: int = 28, min_dur: float = 0.35) -> str:
    """Vertical-video captions: short, one line, balanced, and free to run across the original cue edges."""
    stream = _word_stream(parse(text))
    runs: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    for i, wd in enumerate(stream):
        if cur and (re.search(r"[.!?][\"')\]]*$", cur[-1]["w"]) or wd["s"] - cur[-1]["e"] > 0.7):
            runs.append(cur)
            cur = []
        cur.append(wd)
    if cur:
        runs.append(cur)
    chunks: List[List[Dict[str, Any]]] = []
    for r in runs:
        chunks.extend(_split_even(r, max(1, words_per_chunk), max(8, max_chars)))
    out: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        a, b = ch[0]["s"], ch[-1]["e"]
        nxt = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else None
        if b - a < min_dur:
            b = a + min_dur
        if nxt is not None and b > nxt:
            b = max(a + 0.05, nxt)
        out.append({"start": a, "end": b, "text": " ".join(x["w"] for x in ch)})
    return to_srt(out)


def render(res: Dict[str, Any]) -> str:
    out = ["SUBTITLE REPORT  |  %d cues  |  %s  |  %d words  |  %d wpm" % (res["cues"], fmt_ts(res["duration"]), res["words"], res["wpm"]), "=" * 74]
    if res["cuts"]:
        out.append("CUT LIST (apply in your editor, ~%.1fs saved)" % res["time_saved"])
        for c in res["cuts"][:25]:
            out.append("  %8s - %-8s %-8s %s" % (fmt_ts(c["start"]), fmt_ts(c["end"]), c["action"], c["reason"]))
    else:
        out.append("No dead air or filler-only cues found.")
    if res["filler_lines"]:
        out.append("FILLERS INSIDE LINES (trim by ear)")
        for f in res["filler_lines"][:12]:
            out.append("  %8s  %s  <- %s" % (fmt_ts(f["at"]), ", ".join(sorted(set(f["fillers"]))), f["text"][:50]))
    for n in res["notes"]:
        out.append("  - " + n)
    return "\n".join(out)
