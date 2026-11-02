"""Capacity-aware content calendar.

Most content plans fail on arithmetic: they schedule more than the week can hold.
This plans from your hours first, shows its assumptions, and exports markdown, CSV or .ics.

Effort numbers and cadence targets are STARTING HYPOTHESES. They are editable in the
profile and meant to be replaced by what your own tracking shows.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .util import ToolError, today

EFFORT_MIN = {"long_video": 360, "short_video": 70, "carousel": 55, "text_post": 15, "story": 10}
ADAPT_FACTOR = 0.3          # adapting an idea you already made, as a share of making it fresh
ENGAGE_SHARE = 0.15         # time reserved for replies, comments and DMs
BATCH_DISCOUNT = 0.8        # when 3+ of the same format are made in one sitting

STAGES = ["zero", "seed", "growing", "established"]
# pieces per week by platform, format, stage index
CADENCE = {
    "youtube": {"long_video": [1, 1, 1, 2], "short_video": [3, 4, 5, 5]},
    "instagram": {"short_video": [3, 4, 5, 5], "carousel": [1, 1, 2, 2], "story": [3, 5, 7, 7]},
    "tiktok": {"short_video": [3, 4, 5, 7]},
    "facebook": {"short_video": [2, 3, 3, 4], "text_post": [1, 2, 2, 3]},
    "linkedin": {"text_post": [2, 3, 4, 5], "carousel": [0, 1, 1, 2], "short_video": [0, 1, 1, 2]},
    "x": {"text_post": [5, 7, 10, 14]},
    "threads": {"text_post": [4, 5, 7, 7]},
}
CONTENT_TYPE_FORMATS = {
    "short_video": ["short_video"],
    "long_video": ["long_video", "short_video"],
    "carousel": ["carousel"],
    "text": ["text_post"],
    "mix": None,        # use every format the platform supports, within budget
}
PRIMARY_FORMAT = {"youtube": "short_video", "instagram": "short_video", "tiktok": "short_video", "facebook": "short_video",
                  "linkedin": "text_post", "x": "text_post", "threads": "text_post"}
SPREAD = {0: [], 1: [2], 2: [1, 4], 3: [0, 2, 4], 4: [0, 2, 4, 6], 5: [0, 1, 3, 4, 6], 6: [0, 1, 2, 4, 5, 6], 7: [0, 1, 2, 3, 4, 5, 6],
          8: [0, 0, 1, 2, 3, 4, 5, 6]}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DEFAULT_SLOT = "18:30"


def _types(content_type: Any) -> List[str]:
    """Accept one type, a comma separated string, or a list."""
    if isinstance(content_type, str):
        out = [t.strip() for t in content_type.split(",") if t.strip()]
    else:
        out = [str(t).strip() for t in (content_type or []) if str(t).strip()]
    for t in out:
        if t not in CONTENT_TYPE_FORMATS:
            raise ToolError("content type '%s' is not one of: %s" % (t, ", ".join(CONTENT_TYPE_FORMATS)))
    return out or ["mix"]


def _formats_for(platform: str, content_type: Any) -> List[str]:
    avail = list(CADENCE[platform].keys())
    types = _types(content_type)
    if "mix" in types:
        return avail
    out: List[str] = []
    for t in types:
        for f in CONTENT_TYPE_FORMATS[t]:
            if f in avail and f not in out:
                out.append(f)
    return out or [PRIMARY_FORMAT.get(platform, avail[0])]


def _plural(word: str) -> str:
    return word[:-1] + "ies" if word.endswith("y") else word + "s"


def _hub_primary(hub: str, content_type: Any, formats: List[str]) -> str:
    if "long_video" in _types(content_type) and "long_video" in formats:
        return "long_video"
    pf = PRIMARY_FORMAT.get(hub)
    return pf if pf in formats else formats[0]


def _spoke_formats(sp: str, content_type: Any, si: int = 0) -> List[str]:
    """A spoke adapts a piece the hub already made. It never 'adapts' a 6 hour long video from a short one.
    If the platform does not take that format at this stage (LinkedIn video at zero followers), use its main one."""
    if "mix" in _types(content_type):
        return [PRIMARY_FORMAT[sp]]
    fm = [f for f in _formats_for(sp, content_type) if f != "long_video" and CADENCE[sp][f][si] > 0]
    return fm or [PRIMARY_FORMAT[sp]]


def capacity(hours: float, stage: str, hub: str, spokes: List[str], content_type: Any = "mix") -> Dict[str, Any]:
    if hub not in CADENCE:
        raise ToolError("Unknown platform '%s'. Choose from: %s" % (hub, ", ".join(sorted(CADENCE))))
    if stage not in STAGES:
        raise ToolError("stage must be one of: %s" % ", ".join(STAGES))
    si = STAGES.index(stage)
    budget = hours * 60.0 * (1.0 - ENGAGE_SHARE)
    items: List[Dict[str, Any]] = []
    hub_formats = _formats_for(hub, content_type)
    primary = _hub_primary(hub, content_type, hub_formats)
    for fmt in hub_formats:
        items.append({"platform": hub, "format": fmt, "per_week": float(CADENCE[hub][fmt][si]), "kind": "create", "tier": 0,
                      "primary": fmt == primary})
    for sp in spokes:
        if sp not in CADENCE:
            raise ToolError("Unknown platform '%s'." % sp)
        for fmt in _spoke_formats(sp, content_type, si):
            items.append({"platform": sp, "format": fmt, "per_week": float(CADENCE[sp][fmt][si]), "kind": "adapt", "tier": 1,
                          "primary": False})
    items = [i for i in items if i["per_week"] > 0]
    started = {(i["platform"], i["format"]) for i in items}
    hub_primary_item = next((i for i in items if i["kind"] == "create" and i["primary"]), None)

    def cap_spokes() -> None:
        """You cannot adapt more pieces than the hub made."""
        if hub_primary_item is None:
            return
        for i in items:
            if i["kind"] == "adapt" and i["per_week"] > hub_primary_item["per_week"] / hub_primary_item.get("period_weeks", 1):
                i["per_week"] = max(0.0, float(int(hub_primary_item["per_week"])))

    def cost(i: Dict[str, Any], count: float) -> float:
        base = EFFORT_MIN[i["format"]] * (ADAPT_FACTOR if i["kind"] == "adapt" else 1.0)
        base = max(base, 8.0)
        if i["kind"] == "create" and count >= 3:
            base *= BATCH_DISCOUNT
        return base

    def total() -> float:
        return sum(cost(i, i["per_week"]) * i["per_week"] for i in items)

    warnings: List[str] = []
    guard = 0
    cap_spokes()
    while total() > budget and guard < 300:
        guard += 1
        # Trim in this order: the hub's side formats (stories first, then carousels), then spokes,
        # then the hub's main format, never below one a week. Spokes are cheap and reuse the main piece,
        # so they should outlive the hub's extras.
        side = [i for i in items if i["kind"] == "create" and not i["primary"] and i["per_week"] > 0]
        if side:
            victim = sorted(side, key=lambda i: (i["format"] != "story", -cost(i, i["per_week"]) * i["per_week"]))[0]
            victim["per_week"] -= 1
            continue
        adapt = [i for i in items if i["kind"] == "adapt" and i["per_week"] > 0]
        if adapt:
            victim = max(adapt, key=lambda i: cost(i, i["per_week"]) * i["per_week"])
            victim["per_week"] -= 1
            continue
        main = [i for i in items if i["kind"] == "create" and i["primary"] and i["per_week"] > 1]
        if main:
            main[0]["per_week"] -= 1
            cap_spokes()
            continue
        break
    items = [i for i in items if i["per_week"] > 0]
    dropped = [f for f in hub_formats if f != primary and (hub, f) in started and not any(i["platform"] == hub and i["format"] == f for i in items)]
    if dropped:
        warnings.append("Left out for now to fit your weekly hours: %s on %s (about %s minutes each). Add them back as your hours grow." % (
            ", ".join(_plural(d.replace("_", " ")) for d in dropped), hub, " / ".join(str(EFFORT_MIN[d]) for d in dropped)))
    lost = [sp for sp in spokes if any(k[0] == sp for k in started) and not any(i["platform"] == sp for i in items)]
    if lost:
        warnings.append("Not enough hours left for %s yet. Add it once the hub feels routine." % ", ".join(lost))

    # a single piece that does not fit in one week is made every k weeks
    for i in items:
        c = cost(i, i["per_week"])
        i["period_weeks"] = 1
        if i["kind"] == "create" and i["per_week"] == 1 and c > budget > 0:
            i["period_weeks"] = int(math.ceil(c / budget))
            warnings.append("A %s on %s takes about %d minutes and your weekly creation budget is %d. Plan one every %d weeks, or pick a lighter format." % (
                i["format"].replace("_", " "), i["platform"], c, budget, i["period_weeks"]))
    planned = sum((cost(i, i["per_week"]) * i["per_week"]) / i["period_weeks"] for i in items)
    for i in items:
        i["minutes_each"] = round(cost(i, i["per_week"]))
    if budget < 60:
        warnings.append("Under an hour a week for creation. Do one platform, one format, and nothing else until it feels easy.")
    return {
        "hours_per_week": hours, "creation_budget_min": round(budget), "engagement_min": round(hours * 60 * ENGAGE_SHARE),
        "planned_min": round(planned), "items": items, "warnings": warnings,
        "assumptions": {"effort_minutes": EFFORT_MIN, "adapt_factor": ADAPT_FACTOR, "engage_share": ENGAGE_SHARE, "batch_discount": BATCH_DISCOUNT},
    }


def build(hub: str, spokes: List[str], hours: float, stage: str, content_type: Any = "mix",
          weeks: int = 4, start: Optional[date] = None, pillars: Optional[List[str]] = None,
          slots: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    cap = capacity(hours, stage, hub, spokes, content_type)
    start = start or today()
    start = start + timedelta(days=(7 - start.weekday()) % 7)      # next Monday (or today if Monday)
    pillars_given = bool(pillars)
    pillars = pillars or ["Pillar A", "Pillar B", "Pillar C"]
    slots = slots or {}
    taken: Dict[Any, int] = {}
    rows: List[Dict[str, Any]] = []
    pidx = 0
    used_pillars_default = not pillars_given
    for w in range(weeks):
        hub_days: List[int] = []
        hub_rows: List[Dict[str, Any]] = []
        week_rows: List[Dict[str, Any]] = []
        for it in cap["items"]:
            if it["kind"] != "create" or w % it["period_weeks"] != 0:
                continue
            days = SPREAD[min(int(it["per_week"]), 8)]
            for d in days:
                row = {"day": d, "item": it}
                week_rows.append(row)
                hub_rows.append(row)
                hub_days.append(d)
        # hub pieces take the pillars in order, earliest first; an adapted piece keeps its source's pillar
        for hr in sorted(hub_rows, key=lambda r: (r["day"], r["item"]["tier"])):
            hr["pillar"] = pillars[pidx % len(pillars)]
            pidx += 1
        spoke_idx = 0
        for it in cap["items"]:
            if it["kind"] != "adapt":
                continue
            days = SPREAD[min(int(it["per_week"]), 8)]
            for d in days:
                # land one day after a hub piece when possible
                anchor = hub_days[spoke_idx % len(hub_days)] if hub_days else d
                src = hub_rows[spoke_idx % len(hub_rows)] if hub_rows else None
                spoke_idx += 1
                week_rows.append({"day": min(6, anchor + 1), "item": it, "src": src})
        week_rows.sort(key=lambda r: (r["day"], r["item"]["tier"]))
        for r in week_rows:
            it = r["item"]
            dt = start + timedelta(days=7 * w + r["day"])
            base_t = slots.get(it["platform"], DEFAULT_SLOT)
            k = taken.get((dt, it["platform"]), 0)
            taken[(dt, it["platform"])] = k + 1
            bh, bm = [int(x) for x in base_t.split(":")]
            tot_min = min(23 * 60 + 30, bh * 60 + bm + 120 * k)          # a second post the same day goes out two hours later
            rows.append({
                "date": dt.isoformat(), "weekday": DAYS[dt.weekday()], "time": "%02d:%02d" % divmod(tot_min, 60),
                "platform": it["platform"], "format": it["format"],
                "pillar": r.get("pillar") or (r["src"]["pillar"] if r.get("src") else pillars[0]),
                "task": "Make from scratch" if it["kind"] == "create" else "Adapt from the hub piece",
                "minutes": it["minutes_each"], "done": "",
            })
    notes: List[str] = []
    if used_pillars_default:
        notes.append("Pillars are placeholders (Pillar A, B, C). Replace them with your own three.")
    return {"rows": rows, "capacity": cap, "weeks": weeks, "start": start.isoformat(), "notes": notes,
            "slot_note": "Posting times are placeholders. Replace them with the hours your own analytics show your audience is online."}


def to_csv(plan: Dict[str, Any]) -> str:
    buf = io.StringIO()
    cols = ["date", "weekday", "time", "platform", "format", "pillar", "task", "minutes", "done"]
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in plan["rows"]:
        w.writerow({k: r[k] for k in cols})
    return buf.getvalue()


def _fold(line: str) -> str:
    out, cur = [], line
    while len(cur.encode("utf-8")) > 74:
        cut = 74
        while len(cur[:cut].encode("utf-8")) > 74:
            cut -= 1
        out.append(cur[:cut])
        cur = " " + cur[cut:]
    out.append(cur)
    return "\r\n".join(out)


def _esc(text: str) -> str:
    """RFC 5545 TEXT escaping."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def to_ics(plan: Dict[str, Any]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Showrunner//Content Calendar//EN", "CALSCALE:GREGORIAN"]
    for r in plan["rows"]:
        hh, mm = r["time"].split(":")
        st = datetime.fromisoformat(r["date"]).replace(hour=int(hh), minute=int(mm))
        en = st + timedelta(minutes=30)
        uid = hashlib.sha1(("%s|%s|%s|%s" % (r["date"], r["platform"], r["format"], r["pillar"])).encode()).hexdigest()[:16] + "@showrunner"
        summary = "Post: %s %s (%s)" % (r["platform"], r["format"].replace("_", " "), r["pillar"])
        desc = "%s. About %d minutes of work. Nothing posts itself: review, then publish." % (r["task"], r["minutes"])
        lines += ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp, "DTSTART:" + st.strftime("%Y%m%dT%H%M%S"),
                  "DTEND:" + en.strftime("%Y%m%dT%H%M%S"), "SUMMARY:" + _esc(summary), "DESCRIPTION:" + _esc(desc), "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


def render(plan: Dict[str, Any]) -> str:
    cap = plan["capacity"]
    out = ["CONTENT CALENDAR  |  %d weeks from %s" % (plan["weeks"], plan["start"]), "=" * 78,
           "Hours/week %.1f -> creation budget %d min, engagement %d min, planned %d min/week" % (
               cap["hours_per_week"], cap["creation_budget_min"], cap["engagement_min"], cap["planned_min"]), "-" * 78]
    last_week = None
    for r in plan["rows"]:
        wk = (datetime.fromisoformat(r["date"]).date() - datetime.fromisoformat(plan["start"]).date()).days // 7 + 1
        if wk != last_week:
            out.append("Week %d" % wk)
            last_week = wk
        out.append("  %s %s %s  %-10s %-12s %-14s %3dm  %s" % (r["weekday"], r["date"][5:], r["time"], r["platform"], r["format"], r["pillar"][:14], r["minutes"], "make" if r["task"].startswith("Make") else "adapt"))
    out.append("-" * 78)
    for w in cap["warnings"]:
        out.append("  ! " + w)
    for n in plan.get("notes", []):
        out.append("  ! " + n)
    out.append("  " + plan["slot_note"])
    return "\n".join(out)
