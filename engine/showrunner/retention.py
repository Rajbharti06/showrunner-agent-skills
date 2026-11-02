"""Retention curve reader.

Feed it the audience-retention export from your analytics (two columns: position,
retention). It finds cliffs, rewatch bumps and sticky stretches, then says where to
cut or re-hook. It does not compare you to a benchmark, because honest benchmarks
vary by niche and length. It compares a video to itself, or to your other videos.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .util import ToolError, fmt_ts, parse_table, to_float


def _columns(rows: List[Dict[str, str]]) -> Tuple[List[float], List[float]]:
    keys = list(rows[0].keys())
    if len(keys) < 2:
        raise ToolError("Need two columns: position and retention.")
    xk = next((k for k in keys if any(s in k for s in ("time", "second", "position", "elapsed", "ratio", "percent_of", "x"))), keys[0])
    yk = next((k for k in keys if any(s in k for s in ("retention", "watching", "audience", "viewers", "y"))), None)
    if yk is None or yk == xk:
        yk = next(k for k in keys if k != xk)
    xs, ys = [], []
    for r in rows:
        x, y = to_float(r.get(xk)), to_float(r.get(yk))
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    if len(xs) < 6:
        raise ToolError("Need at least 6 data points on the curve.")
    return xs, ys


def analyze(table_text: str, duration: Optional[float] = None, cliff: float = 5.0) -> Dict[str, Any]:
    rows = parse_table(table_text)
    xs, ys = _columns(rows)
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    xs, ys = [xs[i] for i in order], [ys[i] for i in order]

    if max(ys) <= 1.5:
        ys = [y * 100.0 for y in ys]
    if max(xs) <= 1.0:                       # fraction of the video
        if not duration:
            raise ToolError("Position looks like a fraction (0 to 1). Pass duration in seconds.")
        xs = [x * duration for x in xs]
    elif duration and abs(max(xs) - 100.0) < 1.0 and duration > 100:
        xs = [x / 100.0 * duration for x in xs]   # percent of video
    total = duration or xs[-1]
    if total <= 0:
        raise ToolError("Could not work out the video length.")

    def at(sec: float) -> float:
        if sec <= xs[0]:
            return ys[0]
        for i in range(1, len(xs)):
            if xs[i] >= sec:
                span = xs[i] - xs[i - 1]
                f = (sec - xs[i - 1]) / span if span else 0
                return ys[i - 1] + f * (ys[i] - ys[i - 1])
        return ys[-1]

    area = 0.0
    for i in range(1, len(xs)):
        area += (xs[i] - xs[i - 1]) * (ys[i] + ys[i - 1]) / 2.0
    avg_pct = area / max(xs[-1] - xs[0], 1e-9)

    # slide a window of ~4 percent of the video (at least 2 seconds)
    win = max(2.0, 0.04 * total)
    cliffs: List[Dict[str, Any]] = []
    t = xs[0]
    while t + win <= xs[-1] + 1e-9:
        drop = at(t) - at(t + win)
        if drop >= cliff:
            cliffs.append({"start": t, "end": t + win, "drop": drop})
        t += win / 2.0
    merged: List[Dict[str, Any]] = []
    for c in cliffs:
        if merged and c["start"] <= merged[-1]["end"] + 1e-9:
            merged[-1]["end"] = c["end"]
            merged[-1]["drop"] = at(merged[-1]["start"]) - at(c["end"])
        else:
            merged.append(dict(c))
    tail_start = 0.92 * total                      # the last stretch always falls off; that is not a finding
    merged = [c for c in merged if c["start"] < tail_start]
    merged.sort(key=lambda c: c["drop"], reverse=True)

    bumps: List[Dict[str, Any]] = []
    t = xs[0]
    while t + win <= xs[-1] + 1e-9:
        gain = at(t + win) - at(t)
        if gain >= 1.5:
            if bumps and t <= bumps[-1]["end"] + 1e-9:          # same bump seen through an overlapping window
                bumps[-1]["end"] = t + win
                bumps[-1]["gain"] = max(bumps[-1]["gain"], gain)
            else:
                bumps.append({"start": t, "end": t + win, "gain": gain})
        t += win / 2.0

    early_end = min(total, max(5.0, min(30.0, 0.15 * total)))
    early_drop = at(xs[0]) - at(early_end)
    end_ret = at(xs[-1])
    start_ret = at(xs[0])

    if early_drop >= 0.40 * max(start_ret - end_ret, 1) or early_drop >= 30:
        shape, shape_note = "front-loaded cliff", "Most of the loss happens in the opening. Fix the first %s before anything else." % fmt_ts(early_end)
    elif end_ret >= 0.7 * start_ret:
        shape, shape_note = "loop-friendly", "People who stay, stay to the end. Replays are likely. Check the last line loops back."
    elif merged and merged[0]["drop"] >= 12 and merged[0]["start"] >= early_end:
        shape, shape_note = "mid-video cliff", "One stretch loses a big share at once. That is a specific edit decision, not a hook problem."
    else:
        shape, shape_note = "steady decay", "No single failure. Tighten pacing throughout rather than fixing one spot."

    advice: List[str] = []
    if early_drop >= 25:
        advice.append("%.0f points lost by %s. Re-cut the opening: lead with the payoff or the stake, cut any intro." % (early_drop, fmt_ts(early_end)))
    opening_given = early_drop >= 25
    for c in [c for c in merged if not (opening_given and c["start"] < early_end)][:3]:
        advice.append("Cliff at %s to %s: lost %.0f points. Look at what was on screen and being said. Cut it, shorten it, or add a visual change and a new open loop." % (fmt_ts(c["start"]), fmt_ts(c["end"]), c["drop"]))
    for b in sorted(bumps, key=lambda b: b["gain"], reverse=True)[:2]:
        advice.append("Rewatch bump at %s to %s (+%.1f). Something here earned a replay. Make more moments like it, or lead with it." % (fmt_ts(b["start"]), fmt_ts(b["end"]), b["gain"]))
    if not advice:
        advice.append("No sharp cliffs at the %.0f-point threshold. If views are still low, the problem is upstream: the packaging and who it was shown to." % cliff)

    return {
        "duration": round(total, 1), "points": len(xs), "average_view_pct": round(avg_pct, 1),
        "start_retention": round(start_ret, 1), "end_retention": round(end_ret, 1),
        "early_window_seconds": round(early_end, 1), "early_drop": round(early_drop, 1),
        "shape": shape, "shape_note": shape_note,
        "cliffs": [{"start": round(c["start"], 1), "end": round(c["end"], 1), "drop": round(c["drop"], 1)} for c in merged[:5]],
        "bumps": [{"start": round(b["start"], 1), "end": round(b["end"], 1), "gain": round(b["gain"], 1)} for b in bumps[:5]],
        "advice": advice, "threshold": cliff,
    }


def render(res: Dict[str, Any]) -> str:
    out = ["RETENTION  |  %s long  |  %d points" % (fmt_ts(res["duration"]), res["points"]), "=" * 72,
           "  Average viewed: %.1f%%   Start: %.0f%%   End: %.0f%%" % (res["average_view_pct"], res["start_retention"], res["end_retention"]),
           "  Shape: %s. %s" % (res["shape"].upper(), res["shape_note"]), "-" * 72]
    for a in res["advice"]:
        out.append("  - " + a)
    return "\n".join(out)
