"""Humanizer and detector.

Cleans a draft so it reads like a person wrote it, then scores what is left.

What it is: a style editor. It removes invisible characters, dash and quote
habits, stock vocabulary and stock sentence shapes, and it tells you which
structures need a human rewrite.

What it is not: a detector bypass. The five checks are local heuristics modelled
on signals public detectors discuss. They do not call GPTZero, Originality,
Turnitin or anyone else, and they cannot promise their verdicts. Where a
platform requires you to label realistic AI-made media, label it
(see the policy-check skill).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from .util import clip, concrete_markers, load_data, mean, sentences, stdev, words

_LEX: Optional[Dict[str, Any]] = None

# characters that are legitimate inside emoji sequences and Indic or Arabic scripts
_JOINERS = {"‌", "‍"}
_SPACE_LIKE = {
    " ": "no-break space", " ": "narrow no-break space", " ": "figure space",
    " ": "thin space", " ": "hair space", " ": "en space", " ": "em space",
    " ": "three-per-em space", " ": "four-per-em space", " ": "six-per-em space",
    " ": "punctuation space", "　": "ideographic space", " ": "medium mathematical space",
}
_DASHES = "—―⸺⸻﹘"
_RTL = re.compile(r"[֐-ࣿיִ-﷿ﹰ-﻿]")


def _lex() -> Dict[str, Any]:
    global _LEX
    if _LEX is None:
        d = load_data("slop.json")
        pairs = list(d["replace"].items()) + [(p, "") for p in d["delete"]]
        pairs.sort(key=lambda kv: len(kv[0]), reverse=True)
        compiled = []
        for phrase, repl in pairs:
            pat = re.escape(phrase.replace("’", "'")).replace(r"\ ", r"\s+")
            compiled.append((phrase, repl, re.compile(r"(?<![\w-])" + pat + r"(?![\w-])", re.I)))
        d["_compiled"] = compiled
        d["_tells"] = [(t["id"], re.compile(t["rx"], re.I | re.M), t["msg"]) for t in d["tells"]]
        d["_flag"] = re.compile(r"(?<![\w-])(" + "|".join(re.escape(f) for f in d["flag"]) + r")(?![\w-])", re.I)
        _LEX = d
    return _LEX


def _case(src: str, repl: str) -> str:
    if not repl:
        return repl
    if len(src) > 1 and src.isupper():
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


# --------------------------------------------------------------------------
# Counting helpers (used by detect and by caption lint)
# --------------------------------------------------------------------------

def slop_hits(text: str) -> List[str]:
    t = text.replace("’", "'")
    hits: List[str] = []
    for phrase, _repl, rx in _lex()["_compiled"]:
        for _m in rx.finditer(t):
            hits.append(phrase)
    return hits


def invisible_count(text: str) -> int:
    lex = _lex()["invisible"]
    n = 0
    for i, ch in enumerate(text):
        cp = "%04X" % ord(ch)
        if cp in lex or 0xE0000 <= ord(ch) <= 0xE007F or 0x206A <= ord(ch) <= 0x206F:
            n += 1
        elif ch in _JOINERS and _joiner_is_stray(text, i):
            n += 1
        elif ch in _SPACE_LIKE:
            n += 1
    return n


def _latin_like(ch: str) -> bool:
    return ord(ch) < 0x250


def _joiner_is_stray(text: str, i: int) -> bool:
    prev = text[i - 1] if i > 0 else " "
    nxt = text[i + 1] if i + 1 < len(text) else " "
    return _latin_like(prev) and _latin_like(nxt)


def structural_tells(text: str) -> List[Dict[str, str]]:
    out = []
    for tid, rx, msg in _lex()["_tells"]:
        m = rx.findall(text)
        if m:
            out.append({"id": tid, "msg": msg, "count": str(len(m))})
    triads = re.findall(r"\b\w+,\s+\w+,\s+and\s+\w+\b", text)
    if len(triads) >= 2:
        out.append({"id": "triads", "msg": "Rule-of-three used %d times. Real lists vary in length." % len(triads), "count": str(len(triads))})
    emoji_bullets = [ln for ln in text.splitlines() if re.match(r"^\s*[✅❌⭐➡\U0001F300-\U0001FAFF]", ln)]
    if len(emoji_bullets) >= 3:
        out.append({"id": "emoji-bullets", "msg": "Emoji bullet list (%d lines). Reads as a template." % len(emoji_bullets), "count": str(len(emoji_bullets))})
    tags = re.findall(r"(?<!\w)#\w+", text)
    wc = max(1, len(words(text)))
    if len(tags) >= 8 or (len(tags) >= 4 and len(tags) / wc > 0.3):
        out.append({"id": "hashtag-wall", "msg": "Hashtag wall (%d tags)." % len(tags), "count": str(len(tags))})
    sl = [len(words(s)) for s in sentences(text)]
    if len(sl) >= 5 and mean(sl) > 0 and stdev(sl) / mean(sl) < 0.2:
        out.append({"id": "uniform-rhythm", "msg": "Every sentence is about the same length. Mix short and long.", "count": "1"})
    starters = [s.split()[0].lower() for s in sentences(text) if s.split()]
    if len(starters) >= 5:
        top = max(set(starters), key=starters.count)
        if starters.count(top) / len(starters) >= 0.4 and top not in ("i",):
            out.append({"id": "same-opener", "msg": "%d sentences start with '%s'." % (starters.count(top), top), "count": str(starters.count(top))})
    return out


# --------------------------------------------------------------------------
# Cleaning
# --------------------------------------------------------------------------

def _mask(text: str) -> Tuple[str, List[str]]:
    held: List[str] = []

    def keep(m: "re.Match[str]") -> str:
        held.append(m.group(0))
        return "\x02%d\x03" % (len(held) - 1)

    text = re.sub(r"`[^`]*`|https?://\S+|(?<!\w)[#@]\w+", keep, text)
    return text, held


def _unmask(text: str, held: List[str]) -> str:
    return re.sub(r"\x02(\d+)\x03", lambda m: held[int(m.group(1))], text)


def clean(text: str, emdash: str = "comma", keep_quotes: bool = False,
          banned_phrases: Optional[List[str]] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (cleaned_text, changes). Changes are aggregated by kind."""
    changes: Dict[Tuple[str, str], int] = {}

    def note(kind: str, what: str, n: int = 1) -> None:
        changes[(kind, what)] = changes.get((kind, what), 0) + n

    lex = _lex()
    rtl = bool(_RTL.search(text))

    # 1. invisible characters
    out_chars: List[str] = []
    for i, ch in enumerate(text):
        cp = "%04X" % ord(ch)
        if cp in lex["invisible"]:
            note("invisible", lex["invisible"][cp])
            continue
        o = ord(ch)
        if 0xE0000 <= o <= 0xE007F:
            note("invisible", "unicode tag character")
            continue
        if 0x206A <= o <= 0x206F:
            note("invisible", "deprecated format character")
            continue
        if ch in _JOINERS and _joiner_is_stray(text, i):
            note("invisible", "stray zero-width joiner" if ch == "‍" else "stray zero-width non-joiner")
            continue
        if ch in ("‎", "‏", "⁦", "⁧", "⁨", "⁩") and not rtl:
            note("invisible", "direction mark in left-to-right text")
            continue
        if ch in _SPACE_LIKE:
            note("invisible", _SPACE_LIKE[ch] + " -> space")
            out_chars.append(" ")
            continue
        out_chars.append(ch)
    t = "".join(out_chars)
    t, held = _mask(t)

    # 2. typography
    n_dash = sum(t.count(d) for d in _DASHES)
    if n_dash:
        if emdash == "keep":
            pass
        else:
            sep = {"comma": ", ", "period": ". ", "hyphen": " - "}.get(emdash, ", ")
            t = re.sub(r"^\s*[%s]\s*" % _DASHES, "- ", t, flags=re.M)
            t = re.sub(r"\s*[%s]\s*" % _DASHES, sep, t)
            note("typography", "em dash -> '%s'" % sep.strip() if sep.strip() else "em dash", n_dash)
    # spaced en dash is an em dash in disguise; unspaced between digits is a range
    n_en = len(re.findall(r"\s–\s", t))
    if n_en:
        t = re.sub(r"\s–\s", ", " if emdash != "hyphen" else " - ", t)
        note("typography", "spaced en dash -> comma", n_en)
    n_en2 = t.count("–")
    if n_en2:
        t = t.replace("–", "-")
        note("typography", "en dash -> hyphen", n_en2)
    if "‑" in t:
        t = t.replace("‑", "-")
        note("typography", "non-breaking hyphen -> hyphen")
    if not keep_quotes:
        nq = sum(t.count(c) for c in "“”‘’")
        if nq:
            t = t.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
            note("typography", "curly quotes -> straight", nq)
    if "…" in t:
        k = t.count("…")
        t = t.replace("…", "...")
        note("typography", "ellipsis character -> three dots", k)

    # 3. lexicon (not inside URLs, hashtags, mentions or code)
    t = t.replace("’", "'")
    for phrase, repl, rx in lex["_compiled"]:
        def sub(m: "re.Match[str]", repl: str = repl) -> str:
            before = t_holder[0][: m.start()]
            at_start = (not before.strip()) or bool(re.search(r"[.!?]\s*$|\n\s*$", before))
            if repl == "":
                return "\x01" if at_start else ""
            return _case(m.group(0), repl)

        t_holder = [t]
        t2, k = rx.subn(sub, t)
        if k:
            note("lexicon", ("%s -> %s" % (phrase, repl)) if repl else ("%s -> (cut)" % phrase), k)
            t = t2

    for phrase in banned_phrases or []:
        if not phrase.strip():
            continue
        rx = re.compile(r"(?<![\w-])" + re.escape(phrase).replace(r"\ ", r"\s+") + r"(?![\w-])", re.I)
        t2, k = rx.subn("", t)
        if k:
            note("voice", "%s -> (cut, your banned list)" % phrase, k)
            t = t2

    # 4. tidy what the cuts left behind
    t = re.sub(r"[ \t]+([,.;:!?])", r"\1", t)
    t = re.sub(r"([,;:])(\s*[,;:])+", r"\1", t)
    t = re.sub(r",\s*([.!?])", r"\1", t)
    t = re.sub(r"(^|[.!?]\s+|\n)\s*[,;:]\s*", r"\1", t)
    t = re.sub(r"\x01\s*[.!?]+\s*", "", t)
    t = re.sub(r"\x01[,;:\s]*([A-Za-z])", lambda m: m.group(1).upper(), t)
    t = t.replace("\x01", "")
    t = re.sub(r"(?<=\S)[ \t]{2,}", " ", t)
    t = re.sub(r"[ \t]+$", "", t, flags=re.M)
    t = _unmask(t, held).strip("\n ")

    result = [{"kind": k, "what": w, "count": n} for (k, w), n in changes.items()]
    return t, result


