"""Script to timed beat sheet, with the retention problems flagged before you shoot.

One sentence (or one line, if it has no sentence end) is one beat. Spoken length is estimated from word count.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .util import concrete_markers, fmt_ts, words

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was", "were",
    "i", "you", "your", "my", "me", "we", "it", "this", "that", "how", "why", "what", "do", "does",
    "did", "at", "as", "by", "from", "be", "can", "will", "not", "no", "so", "but", "if", "then",
    "just", "very", "really", "one",
}
CTA_RX = re.compile(r"\b(follow|subscribe|comment|share|save|link in bio|dm me|click|join)\b", re.I)
TAG_RX = re.compile(r"^\s*\[(hook|cta|body|beat|b-?roll|text)[^\]]*\]\s*", re.I)


def _content(line: str) -> set:
    return {w.lower() for w in words(line) if w.lower() not in STOP and len(w) > 2}


def beat_sheet(script: str, target: Optional[float] = None, wpm: float = 165.0) -> Dict[str, Any]:
    lines = []
    for raw in script.splitlines():
        raw = TAG_RX.sub("", raw).strip()
        if not raw:
            continue
        # a pasted paragraph is many beats: split on sentence ends, keep a line without any as one beat
        lines.extend(x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", raw) if x.strip())
    if not lines:
        raise ValueError("The script is empty.")
    wps = wpm / 60.0
    beats: List[Dict[str, Any]] = []
    t = 0.0
    for i, ln in enumerate(lines):
        n = len(words(ln))
        dur = max(0.8, n / wps)
        beats.append({"i": i + 1, "start": t, "dur": dur, "words": n, "text": ln})
        t += dur
    total = t
    notes: List[str] = []

    hook = beats[0]
    if hook["dur"] > 3.0:
        cut = int(round((hook["dur"] - 3.0) * wps))
        notes.append("Hook runs %.1fs. The window is about 3s. Cut roughly %d words or split it into two beats." % (hook["dur"], cut))
    for b in beats[1:]:
        if b["dur"] > 4.0:
            notes.append("Beat %d runs %.1fs on one line. Split it, or change what is on screen inside it. A static frame is where people leave." % (b["i"], b["dur"]))
        if b["words"] / max(b["dur"], 0.1) > 3.6 and b["words"] > 10:
            notes.append("Beat %d is dense (%d words in %.1fs). Captions will be hard to read." % (b["i"], b["words"], b["dur"]))

    # runs of lines with nothing concrete in them
    run = 0
    for b in beats:
        w, _ = concrete_markers(b["text"])
        has_gap = "?" in b["text"] or bool(re.search(r"\b(but|because|so|instead)\b", b["text"], re.I))
        if w == 0 and not has_gap:
            run += 1
            if run == 3:
                notes.append("Beats %d to %d have no number, name or turn in them. Add a concrete detail or cut them." % (b["i"] - 2, b["i"]))
        else:
            run = 0

    # loop back
    first = _content(lines[0])
    last = _content(lines[-1])
    loops = bool(first & last)
    if len(lines) > 2 and not loops:
        notes.append("No loop: the last line shares nothing with the first. Echo a word from the hook so a second watch is free.")

    # CTA position
    for b in beats:
        if CTA_RX.search(b["text"]) and b["start"] < total * 0.5 and b["i"] != len(beats):
            notes.append("A call to action in beat %d, before the halfway point. Earn it first." % b["i"])
            break

    diff = None
    if target:
        diff = total - target
        if abs(diff) > max(2.0, 0.1 * target):
            words_off = int(round(abs(diff) * wps))
            if diff > 0:
                notes.append("%.1fs over the %.0fs target. Cut about %d words." % (diff, target, words_off))
            else:
                notes.append("%.1fs under the %.0fs target. Add about %d words, or shoot it short. Short is usually right." % (-diff, target, words_off))

    for b in beats:
        b["label"] = "HOOK" if b["i"] == 1 else "CTA" if (b["i"] == len(beats) and CTA_RX.search(b["text"])) else ""
    return {
        "beats": beats, "total_seconds": round(total, 1), "words": sum(b["words"] for b in beats),
        "wpm": wpm, "target": target, "loops": loops, "notes": notes,
    }


def render(res: Dict[str, Any]) -> str:
    out = []
    head = "BEAT SHEET  |  %d words  |  ~%.1fs at %d wpm" % (res["words"], res["total_seconds"], res["wpm"])
    if res["target"]:
        head += "  |  target %.1fs" % res["target"]
    out.append(head)
    out.append("=" * 76)
    for b in res["beats"]:
        txt = b["text"] if len(b["text"]) <= 52 else b["text"][:49] + "..."
        out.append("  %7s %5.1fs  %-4s  %s" % (fmt_ts(b["start"]), b["dur"], b["label"], txt))
    out.append("-" * 76)
    if res["notes"]:
        for n in res["notes"]:
            out.append("  - " + n)
    else:
        out.append("  No structural problems found.")
    if res["loops"]:
        out.append("  Loops: the last line echoes the hook. Second watches are free reach.")
    return "\n".join(out)
