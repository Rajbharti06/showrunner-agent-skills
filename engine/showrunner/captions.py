"""Caption and post-copy linter with the truncation preview.

The part of a caption that people see before the "more" tap does most of the work.
Limits are conservative and come with a status; see `showrunner facts` for provenance.
"""
from __future__ import annotations

import re
import textwrap
from typing import Any, Dict, List, Optional

from .util import concrete_markers, words
from . import humanize

# chars: hard limit. preview: approximate characters shown before the fold (inferred).
# hashtags: cap or advised ceiling. status: official | reported | inferred
LIMITS: Dict[str, Dict[str, Any]] = {
    "instagram": {"chars": 2200, "preview": 125, "hashtags": 5, "hashtag_kind": "cap", "links": "not clickable in captions", "status": "reported"},
    "tiktok": {"chars": 2200, "preview": 100, "hashtags": 5, "hashtag_kind": "advised", "links": "not clickable in captions", "status": "inferred"},
    "youtube": {"chars": 5000, "preview": 150, "hashtags": 15, "hashtag_kind": "cap", "links": "clickable", "status": "official"},
    "facebook": {"chars": 63206, "preview": 125, "hashtags": 3, "hashtag_kind": "advised", "links": "clickable, can limit reach", "status": "inferred"},
    "linkedin": {"chars": 3000, "preview": 210, "hashtags": 3, "hashtag_kind": "advised", "links": "put in first comment or keep out of the opening", "status": "inferred"},
    "x": {"chars": 280, "preview": 280, "hashtags": 2, "hashtag_kind": "advised", "links": "clickable", "status": "official"},
    "threads": {"chars": 500, "preview": 200, "hashtags": 1, "hashtag_kind": "advised", "links": "clickable", "status": "official"},
}

ASK_RX = {
    "follow": r"\bfollow\b", "subscribe": r"\bsubscribe\b", "comment": r"\bcomment\b",
    "share": r"\bshare\b", "save": r"\bsave\b", "link": r"\blink in (my )?bio\b|\bclick\b",
    "dm": r"\bdm\b|\bmessage me\b", "like": r"\blike (this|the)\b|\bsmash\b",
}


def preview_box(text: str, width: int, label: str = "WHAT THE FEED SHOWS") -> str:
    shown = text[:width]
    wrapped = textwrap.wrap(shown.replace("\n", " / "), 52, drop_whitespace=False, break_long_words=True) or [""]
    box = ["  " + label, "  +" + "-" * 54 + "+"]
    for ln in wrapped:
        box.append("  | " + ln.ljust(52) + " |")
    cut = " ... more " if len(text) > width else ""
    box.append("  +" + "-" * (54 - len(cut)) + cut + "+")
    return "\n".join(box)


def lint(text: str, platform: str = "instagram", keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    if platform not in LIMITS:
        raise ValueError("Unknown platform '%s'. Choose from: %s" % (platform, ", ".join(sorted(LIMITS))))
    lim = LIMITS[platform]
    body = text.strip()
    checks: List[Dict[str, str]] = []

    def add(level: str, name: str, msg: str) -> None:
        checks.append({"level": level, "name": name, "msg": msg})

    n = len(body)
    if n > lim["chars"]:
        add("FAIL", "LENGTH", "%d / %d characters. Over the limit." % (n, lim["chars"]))
    else:
        add("PASS", "LENGTH", "%d / %d characters" % (n, lim["chars"]))

    first = re.split(r"(?<=[.!?])\s|\n", body, maxsplit=1)[0] if body else ""
    if len(first) > lim["preview"]:
        add("WARN", "FIRST LINE", "%d characters, so it gets cut at about %d mid-thought." % (len(first), lim["preview"]))
    else:
        add("PASS", "FIRST LINE", "%d characters, lands inside the preview" % len(first))

    window = body[: lim["preview"]]
    w, found = concrete_markers(window)
    if w >= 1.0:
        add("PASS", "HOOK IS CONCRETE", "%d number or name in the visible window" % len(found))
    else:
        add("WARN", "HOOK IS CONCRETE", "Nothing concrete in the first %d characters. Lead with a number, a name or a place." % lim["preview"])

    tags = re.findall(r"(?<!\w)#\w+", body)
    cap = lim["hashtags"]
    if len(tags) > cap:
        kind = "the platform cap" if lim["hashtag_kind"] == "cap" else "a sensible ceiling"
        add("FAIL" if lim["hashtag_kind"] == "cap" else "WARN", "HASHTAGS", "%d tags, over %s of %d." % (len(tags), kind, cap))
    else:
        add("PASS", "HASHTAGS", "%d tag%s (%s %d)" % (len(tags), "" if len(tags) == 1 else "s", lim["hashtag_kind"], cap))

    asks = [k for k, rx in ASK_RX.items() if re.search(rx, body, re.I)]
    if len(asks) > 2:
        add("WARN", "ONE ASK", "%d different asks (%s). People do one thing. Pick it." % (len(asks), ", ".join(asks)))
    elif asks:
        add("PASS", "ONE ASK", "call to action: " + ", ".join(asks))
    else:
        add("INFO", "ONE ASK", "No call to action. Fine if the post earns the next step on its own.")

    if keywords:
        low = body.lower()
        missing = [k for k in keywords if k.lower() not in low]
        in_window = [k for k in keywords if k.lower() in window.lower()]
        if missing:
            add("WARN", "SEARCH TERMS", "%d/%d present. Missing: %s" % (len(keywords) - len(missing), len(keywords), ", ".join(missing)))
        elif not in_window:
            add("WARN", "SEARCH TERMS", "All present, but none in the visible window.")
        else:
            add("PASS", "SEARCH TERMS", "%d/%d present, %d in the visible window" % (len(keywords), len(keywords), len(in_window)))

    names = {"instagram": "an Instagram", "tiktok": "a TikTok", "facebook": "a Facebook", "youtube": "a YouTube",
             "linkedin": "a LinkedIn", "threads": "a Threads", "x": "an X"}
    if re.search(r"https?://", body) and platform in ("instagram", "tiktok"):
        add("WARN", "LINKS", "A URL in %s caption is not clickable. Use the bio link." % names.get(platform, "this"))
    elif re.search(r"https?://", body) and platform == "linkedin" and re.search(r"https?://", window):
        add("WARN", "LINKS", "A link in the opening of a LinkedIn post. Common advice is to put it in the first comment. That is not verified here, so treat it as something to test.")

    if n > 400 and "\n" not in body:
        add("WARN", "READABILITY", "A wall of text. Add line breaks.")

    slop = humanize.slop_hits(body)
    if slop:
        add("WARN", "STOCK PHRASES", "%d found (%s). Run the humanizer." % (len(slop), ", ".join(sorted(set(slop))[:4])))

    fails = sum(1 for c in checks if c["level"] == "FAIL")
    warns = sum(1 for c in checks if c["level"] == "WARN")
    return {
        "platform": platform, "chars": n, "limit_status": lim["status"], "checks": checks,
        "fails": fails, "warns": warns, "preview": preview_box(body, lim["preview"]),
    }
