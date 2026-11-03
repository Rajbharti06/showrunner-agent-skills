"""Where Showrunner keeps your state: profile, experiments, playbook runs, weights.

Default home is ~/.showrunner. Override with SHOWRUNNER_HOME.
Everything is plain JSON or JSONL so you can read it, diff it, and delete it.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .util import ToolError

PROFILE_FIELDS = {
    "name": str,
    "niche": str,
    "audience": dict,          # {"who": str, "region": str, "languages": [..], "level": str}
    "goal": str,
    "stage": str,              # zero | seed | growing | established
    "platforms": list,
    "hub": str,
    "hours_per_week": (int, float),
    "on_camera": bool,
    "tools": list,
    "pillars": list,
    "proof": list,             # things you can actually prove about yourself
    "voice": dict,             # {"banned_phrases": [..], "banned_chars": [..], "notes": str}
    "content_type": str,
    "best_times": dict,        # filled from your own analytics, never guessed
    "lessons": list,           # one line per adopted finding, with the sample size
}

STAGES = ("zero", "seed", "growing", "established")


def home() -> Path:
    p = Path(os.environ.get("SHOWRUNNER_HOME") or (Path.home() / ".showrunner"))
    return p


def ensure_home() -> Path:
    h = home()
    h.mkdir(parents=True, exist_ok=True)
    return h


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ToolError("%s is not valid JSON: %s" % (path, exc))


def write_json(path: Path, obj: Any) -> None:
    _atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            raise ToolError("%s line %d is not valid JSON." % (path, i))
    return out


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


# ---- profile -------------------------------------------------------------

def profile_path() -> Path:
    return home() / "profile.json"


def load_profile() -> Optional[Dict[str, Any]]:
    return read_json(profile_path(), None)


def validate_profile(data: Dict[str, Any]) -> List[str]:
    problems = []
    for key, val in data.items():
        if key.startswith("_") or key in ("created", "updated"):
            continue
        if key not in PROFILE_FIELDS:
            problems.append("unknown field '%s'" % key)
            continue
        want = PROFILE_FIELDS[key]
        if not isinstance(val, want):
            problems.append("'%s' has the wrong type" % key)
    if data.get("stage") and data["stage"] not in STAGES:
        problems.append("stage must be one of %s" % ", ".join(STAGES))
    hrs = data.get("hours_per_week")
    if isinstance(hrs, (int, float)) and not isinstance(hrs, bool) and not (0 < hrs <= 80):
        problems.append("hours_per_week must be between 0 and 80")
    return problems


def save_profile(data: Dict[str, Any], merge: bool = True) -> Dict[str, Any]:
    data = dict(data)
    ct = data.get("content_type")
    if isinstance(ct, list) and ct and all(isinstance(x, str) for x in ct):
        # intake takes several formats, the profile keeps one; several means a mix
        data["content_type"] = ct[0] if len(ct) == 1 else "mix"
    problems = validate_profile(data)
    if problems:
        raise ToolError("Profile problems: " + "; ".join(problems))
    cur = (load_profile() or {}) if merge else {}
    cur.update({k: v for k, v in data.items() if not k.startswith("_")})
    cur.setdefault("created", now_iso())
    cur["updated"] = now_iso()
    write_json(profile_path(), cur)
    return cur


# ---- weights (written by `calibrate`) -----------------------------------

def weights_path() -> Path:
    return home() / "weights.json"
