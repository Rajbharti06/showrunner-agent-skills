"""Outlier ranking.

Raw views are not evidence. A 2,000,000-follower account getting 400,000 views
had a quiet Tuesday. A 4,000-follower account getting 400,000 views found
something. This ranks every post by its multiple over its own account's median,
names the hook formula, and shows what separates the top third from the bottom.

Input is a table YOU collected by hand or exported from your own analytics.
Showrunner does not scrape anything.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import hooks
from .util import ToolError, mean, median, parse_table, pick, to_float, truncate, words

ALIASES = {
    "account": ("account", "channel", "creator", "handle", "author", "profile", "username"),
    "views": ("views", "view_count", "plays", "play_count", "impressions", "reach"),
    "text": ("hook", "title", "caption", "text", "description", "first_line", "transcript"),
    "url": ("url", "link", "permalink"),
    "date": ("date", "published", "posted", "published_at", "created", "timestamp"),
    "followers": ("followers", "subscribers", "subs", "follower_count", "subscriber_count"),
    "duration": ("duration", "length", "seconds", "duration_seconds"),
    "platform": ("platform", "network", "source"),
}


def skeleton(text: str) -> str:
    """Strip a hook down to its reusable shape. Steal the structure, not the words."""
    t = re.sub(r"[$€£₹]\s?\d[\d,.]*\s?[kKmMbB]?", "{amount}", text)
    t = re.sub(r"\b\d[\d,.]*\s?(%|percent)", "{pct}", t)
    t = re.sub(r"\b\d[\d,.]*\s?(days?|weeks?|months?|years?|hours?|minutes?|seconds?)\b", "{time}", t, flags=re.I)
    t = re.sub(r"\b\d[\d,.]*[kKmMbB]?\b", "{N}", t)
    parts = t.split()
    for i, w in enumerate(parts):
        if i > 0 and w[:1].isupper() and w.strip(".,!?") not in ("I", "I'm", "I've", "I'll") and not parts[i - 1].endswith((".", "!", "?")):
            parts[i] = "{Name}" + (w[-1] if w[-1] in ".,!?" else "")
    return " ".join(parts)


def _parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s.strip()[:19] if "T" in s or " " in s and ":" in s else s.strip(), fmt)
        except ValueError:
            continue
    return None


def rank(table_text: str, platform: str = "short", top: int = 15) -> Dict[str, Any]:
    rows = parse_table(table_text)
    items: List[Dict[str, Any]] = []
    for r in rows:
        views = to_float(pick(r, ALIASES["views"]))
        text = pick(r, ALIASES["text"])
        if views is None or not text:
            continue
        items.append({
            "account": pick(r, ALIASES["account"], "(unknown)"),
            "views": views,
            "text": text,
            "url": pick(r, ALIASES["url"]),
            "date": pick(r, ALIASES["date"]),
            "followers": to_float(pick(r, ALIASES["followers"])),
            "duration": to_float(pick(r, ALIASES["duration"])),
            "platform": pick(r, ALIASES["platform"]),
        })
    if len(items) < 3:
        raise ToolError("Need at least 3 rows with a views column and some text (hook, title or caption).")

    by_acct: Dict[str, List[float]] = defaultdict(list)
    for it in items:
        by_acct[it["account"]].append(it["views"])
    global_median = median([it["views"] for it in items])
    notes: List[str] = []
    thin = [a for a, v in by_acct.items() if len(v) < 3]
    if thin:
        notes.append("%d account(s) have fewer than 3 posts, so their baseline falls back to the whole-table median: %s" % (len(thin), ", ".join(thin[:5])))

    for it in items:
        vs = by_acct[it["account"]]
        base = median(vs) if len(vs) >= 3 else global_median
        it["baseline"] = base
        it["multiple"] = it["views"] / base if base > 0 else 0.0
        it["reach_ratio"] = (it["views"] / it["followers"]) if it["followers"] else None
        sc = hooks.score_hook(it["text"].split("\n")[0], "short" if platform == "short" else platform)
        it["hook_score"] = sc["score"]
        it["formulas"] = [f["name"] for f in sc["formulas"]]
        it["skeleton"] = skeleton(it["text"].split("\n")[0])
        it["words"] = len(words(it["text"].split("\n")[0]))

    items.sort(key=lambda x: x["multiple"], reverse=True)
    third = max(1, len(items) // 3)
    top_third, bottom_third = items[:third], items[-third:]

    def avg(group: List[Dict[str, Any]], key: str) -> float:
        return mean([g[key] for g in group])

    fcount_top = Counter(f for g in top_third for f in (g["formulas"] or ["(no formula)"]))
    by_formula: Dict[str, List[float]] = defaultdict(list)
    for it in items:
        for f in (it["formulas"] or ["(no formula)"]):
            by_formula[f].append(it["multiple"])
    formula_table = sorted(
        ({"formula": f, "n": len(v), "avg_multiple": round(mean(v), 2)} for f, v in by_formula.items() if f != "(no formula)"),
        key=lambda d: (d["avg_multiple"], d["n"]), reverse=True,
    )

    weekday = Counter()
    for g in top_third:
        d = _parse_date(g["date"]) if g["date"] else None
        if d:
            weekday[d.strftime("%A")] += 1

    summary = {
        "posts": len(items), "accounts": len(by_acct),
        "top_third_avg_hook_score": round(avg(top_third, "hook_score"), 1),
        "bottom_third_avg_hook_score": round(avg(bottom_third, "hook_score"), 1),
        "top_third_avg_words": round(avg(top_third, "words"), 1),
        "bottom_third_avg_words": round(avg(bottom_third, "words"), 1),
        "top_formulas": fcount_top.most_common(4),
        "weekdays_in_top_third": weekday.most_common(3),
    }
    gap = summary["top_third_avg_hook_score"] - summary["bottom_third_avg_hook_score"]
    if len(items) < 20:
        notes.append("Only %d posts. Treat patterns as hunches, not findings." % len(items))
    if abs(gap) < 5:
        notes.append("The hook score barely differs between your top and bottom third (%.1f points). On this data the hook text is not what separated them. Look at the edit, the topic, the first frame." % gap)
    return {"items": items, "top": items[:top], "summary": summary, "formula_table": formula_table, "notes": notes}


def swipe_markdown(res: Dict[str, Any]) -> str:
    lines = ["# Swipe file", "", "Ranked by multiple over each account's own median. Steal the structure, not the words.", ""]
    for it in res["top"]:
        lines.append("## %.1fx  |  %s  |  %s views" % (it["multiple"], it["account"], format(int(it["views"]), ",")))
        lines.append("")
        lines.append("> " + truncate(it["text"], 220))
        lines.append("")
        if it["formulas"]:
            lines.append("- Formula: " + ", ".join(it["formulas"]))
        lines.append("- Shape: `%s`" % truncate(it["skeleton"], 160))
        lines.append("- Hook score: %.0f" % it["hook_score"])
        if it["url"]:
            lines.append("- Source: " + it["url"])
        lines.append("")
    return "\n".join(lines)


def render(res: Dict[str, Any]) -> str:
    s = res["summary"]
    out = ["OUTLIERS  |  %d posts  |  %d accounts  |  baseline: each account's median" % (s["posts"], s["accounts"]), "=" * 78]
    for it in res["top"]:
        f = it["formulas"][0] if it["formulas"] else "-"
        out.append("%7.1fx  hook %3.0f  %-22s %-16s %12s" % (it["multiple"], it["hook_score"], truncate(f, 22), truncate(it["account"], 16), format(int(it["views"]), ",")))
        out.append("          \"%s\"" % truncate(it["text"], 66))
    out.append("-" * 78)
    out.append("Top third vs bottom third: hook score %.1f vs %.1f, hook length %.1f vs %.1f words" % (
        s["top_third_avg_hook_score"], s["bottom_third_avg_hook_score"], s["top_third_avg_words"], s["bottom_third_avg_words"]))
    if res["formula_table"]:
        out.append("Formulas by average multiple: " + "; ".join("%s %.1fx (n=%d)" % (f["formula"], f["avg_multiple"], f["n"]) for f in res["formula_table"][:4]))
    for n in res["notes"]:
        out.append("  - " + n)
    return "\n".join(out)
