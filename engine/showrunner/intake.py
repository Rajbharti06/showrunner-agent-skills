"""The intake: what are you making, who is it for, where does it go, what do you want out of it.

Turns those answers into a transparent first recommendation: which platform is the hub,
which are spokes, what to skip for now, how often, and what to do in the first seven days.
The scoring table is `data/fit.json`. It is the maintainer's opinion, labelled as such,
and you can edit it.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from . import planner
from .util import ToolError, load_data

GOALS = {
    "audience": "Grow an audience or personal brand",
    "leads": "Get leads, customers or sales",
    "authority": "Build credibility, a career or a reputation",
    "income": "Earn creator income",
    "community": "Build a community or support a cause",
}
CONTENT_TYPES = ("short_video", "long_video", "carousel", "text", "mix")
STAGE_NAMES = {"zero": "Starting from zero", "seed": "Under 1,000 followers", "growing": "1,000 to 10,000", "established": "Over 10,000"}

GOAL_ALIASES = {
    "brand": "audience", "personal brand": "audience", "followers": "audience", "audience": "audience", "grow": "audience",
    "leads": "leads", "sales": "leads", "customers": "leads", "clients": "leads", "business": "leads",
    "authority": "authority", "credibility": "authority", "career": "authority", "job": "authority", "reputation": "authority", "hiring": "authority",
    "income": "income", "money": "income", "monetise": "income", "monetize": "income", "revenue": "income",
    "community": "community", "cause": "community", "movement": "community",
}


def _norm_goal(goal: str) -> str:
    g = (goal or "audience").strip().lower()
    if g in GOALS:
        return g
    for k, v in GOAL_ALIASES.items():
        if k in g:
            return v
    return "audience"


def audience_tags(text: str) -> List[str]:
    tags = load_data("fit.json")["audience_tags"]
    low = " " + (text or "").lower() + " "
    found = [t for t, kws in tags.items() if any(re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", low) for k in kws)]
    return found or ["general"]


def _content_fit(cp: Dict[str, int], types: List[str]) -> float:
    if not types or "mix" in types:
        vals = sorted(cp.values(), reverse=True)
        return sum(vals[:2]) / 2.0
    key = {"short_video": "short_video", "long_video": "long_video", "carousel": "carousel", "text": "text"}
    return max(cp[key[t]] for t in types if t in key)


def recommend(answers: Dict[str, Any]) -> Dict[str, Any]:
    fit = load_data("fit.json")
    plats = fit["platforms"]
    types = [t for t in (answers.get("content_types") or ([answers["content_type"]] if answers.get("content_type") else ["mix"])) if t]
    for t in types:
        if t not in CONTENT_TYPES:
            raise ToolError("content type must be one of: %s" % ", ".join(CONTENT_TYPES))
    goal = _norm_goal(answers.get("goal", "audience"))
    stage = answers.get("stage", "zero")
    if stage not in planner.STAGES:
        raise ToolError("stage must be one of: %s" % ", ".join(planner.STAGES))
    hours = float(answers.get("hours_per_week") or 5)
    tags = audience_tags(answers.get("audience", ""))
    want = [p.lower() for p in (answers.get("platforms") or []) if p]
    for p in want:
        if p not in plats:
            raise ToolError("Unknown platform '%s'. Known: %s" % (p, ", ".join(sorted(plats))))
    on_camera = answers.get("on_camera")

    effort_w = 1.0 if hours < 5 else 0.5 if hours < 10 else 0.0
    rows = []
    for pid, p in plats.items():
        g = p["goal"][goal]
        c = _content_fit(p["content"], types)
        a = max(p["audience"][t] for t in tags)
        e = 5 - (p["effort"] - 1) * effort_w
        raw = 0.35 * g + 0.30 * c + 0.25 * a + 0.10 * e
        score = (raw - 1) / 4 * 100
        reasons = []
        if g >= 5:
            reasons.append("one of the strongest fits for your goal (%s)" % GOALS[goal].lower())
        elif g <= 2:
            reasons.append("a weak fit for your goal")
        if c >= 5:
            reasons.append("built for the format you want to make")
        elif c <= 2:
            reasons.append("not a natural home for that format")
        if a >= 5:
            reasons.append("your audience is concentrated here")
        elif a <= 2:
            reasons.append("your audience is thin here")
        if effort_w and p["effort"] >= 4:
            reasons.append("heavy for %.0f hours a week" % hours)
        if pid in want:
            score += 4.0
            reasons.append("you asked for it")
        rows.append({"platform": pid, "label": p["label"], "score": round(score, 1), "reasons": reasons or ["average fit across the board"], "note": p["note"]})
    rows.sort(key=lambda r: r["score"], reverse=True)

    pool = [r for r in rows if r["platform"] in want] if want else rows
    hub = pool[0]["platform"]
    max_spokes = 1 if hours < 6 else 2 if hours < 12 else 3
    if stage == "zero":
        max_spokes = min(max_spokes, 2)
    # a spoke should be cheap to feed from the hub
    fam = set(fit["short_video_family"])
    cand = [r for r in (pool if want else rows) if r["platform"] != hub and r["score"] >= 45]
    bonus = lambda r: 12.0 if (r["platform"] in fam and hub in fam) else 0.0     # cheaper to feed, but not at any price
    cand.sort(key=lambda r: r["score"] + bonus(r), reverse=True)
    spokes = [r["platform"] for r in cand[:max_spokes]]
    skip = [r["platform"] for r in rows if r["platform"] not in [hub] + spokes]
    for r in rows:
        pid = r["platform"]
        if pid == hub:
            r["role"] = "HUB"
        elif pid in spokes:
            r["role"] = "spoke"
        elif pid in want or r["score"] >= 70:
            r["role"] = "later"
            lead = "you asked for it" if pid in want else "a strong fit"
            r["reasons"] = ["%s, but %.0f hours a week fits %d platform%s" % (lead, hours, 1 + max_spokes, "" if max_spokes == 0 else "s")] + [x for x in r["reasons"] if x != "you asked for it"]
        else:
            r["role"] = "skip"

    cap = planner.capacity(hours, stage, hub, spokes, "mix" if "mix" in types else types)
    notes: List[str] = []
    if want and len(want) > 1 + max_spokes:
        dropped = [w for w in want if w not in [hub] + spokes]
        notes.append("You listed %d platforms, but %.0f hours a week fits %d. Start with %s and add %s once the first one feels routine." % (
            len(want), hours, 1 + max_spokes, ", ".join([hub] + spokes), ", ".join(dropped)))
    if on_camera is False and hub in ("youtube", "instagram", "tiktok"):
        notes.append("You prefer not to be on camera. Plan faceless formats: voiceover with screen recording or b-roll, text on screen, or carousels.")
    if hub == "tiktok":
        notes.append("Check TikTok is available and allowed in your market before you build on it.")
    if hours < 3:
        notes.append("Under 3 hours a week. One platform, one format, a fixed weekly slot. Anything else will burn out.")
    notes.extend(cap["warnings"])
    if hub in fam:
        notes.append("%s are all vertical-video platforms. Make once, then post the native version on each: new first frame, platform captions, no watermarks from other apps." % ", ".join(sorted(fam)))

    plan7 = [
        {"day": 1, "do": "Save your profile and capture how you talk, so every draft sounds like you.", "skill": "sr-voice"},
        {"day": 1, "do": "Audit and fix the %s profile: name, one-line promise, link, pinned post." % plats[hub]["label"], "skill": "sr-profile-audit"},
        {"day": 2, "do": "Build a bank of 30 ideas from your three pillars, scored.", "skill": "sr-ideas"},
        {"day": 3, "do": "Collect 10 to 20 posts that beat their own account's median in your niche, then rank them.", "skill": "sr-outliers"},
        {"day": 4, "do": "Write and score three hooks per idea for the best three ideas.", "skill": "sr-hook"},
        {"day": 5, "do": "Script, caption and clean the first batch of pieces. Run the policy check.", "skill": "sr-script"},
        {"day": 6, "do": "Lay out the first four weeks inside your hours budget.", "skill": "sr-calendar"},
        {"day": 7, "do": "Post the first piece. Open an experiment log so what you learn sticks.", "skill": "sr-growth-loop"},
    ]
    return {
        "inputs": {"content_types": types, "audience_tags": tags, "goal": goal, "goal_label": GOALS[goal], "stage": stage,
                   "hours_per_week": hours, "platforms_requested": want, "on_camera": on_camera},
        "ranking": rows, "hub": hub, "spokes": spokes, "skip_for_now": skip,
        "capacity": cap, "measure": {p: fit["measure"][p] for p in [hub] + spokes},
        "first_week": plan7, "notes": notes,
        "disclaimer": "Starting hypothesis from priors in data/fit.json, not a prediction. Replace it with what your own numbers show after 6 to 8 posts.",
    }


def render(res: Dict[str, Any]) -> str:
    i = res["inputs"]
    out = ["INTAKE RESULT", "=" * 78,
           "Making: %s | For: %s | Goal: %s | Stage: %s | %.0f h/week" % (", ".join(i["content_types"]), ", ".join(i["audience_tags"]), i["goal_label"], STAGE_NAMES[i["stage"]], i["hours_per_week"]),
           "-" * 78, "RANKING (fit 0 to 100)"]
    for r in res["ranking"]:
        role = r.get("role") or ("HUB" if r["platform"] == res["hub"] else "spoke" if r["platform"] in res["spokes"] else "skip")
        out.append("  %5.1f  %-10s %-5s  %s" % (r["score"], r["label"], role, "; ".join(r["reasons"][:2])))
    out.append("-" * 78)
    out.append("Hub: %s    Spokes: %s    Skip for now: %s" % (res["hub"], ", ".join(res["spokes"]) or "none", ", ".join(res["skip_for_now"]) or "none"))
    cap = res["capacity"]
    out.append("Weekly load: %d min planned of a %d min creation budget (+%d min for replies and DMs)" % (cap["planned_min"], cap["creation_budget_min"], cap["engagement_min"]))
    for it in cap["items"]:
        out.append("  %-10s %-12s %d per week%s  (~%d min each, %s)" % (it["platform"], it["format"], it["per_week"],
                   "" if it["period_weeks"] == 1 else ", one every %d weeks" % it["period_weeks"], it["minutes_each"], "made fresh" if it["kind"] == "create" else "adapted from the hub piece"))
    out.append("-" * 78)
    out.append("FIRST 7 DAYS")
    for d in res["first_week"]:
        out.append("  Day %d  %s  [%s]" % (d["day"], d["do"], d["skill"]))
    if res["notes"]:
        out.append("-" * 78)
        for n in res["notes"]:
            out.append("  - " + n)
    out.append("-" * 78)
    out.append(res["disclaimer"])
    return "\n".join(out)
