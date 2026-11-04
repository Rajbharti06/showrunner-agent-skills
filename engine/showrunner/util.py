"""Small shared helpers. Standard library only."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import random
import re
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


class ToolError(Exception):
    """A user-facing error: bad input, missing file, unsupported option."""


# --------------------------------------------------------------------------
# Text basics. Script-agnostic on purpose: Hindi and Hinglish must work.
# --------------------------------------------------------------------------

_STRIP = "\"'`.,;:!?()[]{}<>“”‘’«»—–-…*_~|/\\।"

NUMBER_WORDS = {
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "billion", "dozen", "half",
}

NOT_PROPER = {"i", "i'm", "i've", "i'll", "i'd", "ok", "okay", "tv", "ai", "us", "uk", "ceo", "faq"}


def words(text: str) -> List[str]:
    """Split on whitespace and trim punctuation. Works for any script."""
    out = []
    for tok in text.split():
        tok = tok.strip(_STRIP)
        if tok:
            out.append(tok)
    return out


def sentences(text: str) -> List[str]:
    """Rough sentence split on terminal punctuation and blank lines."""
    parts = re.split(r"(?<=[.!?।])\s+|\n{2,}|\n", text.strip())
    return [p.strip() for p in parts if p and p.strip()]


def concrete_markers(text: str) -> Tuple[float, List[Tuple[str, str]]]:
    """Count concrete details: numbers, spoken numbers, names, acronyms.

    Returns (weight, [(kind, token), ...]). Weight 1.0 is roughly one real number.
    """
    found: List[Tuple[str, str]] = []
    weight = 0.0
    for sent in sentences(text) or [text]:
        toks = words(sent)
        for i, tok in enumerate(toks):
            low = tok.lower()
            if any(ch.isdigit() for ch in tok):
                weight += 1.0
                found.append(("number", tok))
            elif low in NUMBER_WORDS:
                weight += 0.8
                found.append(("number-word", tok))
            elif i > 0 and low not in NOT_PROPER:
                alpha = re.sub(r"[^A-Za-z]", "", tok)
                if len(alpha) >= 2 and alpha.isupper() and len(alpha) <= 6:
                    weight += 0.6
                    found.append(("acronym", tok))
                elif len(alpha) >= 3 and tok[0].isupper() and alpha[1:].islower():
                    weight += 0.6
                    found.append(("name", tok))
    return weight, found


def clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def mean(xs: Sequence[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def median(xs: Sequence[float]) -> float:
    xs = list(xs)
    return float(statistics.median(xs)) if xs else 0.0


def stdev(xs: Sequence[float]) -> float:
    xs = list(xs)
    return float(statistics.pstdev(xs)) if len(xs) > 1 else 0.0


def auc(pos: Sequence[float], neg: Sequence[float]) -> float:
    """Probability a random positive outranks a random negative (ties count half)."""
    if not pos or not neg:
        return 0.5
    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def bootstrap_auc(pos: Sequence[float], neg: Sequence[float], rounds: int = 300, seed: int = 7) -> Tuple[float, float]:
    """90% bootstrap interval for AUC. Deterministic for a given seed."""
    if len(pos) < 2 or len(neg) < 2:
        return (0.0, 1.0)
    rng = random.Random(seed)
    vals = []
    for _ in range(rounds):
        p = [rng.choice(pos) for _ in pos]
        n = [rng.choice(neg) for _ in neg]
        vals.append(auc(p, n))
    vals.sort()
    return (vals[int(0.05 * rounds)], vals[int(0.95 * rounds) - 1])


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------

def bar(score: float, width: int = 24) -> str:
    n = int(round(clip(score) / 100.0 * width))
    return "#" * n + "." * (width - n)


def fmt_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    if h:
        return "%d:%02d:%04.1f" % (h, m, s)
    return "%d:%04.1f" % (m, s)


def ffmpeg_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec - h * 3600 - m * 60
    return "%02d:%02d:%06.3f" % (h, m, s)


def band(score: float, strong: float = 70.0, ok: float = 45.0) -> str:
    if score >= strong:
        return "STRONG"
    if score >= ok:
        return "OK"
    return "WEAK"


def rule(width: int = 78, ch: str = "=") -> str:
    return ch * width


def truncate(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: max(0, n - 3)].rstrip() + "..."


def ascii_safe(text: str) -> str:
    """Windows consoles on legacy code pages choke on fancy characters."""
    repl = {
        "—": "-", "–": "-", "‘": "'", "’": "'",
        "“": '"', "”": '"', "…": "...", " ": " ",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text


def today() -> date:
    env = os.environ.get("SHOWRUNNER_TODAY")
    if env:
        return date.fromisoformat(env)
    return date.today()


# --------------------------------------------------------------------------
# Input helpers
# --------------------------------------------------------------------------

def read_text(params: Dict[str, Any], key: str = "text", file_key: str = "file", required: bool = True) -> str:
    """Return params[key], or the contents of params[file_key]. UTF-8 with BOM tolerated."""
    val = params.get(key)
    if val is not None and str(val).strip() != "":
        return str(val)
    path = params.get(file_key)
    if path:
        if params.get("_no_files"):
            raise ToolError("File paths are disabled in this mode. Pass the text itself in '%s'." % key)
        p = Path(os.path.expanduser(str(path)))
        if not p.exists():
            raise ToolError("File not found: %s" % p)
        return p.read_text(encoding="utf-8-sig", errors="replace")
    if required:
        raise ToolError("Nothing to read. Pass '%s' or '%s'." % (key, file_key))
    return ""


def parse_table(text: str) -> List[Dict[str, str]]:
    """CSV or TSV or semicolon-separated, header row required. Keys lowercased."""
    text = text.lstrip("﻿").strip("\n")
    if not text.strip():
        raise ToolError("The table is empty.")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = []
    for raw in reader:
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
        if any(row.values()):
            rows.append(row)
    if not rows:
        raise ToolError("No data rows found under the header.")
    return rows


def pick(row: Dict[str, str], aliases: Iterable[str], default: str = "") -> str:
    for a in aliases:
        v = row.get(a)
        if v not in (None, ""):
            return v
    return default


_MULT = {"k": 1e3, "m": 1e6, "b": 1e9}


def to_float(s: Any, default: Optional[float] = None) -> Optional[float]:
    """Parse '1,200', '12.5K', '1.2M', '45%', '0.45'. Returns default on failure."""
    if s is None:
        return default
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().lower().replace(",", "").replace(" ", "")
    if not t:
        return default
    pct = t.endswith("%")
    t = t.rstrip("%")
    mult = 1.0
    if t and t[-1] in _MULT:
        mult = _MULT[t[-1]]
        t = t[:-1]
    try:
        v = float(t) * mult
    except ValueError:
        return default
    return v


def pack_dirs() -> List[Path]:
    """Folders of data packs that extend the shipped data, in load order.

    A pack is a folder with a pack.json and any of the data files (hooks.json, slop.json, ...) plus
    an optional playbooks/ folder. Packs are found in data/packs/ inside the package, in
    SHOWRUNNER_HOME/packs, and in the folders listed in SHOWRUNNER_PACKS. SHOWRUNNER_NO_PACKS=1
    turns them off; the repo's generators set it so a pack on a maintainer's machine never leaks
    into generated files."""
    if os.environ.get("SHOWRUNNER_NO_PACKS"):
        return []
    roots = [Path(__file__).resolve().parent / "data" / "packs",
             Path(os.environ.get("SHOWRUNNER_HOME") or (Path.home() / ".showrunner")) / "packs"]
    roots += [Path(p) for p in os.environ.get("SHOWRUNNER_PACKS", "").split(os.pathsep) if p.strip()]
    out: List[Path] = []
    for root in roots:
        if (root / "pack.json").is_file():
            out.append(root)
        elif root.is_dir():
            out.extend(sorted(c for c in root.iterdir() if (c / "pack.json").is_file()))
    return out


def packs() -> List[Dict[str, Any]]:
    """The data packs in use, one per pack id (the first one found wins)."""
    out: List[Dict[str, Any]] = []
    ids = set()
    for d in pack_dirs():
        try:
            meta = json.loads((d / "pack.json").read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            raise ToolError("Data pack %s has a broken pack.json: %s" % (d, e))
        pid = str(meta.get("id") or d.name)
        if pid in ids:
            continue
        ids.add(pid)
        out.append(dict(meta, id=pid, path=str(d)))
    return out


def _merge(base: Any, extra: Any) -> Any:
    """Packs only add: lists are extended, new keys are added, existing values are kept."""
    if isinstance(base, dict) and isinstance(extra, dict):
        for k, v in extra.items():
            if k not in base:
                base[k] = v
            elif isinstance(base[k], (dict, list)):
                base[k] = _merge(base[k], v)
        return base
    if isinstance(base, list) and isinstance(extra, list):
        return base + extra
    return base


def load_data(name: str) -> Any:
    """Load a JSON file shipped inside the package's data folder, extended by any data packs."""
    here = Path(__file__).resolve().parent / "data" / name
    with open(here, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for p in packs():
        f = Path(p["path"]) / name
        if f.is_file():
            try:
                data = _merge(data, json.loads(f.read_text(encoding="utf-8-sig")))
            except ValueError as e:
                raise ToolError("Data pack %s has a broken %s: %s" % (p["id"], name, e))
    return data


def jdump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False)


def have_stdout_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
