"""Plain-text renderers for the tools that do not carry their own.

Everything here returns ASCII-safe text that reads well in a terminal, a chat window, or a
tool result. No colour codes, no box drawing outside ASCII.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .util import bar, truncate

W = 78


def _h(title: str) -> List[str]:
    return [title, "=" * W]


def hooks(results: List[Dict[str, Any]], platform: str) -> str:
    out = _h("HOOK SCORES  |  %s  |  weights: %s" % (platform, results[0]["weights"] if results else "default"))
    for i, r in enumerate(results, 1):
        out.append("")
        out.append("%d. [%5.1f %s]  %s" % (i, r["score"], r["band"], truncate(r["hook"], 120)))
        out.append("   " + "  ".join("%s %3.0f" % (k[:5], v) for k, v in r["components"].items()))
        if r["formulas"]:
            out.append("   shape: " + ", ".join(f["name"] for f in r["formulas"]))
        for d in r["dealbreakers"]:
            out.append("   DEALBREAKER: " + d)
        for w in r["warnings"]:
            out.append("   warning: " + w)
        if r["band"] != "STRONG" or r["dealbreakers"]:
            out.append("   weakest: %s. %s" % (r["weakest"], r["hint"]))
    out.append("")
    out.append("-" * W)
    out.append("Heuristic text score. It has not been validated against views. Run `calibrate` on your own posts to see which checks hold for your audience.")
    return "\n".join(out)


def formulas(rows: List[Dict[str, Any]]) -> str:
    out = _h("HOOK SHAPES")
    for f in rows:
        out.append("%-20s %s" % (f["name"], f.get("template", "")))
        out.append("    e.g. " + f.get("example", ""))
        out.append("    good for: %s   |   ruined by: %s" % (f.get("purpose", ""), f.get("ruins", "")))
    return "\n".join(out)


def title(res: Dict[str, Any]) -> str:
    out = _h("TITLE  |  %.1f %s  |  %d characters" % (res["score"], res["band"], res["chars"]))
    out.append(res["title"])
    out.append("-" * W)
    for k, v in res["components"].items():
        out.append("%-12s %5.1f  %s" % (k, v, bar(v, 20)))
    for f in res["flags"]:
        out.append("FLAG: " + f)
    if res["risk"]:
        out.append("RISK: " + res["risk"])
    for n in res["notes"]:
        out.append("  - " + n)
    return "\n".join(out)


def pair(res: Dict[str, Any], plan: List[str]) -> str:
    out = _h("TITLE + THUMBNAIL PAIR  |  %.1f" % res["score"])
    out.append("Title:     " + res["title"])
    out.append("Thumbnail: " + (res["thumbnail_text"] or "(image only)"))
    out.append("Word overlap %.0f%%, thumbnail words %d" % (res["overlap"] * 100, res["thumbnail_words"]))
    for n in res["notes"]:
        out.append("  - " + n)
    out.append("-" * W)
    out.append("TO TEST THIS:")
    for p in plan:
        out.append("  - " + p)
    return "\n".join(out)


def caption(res: Dict[str, Any]) -> str:
    out = _h("CAPTION CHECK  |  %s  |  %d chars  |  %d fail, %d warn" % (res["platform"], res["chars"], res["fails"], res["warns"]))
    out.append(res["preview"])
    out.append("-" * W)
    for c in res["checks"]:
        out.append("%-5s %-17s %s" % (c["level"], c["name"], c["msg"]))
    out.append("-" * W)
    out.append("Platform limits here are marked '%s' in the facts database. Run `showrunner facts --topic limits` for sources and dates." % res["limit_status"])
    return "\n".join(out)


def humanized(res: Dict[str, Any], show_text: bool = True) -> str:
    b, a = res["before"], res["after"]
    out = _h("HUMANIZE  |  style score %.1f -> %.1f (%+.1f)" % (b["human_score"], a["human_score"], res["delta"]))
    if res["changes"]:
        out.append("MECHANICAL CHANGES")
        for c in res["changes"]:
            out.append("  %-10s %s%s" % (c["kind"], c["what"], "" if c["count"] == 1 else "  x%d" % c["count"]))
    else:
        out.append("No mechanical changes needed.")
    if res["needs_rewrite"]:
        out.append("")
        out.append("STILL NEEDS A HUMAN REWRITE (a script cannot fix these)")
        for t in res["needs_rewrite"]:
            out.append("  - %s (x%s)" % (t["msg"], t["count"]))
    if res["watch_words"]:
        out.append("")
        out.append("Words to reconsider: " + ", ".join(res["watch_words"]))
    if show_text:
        out.append("")
        out.append("CLEANED TEXT")
        out.append("-" * W)
        out.append(res["text"])
        out.append("-" * W)
    out.append("This is a style editor. It does not promise anything about AI detectors, and nothing here should be used to hide AI use where a rule requires you to disclose it.")
    return "\n".join(out)


def detected(res: Dict[str, Any]) -> str:
    out = _h("STYLE CHECK  |  %.1f  %s  |  %d words" % (res["human_score"], res["verdict"], res["words"]))
    for k, v in res["checks"].items():
        out.append("%-12s %5.1f  %s  %s" % (k, v["score"], bar(v["score"], 16), v["note"]))
    if res["tells"]:
        out.append("")
        for t in res["tells"]:
            out.append("  - %s (x%s)" % (t["msg"], t["count"]))
    if res["stock_terms"]:
        out.append("Stock terms: " + ", ".join(res["stock_terms"][:12]))
    out.append("-" * W)
    out.append(res["disclaimer"])
    return "\n".join(out)


def profile(p: Dict[str, Any]) -> str:
    out = _h("PROFILE")
    for k, v in p.items():
        if isinstance(v, (dict, list)):
            v = str(v)
        out.append("%-15s %s" % (k, truncate(str(v), 58)))
    return "\n".join(out)
