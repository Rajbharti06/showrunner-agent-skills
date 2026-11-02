"""Calibration: does the hook score actually separate YOUR winners from YOUR misses?

Give it a table of your own posts (hook text and views). Within each account it splits posts
at that account's median, then asks, for each of the six checks, how often a winner outscores a
miss (AUC: 0.5 is a coin flip, 1.0 is perfect). Checks that do not beat chance on your data
should not be trusted on your data. It can write calibrated weights for the scorer to use.

This exists because a text scorer that has never met your audience has no right to be trusted.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from . import hooks, store
from .util import ToolError, auc, bootstrap_auc, median, parse_table, pick, to_float
from .outliers import ALIASES


def run(table_text: str, write_weights: bool = False, platform: str = "short") -> Dict[str, Any]:
    rows = parse_table(table_text)
    items = []
    for r in rows:
        v = to_float(pick(r, ALIASES["views"]))
        t = pick(r, ALIASES["text"])
        if v is None or not t:
            continue
        items.append({"account": pick(r, ALIASES["account"], "(all)"), "views": v, "text": t.split("\n")[0]})
    if len(items) < 8:
        raise ToolError("Need at least 8 posts with views and hook text. 30 or more is where the answer starts to mean something.")
    by = defaultdict(list)
    for it in items:
        by[it["account"]].append(it)
    pos: Dict[str, List[float]] = defaultdict(list)
    neg: Dict[str, List[float]] = defaultdict(list)
    used = 0
    for acct, grp in by.items():
        if len(grp) < 4:
            continue
        med = median([g["views"] for g in grp])
        for g in grp:
            if g["views"] == med:
                continue
            sc = hooks.score_hook(g["text"], platform, {**{k: 1.0 / 6 for k in hooks.COMPONENTS}})
            vals = dict(sc["components"])
            vals["total"] = sc["score"]
            bucket = pos if g["views"] > med else neg
            for k, v in vals.items():
                bucket[k].append(v)
            used += 1
    if used < 8:
        raise ToolError("After splitting by account, fewer than 8 usable posts remain. Accounts need 4+ posts each.")

    report = {}
    for k in list(hooks.COMPONENTS) + ["total"]:
        a = auc(pos[k], neg[k])
        lo, hi = bootstrap_auc(pos[k], neg[k])
        if lo > 0.55:
            verdict = "separates winners from misses on this data"
        elif hi < 0.45:
            verdict = "points the wrong way on this data"
        elif lo <= 0.5 <= hi:
            verdict = "indistinguishable from a coin flip here"
        else:
            verdict = "weak signal"
        report[k] = {"auc": round(a, 3), "low": round(lo, 3), "high": round(hi, 3), "verdict": verdict}

    n_win, n_loss = len(pos["total"]), len(neg["total"])
    caveats = []
    if used < 30:
        caveats.append("Only %d usable posts. Intervals are wide on purpose. Read the verdicts as hints." % used)
    if len(by) == 1:
        caveats.append("One account. The result describes your audience and nobody else's.")
    caveats.append("Text only. A hook's delivery, the first frame and the edit are not in the score.")

    default = hooks.load_weights()
    fitted = {k: max(0.0, report[k]["auc"] - 0.5) for k in hooks.COMPONENTS}
    ssum = sum(fitted.values())
    wrote = None
    if ssum > 0 and used >= 30:
        fitted = {k: v / ssum for k, v in fitted.items()}
        blended = {k: 0.5 * default[k] + 0.5 * fitted[k] for k in hooks.COMPONENTS}
        floor = {k: max(0.05, v) for k, v in blended.items()}
        norm = sum(floor.values())
        new = {k: round(v / norm, 4) for k, v in floor.items()}
        new.update({"version": 1, "source": "calibrated", "posts": used})
        if write_weights:
            store.ensure_home()
            store.write_json(store.weights_path(), new)
            wrote = str(store.weights_path())
        proposed = {k: new[k] for k in hooks.COMPONENTS}
    else:
        proposed = None
        if write_weights:
            caveats.append("Weights NOT written: need 30+ usable posts and at least one check above chance.")
    return {"posts_used": used, "winners": n_win, "misses": n_loss, "accounts": len(by), "report": report,
            "proposed_weights": proposed, "wrote": wrote, "caveats": caveats}


def render(res: Dict[str, Any]) -> str:
    out = ["CALIBRATION  |  %d posts used  |  %d above median, %d below  |  %d account(s)" % (res["posts_used"], res["winners"], res["misses"], res["accounts"]), "=" * 78,
           "%-12s %6s   %-15s  verdict" % ("check", "AUC", "90% interval")]
    for k in list(hooks.COMPONENTS) + ["total"]:
        r = res["report"][k]
        out.append("%-12s %6.3f   %.2f to %.2f      %s" % (k, r["auc"], r["low"], r["high"], r["verdict"]))
    out.append("-" * 78)
    if res["proposed_weights"]:
        out.append("Proposed weights: " + ", ".join("%s %.2f" % (k, v) for k, v in res["proposed_weights"].items()))
    if res["wrote"]:
        out.append("Written to " + res["wrote"] + ". The hook scorer will use them from now on. Delete the file to go back to defaults.")
    for c in res["caveats"]:
        out.append("  - " + c)
    return "\n".join(out)
