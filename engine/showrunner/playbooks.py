"""Playbooks: the orchestration layer.

A playbook is an ordered list of steps. Each step names the skill to run, what to do, and a
gate: `approve` (a person must say yes before moving on), `human` (a person does something outside
the chat), `data` (a person must bring numbers or files), or `auto`.

This module keeps the state of a run on disk so an agent can stop, resume tomorrow, or hand over
to another agent. It never publishes anything. Every `human` step stays human.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import store
from .util import ToolError

DATA = Path(__file__).resolve().parent / "data" / "playbooks"
GATE_HELP = {
    "approve": "Show the result and wait for a clear yes before moving on.",
    "human": "This step happens outside the chat. Ask the person to do it, then confirm it is done.",
    "data": "Ask the person for the numbers or files this step needs. Do not guess them.",
    "auto": "Safe to run without asking.",
}


def _load_all() -> Dict[str, Dict[str, Any]]:
    out = {}
    for p in sorted(DATA.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[d["id"]] = d
    return out


def list_all() -> List[Dict[str, Any]]:
    return [{"id": d["id"], "title": d["title"], "duration": d["duration"], "steps": len(d["steps"]), "when": d["when"]} for d in _load_all().values()]


def get(pid: str) -> Dict[str, Any]:
    all_ = _load_all()
    if pid not in all_:
        raise ToolError("No playbook '%s'. Available: %s" % (pid, ", ".join(all_)))
    return all_[pid]


def _runs_dir() -> Path:
    return store.home() / "runs"


def _run_path(run_id: str) -> Path:
    return _runs_dir() / (run_id + ".json")


def start(pid: str, name: Optional[str] = None) -> Dict[str, Any]:
    pb = get(pid)
    store.ensure_home()
    base = re.sub(r"[^a-z0-9-]+", "-", (name or pid).lower()).strip("-") or pid
    run_id, n = base, 1
    while _run_path(run_id).exists():
        n += 1
        run_id = "%s-%d" % (base, n)
    run = {"id": run_id, "playbook": pid, "started": store.now_iso(), "steps": {s["id"]: {"status": "pending", "note": "", "at": None} for s in pb["steps"]}}
    store.write_json(_run_path(run_id), run)
    return run


def _latest_run() -> Optional[str]:
    d = _runs_dir()
    if not d.exists():
        return None
    runs = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in runs:
        r = store.read_json(p, {})
        if any(s["status"] == "pending" for s in r.get("steps", {}).values()):
            return r["id"]
    return runs[0].stem if runs else None


def _load_run(run_id: Optional[str]) -> Dict[str, Any]:
    rid = run_id or _latest_run()
    if not rid:
        raise ToolError("No run in progress. Start one with: playbook start <id>")
    run = store.read_json(_run_path(rid), None)
    if not run:
        raise ToolError("No run called '%s'." % rid)
    return run


def next_step(run_id: Optional[str] = None) -> Dict[str, Any]:
    run = _load_run(run_id)
    pb = get(run["playbook"])
    for i, s in enumerate(pb["steps"], 1):
        if run["steps"][s["id"]]["status"] == "pending":
            done_notes = {k: v["note"] for k, v in run["steps"].items() if v["status"] == "done" and v["note"]}
            return {"run": run["id"], "playbook": pb["id"], "step": s, "number": i, "of": len(pb["steps"]),
                    "gate_help": GATE_HELP[s["gate"]], "earlier_notes": done_notes}
    return {"run": run["id"], "playbook": pb["id"], "step": None, "number": len(pb["steps"]), "of": len(pb["steps"]),
            "gate_help": "", "earlier_notes": {k: v["note"] for k, v in run["steps"].items() if v["note"]}}


def done(step_id: str, note: str = "", run_id: Optional[str] = None, skip: bool = False) -> Dict[str, Any]:
    run = _load_run(run_id)
    if step_id not in run["steps"]:
        raise ToolError("Step '%s' is not in this playbook. Steps: %s" % (step_id, ", ".join(run["steps"])))
    run["steps"][step_id].update({"status": "skipped" if skip else "done", "note": note, "at": store.now_iso()})
    store.write_json(_run_path(run["id"]), run)
    return next_step(run["id"])


def status(run_id: Optional[str] = None) -> Dict[str, Any]:
    run = _load_run(run_id)
    pb = get(run["playbook"])
    rows = [{"id": s["id"], "title": s["title"], "skill": s["skill"], "gate": s["gate"], **run["steps"][s["id"]]} for s in pb["steps"]]
    n_done = sum(1 for r in rows if r["status"] in ("done", "skipped"))
    return {"run": run["id"], "playbook": pb["id"], "title": pb["title"], "done": n_done, "total": len(rows), "steps": rows}


def render_list(rows: List[Dict[str, Any]]) -> str:
    out = ["PLAYBOOKS", "=" * 74]
    for r in rows:
        out.append("%-22s %-12s %2d steps  %s" % (r["id"], r["duration"], r["steps"], r["title"]))
        out.append("    When: " + r["when"])
    return "\n".join(out)


def render_show(pb: Dict[str, Any]) -> str:
    out = ["%s  (%s)" % (pb["title"], pb["duration"]), pb["summary"], "=" * 74]
    for i, s in enumerate(pb["steps"], 1):
        out.append("%2d. %-12s [%-7s] %-16s %s" % (i, s["id"], s["gate"], s["skill"], s["title"]))
        out.append("      " + s["do"])
    return "\n".join(out)


def render_next(n: Dict[str, Any]) -> str:
    if n["step"] is None:
        return "Playbook '%s' (run %s) is finished. Every step is done or skipped." % (n["playbook"], n["run"])
    s = n["step"]
    out = ["STEP %d of %d  |  %s  |  run %s" % (n["number"], n["of"], n["playbook"], n["run"]), "=" * 74,
           "%s" % s["title"], "Skill: %s     Gate: %s" % (s["skill"], s["gate"]), "",
           "Do: " + s["do"], "Produces: " + (s["produces"] or "-"), "Gate rule: " + n["gate_help"]]
    if n["earlier_notes"]:
        out.append("")
        out.append("Carry forward:")
        for k, v in n["earlier_notes"].items():
            out.append("  %s: %s" % (k, v))
    out.append("")
    out.append("When finished: playbook done %s --note \"what was decided\"" % s["id"])
    out.append("To skip it:    playbook done %s --skip --note \"why, and what later steps lose\"" % s["id"])
    return "\n".join(out)


def render_status(st: Dict[str, Any]) -> str:
    out = ["%s  |  run %s  |  %d of %d done" % (st["title"], st["run"], st["done"], st["total"]), "=" * 74]
    mark = {"done": "[x]", "skipped": "[-]", "pending": "[ ]"}
    for r in st["steps"]:
        out.append("%s %-14s %-16s %s%s" % (mark[r["status"]], r["id"], r["skill"], r["title"], ("  -> " + r["note"]) if r["note"] else ""))
    return "\n".join(out)
