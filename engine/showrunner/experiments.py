"""Experiment log with an honest significance check.

Most creator "tests" are two posts and a feeling. This keeps a log of what you changed and what
happened, and when you have enough posts per variant it runs a permutation test so you can tell a
real difference from noise. When you do not have enough posts, it says so instead of guessing.
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List, Optional

from . import store
from .util import ToolError, median


def _path():
    return store.home() / "experiments.jsonl"


def _all() -> List[Dict[str, Any]]:
    return store.read_jsonl(_path())


def create(hypothesis: str, variable: str, metric: str, platform: str = "") -> Dict[str, Any]:
    if not hypothesis.strip() or not variable.strip() or not metric.strip():
        raise ToolError("An experiment needs a hypothesis, a variable and a metric. Write them down before you post.")
    n = sum(1 for r in _all() if r["type"] == "experiment") + 1
    rec = {"type": "experiment", "id": "exp-%03d" % n, "hypothesis": hypothesis, "variable": variable, "metric": metric,
           "platform": platform, "created": store.now_iso()}
    store.ensure_home()
    store.append_jsonl(_path(), rec)
    return rec


def log(exp_id: str, variant: str, value: float, ref: str = "", note: str = "") -> Dict[str, Any]:
    exps = {r["id"] for r in _all() if r["type"] == "experiment"}
    if exp_id not in exps:
        raise ToolError("No experiment '%s'. Create one first." % exp_id)
    rec = {"type": "obs", "exp": exp_id, "variant": variant.strip().upper(), "value": float(value), "ref": ref, "note": note, "at": store.now_iso()}
    store.append_jsonl(_path(), rec)
    return rec


def _ranks(values: List[float]) -> List[float]:
    """Average ranks, so ties share their rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _perm_p(a: List[float], b: List[float], seed: int = 11, max_draws: int = 20000) -> float:
    """Two-sided exact (or sampled) permutation test on the rank sum.

    Views are heavy-tailed, so ranks are fairer than means and have more power than medians at
    the sample sizes creators actually have.
    """
    pool = a + b
    n, big_n = len(a), len(a) + len(b)
    ranks = _ranks(pool)
    expect = n * (big_n + 1) / 2.0
    obs = abs(sum(ranks[:n]) - expect)
    idx = list(range(big_n))
    count = total = 0
    from math import comb
    if comb(big_n, n) <= max_draws:
        for ca in itertools.combinations(idx, n):
            total += 1
            if abs(sum(ranks[i] for i in ca) - expect) >= obs - 1e-9:
                count += 1
    else:
        rng = random.Random(seed)
        for _ in range(max_draws):
            rng.shuffle(idx)
            total += 1
            if abs(sum(ranks[i] for i in idx[:n]) - expect) >= obs - 1e-9:
                count += 1
    return count / total


def review(exp_id: Optional[str] = None) -> List[Dict[str, Any]]:
    recs = _all()
    exps = [r for r in recs if r["type"] == "experiment" and (exp_id is None or r["id"] == exp_id)]
    if exp_id and not exps:
        raise ToolError("No experiment '%s'." % exp_id)
    out = []
    for e in exps:
        obs = [r for r in recs if r["type"] == "obs" and r["exp"] == e["id"]]
        by: Dict[str, List[float]] = {}
        for o in obs:
            by.setdefault(o["variant"], []).append(o["value"])
        res: Dict[str, Any] = {"id": e["id"], "hypothesis": e["hypothesis"], "variable": e["variable"], "metric": e["metric"],
                               "variants": {v: {"n": len(x), "median": round(median(x), 3)} for v, x in by.items()}}
        names = sorted(by)
        if len(names) < 2:
            res["verdict"] = "Needs at least two variants (A and B). Log observations with --variant."
        else:
            a, b = by[names[0]], by[names[1]]
            if min(len(a), len(b)) < 4:
                need = 4 - min(len(a), len(b))
                res["verdict"] = "Not enough posts. With %d and %d per variant you cannot tell a real difference from luck. Post at least %d more of the smaller variant." % (len(a), len(b), need)
            else:
                p = _perm_p(a, b)
                ma, mb = median(a), median(b)
                ratio = (mb / ma) if ma else float("inf")
                res["p_value"] = round(p, 3)
                res["ratio_b_over_a"] = round(ratio, 2)
                if p < 0.1 and ratio >= 1.2:
                    res["verdict"] = "%s looks better (%.2fx the median, p=%.2f). Adopt it and keep logging." % (names[1], ratio, p)
                elif p < 0.1 and ratio <= 1 / 1.2:
                    res["verdict"] = "%s looks better (%.2fx the median, p=%.2f). Adopt it and keep logging." % (names[0], 1 / ratio if ratio else 0, p)
                else:
                    res["verdict"] = "No clear difference (p=%.2f). Run it longer, or test something bigger." % p
        out.append(res)
    return out


def render(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "No experiments logged yet. Create one with: exp new --hypothesis ... --variable ... --metric ..."
    out = []
    for r in items:
        out.append("%s  %s" % (r["id"], r["hypothesis"]))
        out.append("    variable: %s | metric: %s" % (r["variable"], r["metric"]))
        for v, s in sorted(r["variants"].items()):
            out.append("    %s: n=%d, median %.3f" % (v, s["n"], s["median"]))
        out.append("    -> " + r["verdict"])
    return "\n".join(out)
