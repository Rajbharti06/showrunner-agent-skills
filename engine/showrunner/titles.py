"""YouTube-style title scoring and title + thumbnail pairing.

Heuristic, like the hook scorer. It catches weak packaging; it cannot tell you
which of two decent packages will win. For that, use YouTube's own Test & Compare
(see `showrunner facts --platform youtube`) and trust the result over this score.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .util import band, clip, concrete_markers, words

CLICKBAIT = [
    r"you won'?t believe", r"shocking", r"gone wrong", r"\(not clickbait\)", r"100% real",
    r"what happens next", r"will blow your mind", r"doctors hate", r"this one trick",
    r"insane", r"unbelievable",
]
VAGUE = {"stuff", "things", "thing", "amazing", "awesome", "great", "best", "cool", "nice", "some", "this", "video"}
GAP_RX = [
    r"\?", r"\bhow\b", r"\bwhy\b", r"\bwhat\b", r"\bnobody\b", r"\bnever\b", r"\bactually\b",
    r"\bvs\.?\b", r"\bversus\b", r"\bi\s+(tried|tested|built|quit|lost|spent|made)\b", r"\btruth\b",
    r"\bmistake", r"\bwithout\b", r"\binstead\b", r"\bthe\s+(real|hidden|only)\b",
]
STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was", "were",
    "i", "you", "your", "my", "me", "we", "it", "this", "that", "how", "why", "what", "do", "does",
    "did", "at", "as", "by", "from", "be", "can", "will", "not", "no", "so", "but", "if",
}

TITLE_MAX = 100          # YouTube hard cap (see facts: youtube.title.max_chars)
IDEAL_LO, IDEAL_HI = 35, 65


def _content_words(text: str) -> List[str]:
    return [w.lower() for w in words(text) if w.lower() not in STOP and len(w) > 1]


def score_title(title: str, keyword: Optional[str] = None) -> Dict[str, Any]:
    t = " ".join(title.split())
    n = len(t)
    low = t.lower()
    comps: Dict[str, float] = {}
    notes: List[str] = []
    flags: List[str] = []

    # LENGTH
    if n > TITLE_MAX:
        comps["length"] = 0.0
        flags.append("Over %d characters. YouTube will not accept it." % TITLE_MAX)
    elif IDEAL_LO <= n <= IDEAL_HI:
        comps["length"] = 100.0
    elif n < IDEAL_LO:
        comps["length"] = clip(50.0 + (n / IDEAL_LO) * 50.0)
        notes.append("Short (%d chars). Room to add the specific detail." % n)
    else:
        comps["length"] = clip(100.0 - (n - IDEAL_HI) * 1.6)
        notes.append("Long (%d chars). Past about %d it is likely to be cut off in many views." % (n, IDEAL_HI))

    # KEYWORD
    if keyword:
        kw = keyword.lower().strip()
        pos = low.find(kw)
        if pos < 0:
            comps["keyword"] = 0.0
            flags.append("Target keyword '%s' is missing." % keyword)
        elif pos <= 40:
            comps["keyword"] = 100.0
        else:
            comps["keyword"] = 65.0
            notes.append("Keyword sits late in the title. Move it into the first 40 characters.")

    # SPECIFICITY
    weight, _ = concrete_markers(t)
    comps["specificity"] = clip(60.0 * weight)

    # CURIOSITY GAP
    hits = sum(1 for rx in GAP_RX if re.search(rx, low))
    comps["curiosity"] = clip(45.0 * hits)

    # CLARITY (penalties)
    clarity = 100.0
    toks = [w.lower() for w in words(t)]
    vague = [w for w in toks if w in VAGUE]
    if vague:
        clarity -= 12 * len(set(vague))
        notes.append("Vague words: %s." % ", ".join(sorted(set(vague))))
    caps = [w for w in words(t) if len(w) > 3 and w.isupper()]
    if len(caps) > 1:
        clarity -= 15
        flags.append("Several ALL CAPS words. One is emphasis, several is shouting.")
    if re.search(r"[!?]{2,}", t):
        clarity -= 15
        flags.append("Stacked punctuation.")
    emoji = re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", t)
    if len(emoji) > 1:
        clarity -= 10
        notes.append("More than one emoji.")
    comps["clarity"] = clip(clarity)

    # CLICKBAIT RISK (flag only, plus a penalty)
    bait = [rx for rx in CLICKBAIT if re.search(rx, low)]
    risk = ""
    if bait:
        risk = "Promise-risk phrase. If the video does not deliver, retention and trust both pay."
        comps["clarity"] = clip(comps["clarity"] - 20)

    weights = {"length": 0.15, "keyword": 0.20, "specificity": 0.25, "curiosity": 0.25, "clarity": 0.15}
    use = {k: weights[k] for k in comps}
    tot = sum(use.values())
    total = sum(comps[k] * use[k] for k in comps) / tot
    hard = sum(1 for f in flags if not f.startswith("Target keyword")) + (1 if risk else 0)
    total = clip(total - 8.0 * hard)
    return {
        "title": t, "chars": n, "score": round(total, 1), "band": band(total),
        "components": {k: round(v, 1) for k, v in comps.items()},
        "notes": notes, "flags": flags, "risk": risk,
    }


def pair_check(title: str, thumb_text: str) -> Dict[str, Any]:
    """A thumbnail and a title are one message in two places. They should not repeat each other."""
    tw = set(_content_words(title))
    hw = set(_content_words(thumb_text))
    thumb_words = len(words(thumb_text))
    overlap = (len(tw & hw) / len(hw)) if hw else 0.0
    score = 100.0 - overlap * 70.0 - max(0, thumb_words - 4) * 9.0
    notes: List[str] = []
    if overlap >= 0.5:
        notes.append("The thumbnail text repeats the title. Spend those words on a different angle (emotion, contrast, the stakes).")
    if thumb_words > 6:
        notes.append("%d words on the thumbnail. Past about 4 it stops being read on a phone." % thumb_words)
    if thumb_words == 0:
        notes.append("No thumbnail text. That is fine if the image carries it. Check it works at phone size.")
        score = 80.0
    if not notes:
        notes.append("Good split: the title carries the topic, the thumbnail carries a different hook.")
    return {
        "title": title, "thumbnail_text": thumb_text, "overlap": round(overlap, 2),
        "thumbnail_words": thumb_words, "score": round(clip(score), 1), "notes": notes,
    }


def test_plan(titles: List[str]) -> List[str]:
    """What to change between variants so a test teaches you something."""
    return [
        "Change ONE variable per test (title wording, or thumbnail focal point, not both).",
        "Variants to test: %s" % " | ".join(titles[:3]),
        "Let it run until YouTube declares a winner or you have a full week of impressions. Do not call it early.",
        "Log the result with `showrunner exp log` so the lesson survives past this video.",
    ]
