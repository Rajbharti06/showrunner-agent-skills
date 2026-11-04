"""Hook scoring and formula matching.

A hook is the first sentence a viewer or reader meets. This scores it on six
properties and flags the patterns that reliably lose people.

IMPORTANT: this is a heuristic. It is good at catching weak hooks and has NOT
been validated as a predictor of views. Run `showrunner calibrate` on your own posts
to see which of the six checks actually separate your winners from your misses.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from . import store
from .util import band, clip, concrete_markers, load_data, words

_HOOKS = None

SECOND_PERSON = {
    "you", "your", "you're", "youre", "you'll", "you've", "you'd", "yours", "yourself", "u", "ur",
    "aap", "aapko", "aapka", "aapke", "tum", "tumhe", "tumhara", "tumhare", "tera", "tere", "tujhe",
}
FIRST_PERSON = {"i", "i'm", "i've", "i'll", "i'd", "my", "me", "we", "our", "mine", "myself", "mera", "meri", "main", "maine"}
AUDIENCE = {
    "students", "student", "founders", "founder", "creators", "creator", "beginners", "beginner",
    "developers", "developer", "freelancers", "freelancer", "parents", "teachers", "engineers",
    "designers", "marketers", "entrepreneurs", "coders", "applicants", "applicant", "gamers",
    "managers", "nurses", "traders", "investors", "aspirants", "interns", "graduates", "juniors",
    "hackers", "analysts", "writers", "musicians", "athletes", "newbies",
}
STAKES = {
    "lost", "lose", "losing", "wasted", "waste", "cost", "costs", "costly", "mistake", "mistakes",
    "wrong", "never", "stop", "avoid", "warning", "risk", "risky", "danger", "dangerous", "fail",
    "failed", "failing", "failure", "broke", "broken", "free", "fastest", "easiest", "without",
    "regret", "ruin", "ruined", "kill", "killing", "quit", "rejected", "rejection", "scam", "trap",
    "afraid", "cheap", "expensive", "flop", "flopped", "ignored", "deadline", "penalty", "banned",
}
FILLER_OPEN = {
    "so", "um", "uh", "umm", "okay", "ok", "well", "hey", "hi", "hello", "yo", "guys", "everyone",
    "today", "welcome", "alright", "right", "like", "basically", "actually", "ah", "oh", "namaste",
}
CURIOSITY_RX = [
    r"\?", r"\bwhy\b", r"\bhow\b", r"\bwhat\s+(happens|if|nobody|no one)\b", r"\bhere'?s\b",
    r"\bthe\s+(reason|truth|catch|trick|part)\b", r"\b(nobody|no\s?one)\b", r"\bactually\b",
    r"\bbut\b", r"\buntil\b", r"\bexcept\b", r"\binstead\b", r"\bturns\s+out\b", r"\bsecret\b",
    r"\bnever\b", r"\bonly\b", r"\bthis\s+(one|is why)\b", r"\bwhat\s+i\s+(found|learned|noticed)\b",
]

COMPONENTS = ("specificity", "frontload", "address", "curiosity", "stakes", "brevity")


def _data() -> Dict[str, Any]:
    global _HOOKS
    if _HOOKS is None:
        _HOOKS = load_data("hooks.json")
        for f in _HOOKS["formulas"]:
            f["_rx"] = [re.compile(r, re.I) for r in f["rx"]]
        for key in ("dealbreakers", "warnings"):
            for d in _HOOKS[key]:
                d["_rx"] = re.compile(d["rx"], re.I)
        # optional "lexicon" in hooks.json (usually from a data pack) adds words to the lists below
        lex = _HOOKS.get("lexicon", {})
        more = lambda key: {w.lower() for w in lex.get(key, [])}  # noqa: E731
        _HOOKS["_lex"] = {
            "second": SECOND_PERSON | more("second_person"), "first": FIRST_PERSON | more("first_person"),
            "audience": AUDIENCE | more("audience"), "stakes": STAKES | more("stakes"),
            "filler": FILLER_OPEN | more("filler_open"), "curiosity": CURIOSITY_RX + list(lex.get("curiosity_rx", [])),
        }
    return _HOOKS


def norm(text: str) -> str:
    return (text.replace("’", "'").replace("‘", "'").replace("“", '"')
            .replace("”", '"').strip())


def load_weights() -> Dict[str, float]:
    """User-calibrated weights win; otherwise the shipped defaults."""
    user = store.read_json(store.weights_path(), None)
    base = load_data("weights.json")
    src = user if isinstance(user, dict) and all(k in user for k in COMPONENTS) else base
    w = {k: float(src[k]) for k in COMPONENTS}
    total = sum(w.values()) or 1.0
    out = {k: v / total for k, v in w.items()}
    out["_source"] = "calibrated" if src is user else "default"  # type: ignore[assignment]
    return out


def formulas(platform: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for f in _data()["formulas"]:
        if platform and platform not in f["platforms"]:
            continue
        out.append({k: v for k, v in f.items() if not k.startswith("_")})
    return out


def classify(text: str) -> List[Dict[str, str]]:
    t = norm(text)
    hits = []
    for f in _data()["formulas"]:
        if any(rx.search(t) for rx in f["_rx"]):
            hits.append({"id": f["id"], "name": f["name"]})
    return hits


def _spoken_words(text: str) -> List[str]:
    return [w.lower() for w in words(text)]


def _component_scores(text: str, platform: str) -> Dict[str, float]:
    t = norm(text)
    toks = _spoken_words(t)
    low = " ".join(toks)
    lx = _data()["_lex"]

    # SPECIFICITY: real numbers, names, acronyms
    weight, _ = concrete_markers(t)
    spec = clip(60.0 * weight)

    # FRONTLOAD: how many throat-clearing words before the claim
    lead = 0
    for tok in toks[:5]:
        if tok in lx["filler"]:
            lead += 1
        else:
            break
    front = clip(100.0 - 30.0 * lead)

    # ADDRESS: who is this for
    tokset = set(toks)
    if tokset & lx["second"]:
        addr = 100.0
    elif tokset & lx["audience"]:
        addr = 85.0
    elif tokset & lx["first"]:
        addr = 55.0
    else:
        addr = 20.0

    # CURIOSITY: an open loop the viewer wants closed
    hits = sum(1 for rx in lx["curiosity"] if re.search(rx, low if rx != r"\?" else t))
    cur = clip(50.0 * hits)

    # STAKES: something is lost, saved, risked
    stake_hits = len({tok for tok in toks if tok in lx["stakes"]})
    stake_hits += len(re.findall(r"[$€£₹]", t))
    sk = clip(45.0 * stake_hits)

    # BREVITY: about three seconds of speech for short-form
    n = len(toks)
    if platform == "text":
        chars = len(t)
        brev = 100.0 if chars <= 90 else 80.0 if chars <= 125 else 50.0 if chars <= 210 else 20.0
    elif platform == "long":
        brev = 100.0 if n <= 20 else 75.0 if n <= 30 else 45.0 if n <= 40 else 15.0
    else:
        brev = 100.0 if n <= 12 else 75.0 if n <= 16 else 45.0 if n <= 22 else 15.0

    return {
        "specificity": spec, "frontload": front, "address": addr,
        "curiosity": cur, "stakes": sk, "brevity": brev,
    }


HINTS = {
    "specificity": "Name a real number, place or person from your own story. 'Four months' beats 'a while'.",
    "frontload": "Cut the throat-clearing. Open on the claim itself.",
    "address": "Talk to someone. Use 'you', or name who it is for ('if you are applying to...').",
    "curiosity": "Hold something back. End the line on the unresolved part, not the answer.",
    "stakes": "Say what it cost, what it saves, or what goes wrong if they skip it.",
    "brevity": "Trim it. A short-form hook has about three seconds, roughly 10 to 12 spoken words.",
}


def score_hook(text: str, platform: str = "short", weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    data = _data()
    t = norm(text)
    if not t:
        raise ValueError("empty hook")
    comps = _component_scores(t, platform)
    w = weights or load_weights()
    total = sum(comps[k] * w[k] for k in COMPONENTS)

    dealbreakers = [d["message"] for d in data["dealbreakers"] if d["_rx"].search(t)]
    warnings = [d["message"] for d in data["warnings"] if d["_rx"].search(t)]
    letters = [c for c in t if c.isalpha()]
    if len(letters) > 12 and sum(1 for c in letters if c.isupper()) / len(letters) > 0.6:
        dealbreakers.append("Shouting. All caps reads as an ad.")
    if dealbreakers:
        total = min(total, 35.0)
    total -= 6.0 * len(warnings)
    total = clip(total)

    wmax = max(w[k] for k in COMPONENTS)
    weakest = min(COMPONENTS, key=lambda k: comps[k] * (w[k] / wmax))
    return {
        "hook": t,
        "score": round(total, 1),
        "band": band(total),
        "components": {k: round(v, 1) for k, v in comps.items()},
        "weakest": weakest,
        "hint": HINTS[weakest],
        "dealbreakers": dealbreakers,
        "warnings": warnings,
        "formulas": classify(t),
        "words": len(_spoken_words(t)),
        "weights": w.get("_source", "default"),
    }


def rank_hooks(lines: List[str], platform: str = "short") -> List[Dict[str, Any]]:
    w = load_weights()
    scored = [score_hook(ln, platform, w) for ln in lines if ln.strip()]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored
