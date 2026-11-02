"""Platform facts with provenance and an expiry date.

Platform numbers go stale. Every fact here says who said it, how sure we are, and when it
was last checked. `showrunner stale` lists what needs re-verifying. Fixing a stale fact is the
easiest useful pull request in this repo.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from .util import ToolError, load_data, today

STATUS = ("official", "reported", "inferred", "study")
REQUIRED = ("id", "platform", "topic", "claim", "status", "source", "as_of", "confidence")


def all_facts() -> List[Dict[str, Any]]:
    return load_data("facts.json")["facts"]


def meta() -> Dict[str, Any]:
    d = load_data("facts.json")
    return {"as_of": d["as_of"], "stale_after_days": d["stale_after_days"], "count": len(d["facts"])}


def query(platform: Optional[str] = None, topic: Optional[str] = None, text: Optional[str] = None,
          status: Optional[str] = None, fid: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for f in all_facts():
        if fid and not (f["id"] == fid or f["id"].startswith(fid.rstrip(".") + ".")):
            continue
        if platform and f["platform"] != platform:
            continue
        if topic and f["topic"] != topic:
            continue
        if status and f["status"] != status:
            continue
        if text:
            hay = re.findall(r"\w+", (f["claim"] + " " + f["id"].replace(".", " ").replace("_", " ") + " " + (f.get("note") or "")).lower())
            if not all(any(w.startswith(t) for w in hay) for t in re.findall(r"\w+", text.lower())):
                continue
        out.append(f)
    return out


def unlinked() -> List[Dict[str, Any]]:
    """Facts with no source link. Not an error, but each one is a good first contribution."""
    return [f for f in all_facts() if not f.get("url")]


def get(fid: str) -> Dict[str, Any]:
    for f in all_facts():
        if f["id"] == fid:
            return f
    raise ToolError("No fact with id '%s'. Try `showrunner facts` to list them." % fid)


def stale(days: Optional[int] = None, now: Optional[date] = None) -> List[Dict[str, Any]]:
    days = days if days is not None else load_data("facts.json")["stale_after_days"]
    now = now or today()
    out = []
    for f in all_facts():
        age = (now - date.fromisoformat(f["as_of"])).days
        if age > days:
            out.append({**f, "age_days": age})
    return sorted(out, key=lambda f: f["age_days"], reverse=True)


def check() -> List[str]:
    """Structure check used by CI. Returns a list of problems."""
    problems: List[str] = []
    seen = set()
    for f in all_facts():
        for k in REQUIRED:
            if f.get(k) in (None, ""):
                problems.append("%s: missing '%s'" % (f.get("id", "?"), k))
        if f.get("id") in seen:
            problems.append("%s: duplicate id" % f.get("id"))
        seen.add(f.get("id"))
        if f.get("status") not in STATUS:
            problems.append("%s: status must be one of %s" % (f.get("id"), ", ".join(STATUS)))
        if f.get("status") in ("reported", "study") and not f.get("url"):
            problems.append("%s: %s facts need a source url" % (f.get("id"), f.get("status")))
        if f.get("status") == "inferred" and not (f.get("note") or f.get("url")):
            problems.append("%s: inferred facts need a note saying what they are inferred from, or a url" % f.get("id"))
        try:
            date.fromisoformat(f["as_of"])
        except Exception:
            problems.append("%s: as_of must be YYYY-MM-DD" % f.get("id"))
    return problems


def render(rows: List[Dict[str, Any]], show_age: bool = False) -> str:
    if not rows:
        return "No matching facts."
    out = []
    for f in rows:
        tag = "%s/%s" % (f["status"], f["confidence"])
        line = "[%s] %s" % (tag, f["id"])
        if show_age:
            age = f.get("age_days")
            if age is None:
                age = (today() - date.fromisoformat(f["as_of"])).days
            line += "  (%s)" % ("checked today" if age == 0 else "%d days old" % age)
        out.append(line)
        out.append("    " + f["claim"])
        src = f["source"] + (" - " + f["url"] if f.get("url") else "")
        out.append("    Source: " + src + ("; primary: " + f["primary"] if f.get("primary") else "") + "; checked " + f["as_of"])
        if f.get("note"):
            out.append("    Note: " + f["note"])
    return "\n".join(out)