# --------------------------------------------------------------------------
# Detection (five local checks)
# --------------------------------------------------------------------------

def detect(text: str) -> Dict[str, Any]:
    wc = len(words(text))
    sl = [len(words(s)) for s in sentences(text)]

    if len(sl) >= 5 and mean(sl) > 0:
        cv = stdev(sl) / mean(sl)
        burst = clip((cv - 0.15) / (0.65 - 0.15) * 100.0)
        burst_note = "sentence-length variation %.2f" % cv
    else:
        burst, burst_note = 60.0, "too short to judge rhythm"

    weight, _ = concrete_markers(text)
    per100 = weight / max(wc, 1) * 100.0
    spec = clip(per100 / 6.0 * 100.0)

    hits = slop_hits(text)
    dens = len(hits) / max(wc, 1) * 100.0
    slop = clip(100.0 - dens * 20.0)

    inv = invisible_count(text)
    dashes = sum(text.count(d) for d in _DASHES)
    curly = sum(text.count(c) for c in "“”‘’")
    ell = text.count("…")
    fp = clip(100.0 - inv * 25 - dashes * 12 - min(curly, 10) * 2 - ell * 5)
    fp_note = "%d invisible, %d em dash, %d curly quote" % (inv, dashes, curly)

    tells = structural_tells(text)
    tell_n = sum(int(t["count"]) for t in tells)
    voice = clip(100.0 - 12.0 * min(tell_n, 8))

    human = 0.20 * burst + 0.25 * spec + 0.20 * slop + 0.15 * fp + 0.20 * voice
    verdict = "PASS" if human >= 70 else "BORDERLINE" if human >= 50 else "FLAGGED"
    return {
        "human_score": round(human, 1), "verdict": verdict, "words": wc,
        "checks": {
            "burstiness": {"score": round(burst, 1), "note": burst_note},
            "specificity": {"score": round(spec, 1), "note": "%.1f concrete markers per 100 words" % per100},
            "slop_density": {"score": round(slop, 1), "note": "%d stock terms, %.1f per 100 words" % (len(hits), dens)},
            "fingerprint": {"score": round(fp, 1), "note": fp_note},
            "voice": {"score": round(voice, 1), "note": "%d structural tells" % tell_n},
        },
        "tells": tells, "stock_terms": sorted(set(hits)),
        "disclaimer": "Local heuristics, not detector verdicts. Not GPTZero, Originality, Turnitin or any other service.",
    }


def humanize(text: str, emdash: str = "comma", keep_quotes: bool = False,
             banned_phrases: Optional[List[str]] = None) -> Dict[str, Any]:
    before = detect(text)
    cleaned, changes = clean(text, emdash=emdash, keep_quotes=keep_quotes, banned_phrases=banned_phrases)
    after = detect(cleaned)
    flagged = structural_tells(cleaned)
    flag_words = sorted({m.group(0).lower() for m in _lex()["_flag"].finditer(cleaned)})
    return {
        "text": cleaned, "changes": changes, "before": before, "after": after,
        "needs_rewrite": flagged, "watch_words": flag_words,
        "delta": round(after["human_score"] - before["human_score"], 1),
    }
