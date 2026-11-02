"""Find the best self-contained clips in a long video, from its transcript.

You give it an SRT of the long video. It slides a window over the sentences, scores each
candidate on hook strength, whether it makes sense without the rest of the video, how
concrete it is, whether it pays off, and pace, then returns the top non-overlapping
clips with timestamps and ready-to-run ffmpeg commands.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from . import hooks, srt
from .util import clip, concrete_markers, ffmpeg_ts, fmt_ts, words

DANGLING = {"and", "so", "but", "it", "that", "this", "they", "he", "she", "because", "which", "then", "also", "or", "those", "these", "him", "her", "them", "its", "there"}
BACKREF = re.compile(r"\b(as i (said|mentioned)|like i (said|mentioned)|earlier|last time|in the previous|we talked about|as we saw|going back to)\b", re.I)
PAYOFF = re.compile(r"\b(so|that'?s why|that is why|which means|the point is|the lesson|the result|turns out|in the end|the key|remember|that'?s the)\b", re.I)


def _sentences(cues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    punct = sum(1 for c in cues if re.search(r"[.!?][\"')\]]*$", c["text"].strip()))
    use_punct = punct / max(len(cues), 1) >= 0.2
    out: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    for i, c in enumerate(cues):
        if cur is None:
            cur = {"start": c["start"], "end": c["end"], "text": c["text"]}
        else:
            cur["end"] = c["end"]
            cur["text"] += " " + c["text"]
        nxt_gap = (cues[i + 1]["start"] - c["end"]) if i + 1 < len(cues) else 99.0
        ends = bool(re.search(r"[.!?][\"')\]]*$", c["text"].strip()))
        if (use_punct and ends) or (not use_punct and nxt_gap >= 0.6) or (cur["end"] - cur["start"]) >= 14.0 or i + 1 == len(cues):
            out.append(cur)
            cur = None
    return out


def _score(text: str, first: str, last: str, dur: float, target: float) -> Dict[str, float]:
    hs = hooks.score_hook(first, "short")["score"]
    first_word = (words(first)[:1] or [""])[0].lower()
    self_c = 40.0 if first_word in DANGLING else 100.0
    if BACKREF.search(text):
        self_c -= 35.0
    wc = max(1, len(words(text)))
    weight, _ = concrete_markers(text)
    dens = clip(weight / wc * 100.0 / 5.0 * 100.0)
    payoff = 100.0 if (PAYOFF.search(last) or re.search(r"\d\W*$", last.strip())) else 50.0
    wpm = wc / (dur / 60.0)
    pace = 100.0 if 130 <= wpm <= 190 else clip(100.0 - min(abs(wpm - 130), abs(wpm - 190)) * 1.5)
    length = clip(100.0 - abs(dur - target) * 3.0)
    total = 0.35 * hs + 0.15 * clip(self_c) + 0.20 * dens + 0.15 * payoff + 0.10 * pace + 0.05 * length
    return {"score": total, "hook": hs, "self_contained": clip(self_c), "density": dens, "payoff": payoff, "pace": pace, "wpm": wpm}


def find(srt_text: str, min_len: float = 20.0, max_len: float = 60.0, n: int = 5,
         target: float = 35.0, source: str = "input.mp4", crop: str = "center") -> Dict[str, Any]:
    cues = srt.parse(srt_text)
    sents = _sentences(cues)
    cands: List[Dict[str, Any]] = []
    for i in range(len(sents)):
        for j in range(i, len(sents)):
            dur = sents[j]["end"] - sents[i]["start"]
            if dur > max_len:
                break
            if dur < min_len:
                continue
            text = " ".join(s["text"] for s in sents[i:j + 1])
            sc = _score(text, sents[i]["text"], sents[j]["text"], dur, target)
            cands.append({"start": sents[i]["start"], "end": sents[j]["end"], "dur": dur, "text": text, "first": sents[i]["text"], **sc})
    cands.sort(key=lambda c: c["score"], reverse=True)
    picked: List[Dict[str, Any]] = []
    for c in cands:
        if all(c["end"] <= p["start"] or c["start"] >= p["end"] for p in picked):
            picked.append(c)
        if len(picked) >= n:
            break
    picked.sort(key=lambda c: c["start"])
    vf = "crop=ih*9/16:ih,scale=1080:1920,setsar=1" if crop == "center" else "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"
    for k, c in enumerate(picked, 1):
        c["id"] = k
        c["ffmpeg"] = 'ffmpeg -ss %s -i "%s" -t %.3f -vf "%s" -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 160k -movflags +faststart "clip_%02d.mp4"' % (
            ffmpeg_ts(c["start"]), source, c["dur"], vf, k)
        window = [dict(x, start=max(0.0, x["start"] - c["start"]), end=max(0.0, x["end"] - c["start"])) for x in cues
                  if x["start"] >= c["start"] - 0.05 and x["end"] <= c["end"] + 0.6]
        c["captions_srt"] = srt.rechunk(srt.to_srt(window)) if window else ""
    notes = []
    if not picked:
        notes.append("No window between %.0fs and %.0fs ended on a sentence boundary. Loosen --min-len/--max-len or check the transcript has timings." % (min_len, max_len))
    if crop == "center":
        notes.append("Center crop assumes the speaker is in the middle of a 16:9 frame. Check each clip, or use --crop pad to letterbox instead.")
    notes.append("Scores are heuristics. Watch each clip cold, with sound off, before you post it.")
    return {"clips": picked, "considered": len(cands), "sentences": len(sents), "notes": notes}


def render(res: Dict[str, Any]) -> str:
    out = ["CLIP CANDIDATES  |  %d windows scored from %d sentences" % (res["considered"], res["sentences"]), "=" * 78]
    for c in res["clips"]:
        out.append("#%d  %s - %s  (%.0fs)  score %.0f   hook %.0f  self-contained %.0f  payoff %.0f  %d wpm" % (
            c["id"], fmt_ts(c["start"]), fmt_ts(c["end"]), c["dur"], c["score"], c["hook"], c["self_contained"], c["payoff"], c["wpm"]))
        out.append('    opens: "%s"' % (c["first"][:70]))
        out.append("    " + c["ffmpeg"])
    for n in res["notes"]:
        out.append("  - " + n)
    return "\n".join(out)
