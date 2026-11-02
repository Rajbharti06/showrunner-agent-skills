"""Idea scoring, de-duplication, and a pillar-by-angle matrix to seed brainstorming."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from . import hooks
from .util import ToolError, words

STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "how", "why", "what", "my", "your", "i", "you", "we", "it", "this", "that", "do", "does"}
ANGLES = [
    "the mistake most people make", "the myth to retire", "the story behind it", "the teardown of something that worked",
    "the checklist", "the comparison", "the beginner trap", "the behind-the-scenes", "the result and how it happened",
    "the prediction and what to do now", "the question your audience keeps asking", "the unpopular opinion",
]
WEIGHTS = {"pain": 0.30, "proof": 0.25, "novelty": 0.15, "fit": 0.15, "ease": 0.15}


def _tokens(s: str) -> set:
    return {w.lower() for w in words(s) if w.lower() not in STOP and len(w) > 2}


def parse(text: str) -> List[Dict[str, Any]]:
    """Each line: idea | pain | proof | novelty | fit | effort   (ratings 1 to 5, all optional)."""
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = [p.strip() for p in re.split(r"\||\t", ln)]
        idea = parts[0]
        nums = []
        for p in parts[1:6]:
            try:
                v = float(p)
            except ValueError:
                raise ToolError("Ratings must be numbers from 1 to 5. Problem line: %s" % ln[:60])
            if not 1 <= v <= 5:
                raise ToolError("Ratings must be between 1 and 5. Problem line: %s" % ln[:60])
            nums.append(v)
        rated = len(nums) == 5
        pain, proof, novelty, fit, effort = nums if rated else (3, 3, 3, 3, 3)
        out.append({"idea": idea, "pain": pain, "proof": proof, "novelty": novelty, "fit": fit, "effort": effort, "rated": rated})
    if not out:
        raise ToolError("No ideas found. One idea per line.")
    return out


def score(text: str) -> Dict[str, Any]:
    items = parse(text)
    for it in items:
        ease = 6 - it["effort"]
        raw = WEIGHTS["pain"] * it["pain"] + WEIGHTS["proof"] * it["proof"] + WEIGHTS["novelty"] * it["novelty"] + WEIGHTS["fit"] * it["fit"] + WEIGHTS["ease"] * ease
        it["score"] = round((raw - 1) / 4 * 100, 1)
        it["hook_potential"] = hooks.score_hook(it["idea"], "short")["score"]
    items.sort(key=lambda i: (i["score"], i["hook_potential"]), reverse=True)
    dups = duplicates([i["idea"] for i in items])
    unrated = sum(1 for i in items if not i["rated"])
    notes = []
    if unrated:
        notes.append("%d idea(s) had no ratings and got neutral 3s. Rate them (pain | proof | novelty | fit | effort, each 1 to 5) to rank properly." % unrated)
    if dups:
        notes.append("%d near-duplicate pair(s). Merge them or drop one." % len(dups))
    return {"ideas": items, "duplicates": dups, "weights": WEIGHTS, "notes": notes}


def duplicates(ideas: List[str], threshold: float = 0.6) -> List[Dict[str, Any]]:
    toks = [_tokens(i) for i in ideas]
    out = []
    for i in range(len(ideas)):
        for j in range(i + 1, len(ideas)):
            if not toks[i] or not toks[j]:
                continue
            jac = len(toks[i] & toks[j]) / len(toks[i] | toks[j])
            if jac >= threshold:
                out.append({"a": ideas[i], "b": ideas[j], "similarity": round(jac, 2)})
    return out


def matrix(pillars: List[str], angles: Optional[List[str]] = None, limit: int = 60) -> List[Dict[str, str]]:
    if not pillars:
        raise ToolError("Give at least one pillar.")
    angles = angles or ANGLES
    out = []
    for i, a in enumerate(angles):
        for p in pillars:
            out.append({"pillar": p, "angle": a, "prompt": "%s: %s" % (p, a)})
    # interleave so the first N cover every pillar
    out.sort(key=lambda r: (angles.index(r["angle"]) if r["angle"] in angles else 0, pillars.index(r["pillar"])))
    return out[:limit]


def render(res: Dict[str, Any]) -> str:
    out = ["IDEA RANKING  |  weights: " + ", ".join("%s %.0f%%" % (k, v * 100) for k, v in res["weights"].items()), "=" * 78]
    for i, it in enumerate(res["ideas"], 1):
        flag = "" if it["rated"] else "  (unrated)"
        out.append("%2d. %5.1f  %s%s" % (i, it["score"], it["idea"][:62], flag))
    for n in res["notes"]:
        out.append("  - " + n)
    for d in res["duplicates"]:
        out.append("    ~ %s%s  (%.0f%% alike)" % (d["a"][:34], " / " + d["b"][:34], d["similarity"] * 100))
    return "\n".join(out)
