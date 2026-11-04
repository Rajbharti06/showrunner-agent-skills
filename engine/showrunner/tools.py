"""The tool registry. One definition per tool, used by the CLI and by the MCP server.

A tool is: a name, a plain description, a list of typed parameters, and a handler that returns
(text, data). `text` is what a person reads. `data` is the same result as structured JSON.
Nothing in here publishes anything or calls a network. The only things that write to disk are
the clearly marked stateful tools, and they write to SHOWRUNNER_HOME (default ~/.showrunner).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import (beats, calibrate, captions, clips, experiments, facts, hooks, humanize, ideas, intake,
               outliers, planner, playbooks, render, retention, srt, store, titles)
from .util import ToolError, jdump, load_data, packs, read_text, truncate

VERSION = "0.1.2"
MAX_INPUT_CHARS = 1_500_000

PLATFORMS = sorted(load_data("fit.json")["platforms"])
CAPTION_PLATFORMS = sorted(captions.LIMITS)
STAGES = list(planner.STAGES)
CONTENT_TYPES = list(intake.CONTENT_TYPES)
CAL_TYPES = ["mix", "short_video", "long_video", "carousel", "text"]


def P(name: str, type_: str, help_: str, required: bool = False, default: Any = None,
      enum: Optional[List[str]] = None, positional: bool = False, bulk: bool = False,
      file_alias: bool = False) -> Dict[str, Any]:
    return {"name": name, "type": type_, "help": help_, "required": required, "default": default,
            "enum": enum, "positional": positional, "bulk": bulk}


def _file_param(of: str = "text") -> Dict[str, Any]:
    return {"name": "file", "type": "string", "help": "Path to a file to read instead of passing '%s'. Local use only." % of,
            "required": False, "default": None, "enum": None, "positional": False, "bulk": False, "is_file": True}


class Tool:
    def __init__(self, name: str, cli: str, summary: str, description: str, params: List[Dict[str, Any]],
                 handler: Callable[[Dict[str, Any]], Tuple[str, Any]], stateful: bool = False):
        self.name, self.cli, self.summary, self.description = name, cli, summary, description
        self.params, self.handler, self.stateful = params, handler, stateful

    def schema(self, allow_files: bool = True) -> Dict[str, Any]:
        props, req = {}, []
        for p in self.params:
            if p.get("is_file") and not allow_files:
                continue
            t = p["type"]
            if t == "string_list":
                d = {"type": "array", "items": {"type": "string"}}
            elif t == "object":
                d = {"type": "object"}
            else:
                d = {"type": t}
            d["description"] = p["help"]
            if p["enum"]:
                d["enum"] = p["enum"]
            if p["default"] is not None:
                d["default"] = p["default"]
            props[p["name"]] = d
            if p["required"]:
                req.append(p["name"])
        sch: Dict[str, Any] = {"type": "object", "properties": props, "additionalProperties": False}
        if req:
            sch["required"] = req
        return sch


# ---------------------------------------------------------------- coercion

def _coerce(tool: Tool, params: Dict[str, Any]) -> Dict[str, Any]:
    known = {p["name"]: p for p in tool.params}
    out: Dict[str, Any] = {k: v for k, v in params.items() if k.startswith("_")}
    for k in params:
        if k.startswith("_"):
            continue
        if k not in known:
            raise ToolError("Unknown parameter '%s' for %s. Known: %s" % (k, tool.name, ", ".join(known) or "none"))
    for name, spec in known.items():
        v = params.get(name)
        if v is None or v == "":
            if spec["required"] and not spec.get("bulk"):
                raise ToolError("Missing required parameter '%s'." % name)
            if spec["default"] is not None:
                out[name] = spec["default"]
            continue
        t = spec["type"]
        try:
            if t == "string":
                v = str(v)
                if len(v) > MAX_INPUT_CHARS:
                    raise ToolError("'%s' is too long (%d characters, limit %d)." % (name, len(v), MAX_INPUT_CHARS))
            elif t == "integer":
                if isinstance(v, bool):
                    raise ValueError
                f = float(v)
                if f != int(f):
                    raise ValueError
                v = int(f)
            elif t == "number":
                if isinstance(v, bool):
                    raise ValueError
                v = float(v)
            elif t == "boolean":
                if isinstance(v, str):
                    low = v.strip().lower()
                    if low in ("1", "true", "yes", "y", "on"):
                        v = True
                    elif low in ("0", "false", "no", "n", "off"):
                        v = False
                    else:
                        raise ValueError
                else:
                    v = bool(v)
            elif t == "string_list":
                if isinstance(v, str):
                    v = [s.strip() for s in re.split(r"[,\n]", v) if s.strip()]
                else:
                    v = [str(s).strip() for s in v if str(s).strip()]
            elif t == "object":
                if isinstance(v, str):
                    v = json.loads(v)
                if not isinstance(v, dict):
                    raise ValueError
        except ToolError:
            raise
        except (ValueError, TypeError):
            raise ToolError("'%s' should be %s." % (name, {"integer": "a whole number", "number": "a number", "boolean": "true or false",
                                                          "object": "a JSON object", "string_list": "a list of text values", "string": "text"}[t]))
        if spec["enum"]:
            vals = v if isinstance(v, list) else [v]
            for x in vals:
                if x not in spec["enum"]:
                    raise ToolError("'%s' must be one of: %s (got '%s')." % (name, ", ".join(spec["enum"]), x))
        out[name] = v
    return out


def _profile(p: Dict[str, Any]) -> Dict[str, Any]:
    if p.get("_readonly"):
        return {}
    return store.load_profile() or {}


def _need_state(p: Dict[str, Any]) -> None:
    if p.get("_readonly"):
        raise ToolError("This tool saves state on disk, and the server is running in read-only mode. Run the MCP server locally (stdio) for state, or start it with --stateful on a machine only you use.")


def _lines(text: str) -> List[str]:
    out = []
    for ln in text.splitlines():
        ln = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s+", "", ln).strip()
        if ln:
            out.append(ln)
    return out


# ---------------------------------------------------------------- handlers

def h_hook_score(p):
    text = read_text(p)
    plat = p.get("platform", "short")
    lines = _lines(text)
    if not lines:
        raise ToolError("No hooks found. Put one hook per line.")
    if len(lines) > 60:
        raise ToolError("Score at most 60 hooks at a time (got %d)." % len(lines))
    res = hooks.rank_hooks(lines, plat)
    return render.hooks(res, plat), {"platform": plat, "results": res}


def h_hook_formulas(p):
    rows = hooks.formulas(p.get("platform"))
    rows = [{k: v for k, v in r.items() if k != "rx"} for r in rows]
    return render.formulas(rows), {"formulas": rows}


def h_title_score(p):
    text = read_text(p)
    kw = p.get("keyword")
    ts = _lines(text)
    if not ts:
        raise ToolError("No titles found. One title per line.")
    res = sorted((titles.score_title(t, kw) for t in ts), key=lambda r: r["score"], reverse=True)
    parts = [render.title(r) for r in res[:6]]
    data: Dict[str, Any] = {"titles": res}
    if len(res) > 1:
        parts.insert(0, "RANKED: " + " | ".join("%.0f  %s" % (r["score"], truncate(r["title"], 40)) for r in res))
    thumb = p.get("thumbnail_text")
    if thumb:
        pr = titles.pair_check(res[0]["title"], thumb)
        plan = titles.test_plan([r["title"] for r in res])
        parts.append(render.pair(pr, plan))
        data["pair"] = pr
        data["test_plan"] = plan
    return "\n\n".join(parts), data


def h_script_beats(p):
    text = read_text(p)
    res = beats.beat_sheet(text, p.get("target_seconds"), p.get("wpm", 165.0))
    return beats.render(res), res


def h_caption_check(p):
    text = read_text(p)
    try:
        res = captions.lint(text, p.get("platform", "instagram"), p.get("keywords"))
    except ValueError as e:
        raise ToolError(str(e))
    return render.caption(res), res


def h_text_humanize(p):
    text = read_text(p)
    banned = p.get("banned_phrases")
    if banned is None:
        banned = ((_profile(p).get("voice") or {}).get("banned_phrases")) or None
    res = humanize.humanize(text, p.get("emdash", "comma"), bool(p.get("keep_quotes", False)), banned)
    return render.humanized(res, show_text=True), res


def h_text_detect(p):
    text = read_text(p)
    res = humanize.detect(text)
    return render.detected(res), res


def h_outliers_rank(p):
    text = read_text(p)
    res = outliers.rank(text, p.get("platform", "short"), int(p.get("top", 15)))
    if p.get("format") == "swipe":
        return outliers.swipe_markdown(res), res
    return outliers.render(res), res


def h_retention_read(p):
    text = read_text(p)
    res = retention.analyze(text, p.get("duration_seconds"), float(p.get("cliff", 5.0)))
    return retention.render(res), res


def h_subtitles_analyze(p):
    text = read_text(p)
    res = srt.analyze(text, float(p.get("pause", 0.7)), p.get("fillers"))
    return srt.render(res), res


def h_subtitles_rechunk(p):
    text = read_text(p)
    out = srt.rechunk(text, int(p.get("words_per_chunk", 4)), int(p.get("max_chars", 28)))
    return out, {"srt": out}


def h_clips_find(p):
    text = read_text(p)
    res = clips.find(text, float(p.get("min_seconds", 20)), float(p.get("max_seconds", 60)), int(p.get("count", 5)),
                     float(p.get("target_seconds", 35)), p.get("source", "input.mp4"), p.get("crop", "center"))
    return clips.render(res), res


def _parse_slots(s: Optional[str]) -> Dict[str, str]:
    if not s:
        return {}
    out = {}
    for part in re.split(r"[,;]\s*", s):
        if not part.strip():
            continue
        m = re.fullmatch(r"\s*([a-z]+)\s*=\s*([01]?\d|2[0-3]):([0-5]\d)\s*", part)
        if not m:
            raise ToolError("Slot '%s' should look like instagram=18:30." % part)
        out[m.group(1)] = "%02d:%s" % (int(m.group(2)), m.group(3))
    return out


def h_calendar_build(p):
    prof = _profile(p)
    hub = p.get("hub") or prof.get("hub")
    if not hub:
        raise ToolError("Which platform is the hub? Run the intake first, or pass 'hub'.")
    if hub not in PLATFORMS:
        raise ToolError("Unknown platform '%s'. Known: %s" % (hub, ", ".join(PLATFORMS)))
    spokes = p.get("spokes")
    if spokes is None:
        spokes = [x for x in (prof.get("platforms") or []) if x != hub and x in PLATFORMS][:2]
    for s in spokes:
        if s not in PLATFORMS:
            raise ToolError("Unknown platform '%s'. Known: %s" % (s, ", ".join(PLATFORMS)))
    hours = p.get("hours_per_week") or prof.get("hours_per_week") or 5.0
    stage = p.get("stage") or prof.get("stage") or "zero"
    ctype = p.get("content_type") or ([prof["content_type"]] if prof.get("content_type") else ["mix"])
    ctype = [c for c in ctype if c in CAL_TYPES] or ["mix"]
    start = None
    if p.get("start"):
        try:
            start = date.fromisoformat(p["start"])
        except ValueError:
            raise ToolError("'start' should be a date like 2026-11-09.")
    pillars = p.get("pillars") or prof.get("pillars") or None
    plan = planner.build(hub, list(spokes), float(hours), stage, ctype, int(p.get("weeks", 4)), start, pillars, _parse_slots(p.get("slots")))
    fmt = p.get("format", "markdown")
    if fmt == "csv":
        return planner.to_csv(plan), plan
    if fmt == "ics":
        return planner.to_ics(plan), plan
    if fmt == "json":
        return jdump(plan), plan
    return planner.render(plan), plan


def h_ideas_score(p):
    res = ideas.score(read_text(p))
    return ideas.render(res), res


def h_ideas_matrix(p):
    rows = ideas.matrix(p["pillars"], None, int(p.get("limit", 36)))
    lines = ["IDEA PROMPTS (pillar x angle). Pick the ones you can answer from your own experience.", "=" * 78]
    for i, r in enumerate(rows, 1):
        lines.append("%2d. %s" % (i, r["prompt"]))
    return "\n".join(lines), {"prompts": rows}


QUESTIONS = [
    {"id": "content_types", "ask": "What do you want to make?", "options": ["short_video", "long_video", "carousel", "text", "mix"],
     "why": "Decides which platforms are a natural home for you.", "multi": True},
    {"id": "audience", "ask": "Who is it for? Describe the person in a sentence: job or situation, region, what they are trying to do.", "options": [],
     "why": "Audiences cluster on different platforms. Vague answers give vague plans."},
    {"id": "goal", "ask": "What do you want out of it?", "options": ["audience", "leads", "authority", "income", "community"],
     "why": "A hiring manager and a paying customer are on different platforms."},
    {"id": "platforms", "ask": "Where do you already post, or want to? It is fine to say 'not sure'.", "options": PLATFORMS,
     "why": "We start from what you named, and we will tell you if it is too many.", "multi": True},
    {"id": "stage", "ask": "Where are you now? (zero = just starting, seed = under 1,000 followers, growing = 1,000 to 10,000, established = over 10,000)", "options": STAGES,
     "why": "Zero followers and 50,000 followers need different advice."},
    {"id": "hours_per_week", "ask": "How many hours a week can you honestly give this, filming and editing included?", "options": [],
     "why": "The plan is sized to your real hours, not the hours you wish you had."},
    {"id": "on_camera", "ask": "Are you willing to be on camera?", "options": ["yes", "no"],
     "why": "Faceless formats exist, and they plan differently."},
]


def h_intake_questions(p):
    lines = ["INTAKE: ask these one or two at a time, in the person's words. Do not interrogate.", "=" * 78]
    for i, q in enumerate(QUESTIONS, 1):
        opt = ("  Options: " + ", ".join(q["options"])) if q["options"] else ""
        lines.append("%d. %s%s" % (i, q["ask"], opt))
        lines.append("     why we ask: " + q["why"])
    lines.append("")
    lines.append("When you have the answers, run the recommendation (CLI: intake, tool: intake_recommend).")
    return "\n".join(lines), {"questions": QUESTIONS}


def h_intake_recommend(p):
    prof = _profile(p)
    given = {k: p[k] for k in ("content_types", "audience", "goal", "stage", "hours_per_week", "platforms", "on_camera") if p.get(k) is not None}
    if not given and not prof:
        raise ToolError("No answers yet. Call intake_questions first and ask them, or pass the answers you have.")
    ans: Dict[str, Any] = {}
    ans["content_types"] = given.get("content_types") or ([prof["content_type"]] if prof.get("content_type") else ["mix"])
    aud = prof.get("audience") if isinstance(prof.get("audience"), dict) else {}
    ans["audience"] = given.get("audience") or " ".join(str(aud.get(k, "")) for k in ("who", "region") if aud.get(k)) or prof.get("niche", "")
    ans["goal"] = given.get("goal") or prof.get("goal") or "audience"
    ans["stage"] = given.get("stage") or prof.get("stage") or "zero"
    ans["hours_per_week"] = given.get("hours_per_week") or prof.get("hours_per_week") or 5
    ans["platforms"] = given.get("platforms") if given.get("platforms") is not None else (prof.get("platforms") or [])
    ans["on_camera"] = given["on_camera"] if "on_camera" in given else prof.get("on_camera")
    res = intake.recommend(ans)
    return intake.render(res), res


def h_facts_search(p):
    rows = facts.query(p.get("platform"), p.get("topic"), p.get("text"), p.get("status"), p.get("id"))
    if not rows:
        return "No facts match. Try fewer filters.", {"facts": []}
    m = facts.meta()
    head = "FACTS  |  %d match  |  database as of %s\n" % (len(rows), m.get("as_of", "?"))
    return head + facts.render(rows, show_age=True), {"facts": rows, "meta": m}


def h_facts_stale(p):
    rows = facts.stale(p.get("days"))
    if not rows:
        return "Nothing is past its review window.", {"stale": []}
    return "STALE FACTS (re-verify before relying on them)\n" + facts.render(rows, show_age=True), {"stale": rows}


def h_calibrate_run(p):
    if p.get("write_weights"):
        _need_state(p)
    res = calibrate.run(read_text(p), bool(p.get("write_weights", False)), p.get("platform", "short"))
    return calibrate.render(res), res


def h_playbook_list(p):
    rows = playbooks.list_all()
    return playbooks.render_list(rows), {"playbooks": rows}


def h_playbook_show(p):
    pb = playbooks.get(p["playbook"])
    return playbooks.render_show(pb), pb


def h_playbook_start(p):
    _need_state(p)
    run = playbooks.start(p["playbook"], p.get("name"))
    n = playbooks.next_step(run["id"])
    return "Started run '%s'.\n\n%s" % (run["id"], playbooks.render_next(n)), {"run": run, "next": n}


def h_playbook_next(p):
    _need_state(p)
    n = playbooks.next_step(p.get("run"))
    return playbooks.render_next(n), n


def h_playbook_done(p):
    _need_state(p)
    n = playbooks.done(p["step"], p.get("note", ""), p.get("run"), bool(p.get("skip", False)))
    return playbooks.render_next(n), n


def h_playbook_status(p):
    _need_state(p)
    st = playbooks.status(p.get("run"))
    return playbooks.render_status(st), st


def h_experiment_new(p):
    _need_state(p)
    rec = experiments.create(p["hypothesis"], p["variable"], p["metric"], p.get("platform", ""))
    return "Logged %s. Post at least 4 pieces per variant before you read it.\n  %s\n  variable: %s | metric: %s" % (
        rec["id"], rec["hypothesis"], rec["variable"], rec["metric"]), rec


def h_experiment_log(p):
    _need_state(p)
    rec = experiments.log(p["experiment"], p["variant"], p["value"], p.get("ref", ""), p.get("note", ""))
    return "Logged %s for %s variant %s: %s" % (p["value"], rec["exp"], rec["variant"], rec["ref"] or "(no ref)"), rec


def h_experiment_review(p):
    _need_state(p)
    items = experiments.review(p.get("experiment"))
    return experiments.render(items), {"experiments": items}


def h_profile_get(p):
    _need_state(p)
    prof = store.load_profile()
    if not prof:
        return "No profile saved yet. Run the intake, then profile_save.", {"profile": None}
    return render.profile(prof), {"profile": prof}


def h_profile_save(p):
    _need_state(p)
    data = dict(p.get("profile") or {})
    data.update({k: p[k] for k in ("niche", "goal", "stage", "hours_per_week", "platforms", "hub", "on_camera") if p.get(k) is not None})
    if p.get("content_types"):
        data["content_type"] = p["content_types"]
    if p.get("audience"):
        aud = data.get("audience")
        if not isinstance(aud, dict):
            aud = {} if p.get("replace") else dict((store.load_profile() or {}).get("audience") or {})
        aud["who"] = p["audience"]
        data["audience"] = aud
    if not data:
        raise ToolError("Nothing to save. Pass the answers with the flags intake takes, or a JSON object of fields.")
    prof = store.save_profile(data, merge=not p.get("replace", False))
    return "Saved to %s\n\n%s" % (store.profile_path(), render.profile(prof)), {"profile": prof}


# ---- skills (for hosts that connect to the engine as a tool server and have no native skill loader)

def skills_dir() -> Optional[Path]:
    env = os.environ.get("SHOWRUNNER_SKILLS")
    cands = [Path(env)] if env else []
    cands.append(Path(__file__).resolve().parents[2] / "skills")
    for c in cands:
        if c.is_dir():
            return c
    return None


def _frontmatter(path: Path) -> Dict[str, str]:
    txt = path.read_text(encoding="utf-8-sig", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", txt, re.S)
    out: Dict[str, str] = {}
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln and not ln.startswith((" ", "\t")):
                k, v = ln.split(":", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def h_skill_list(p):
    d = skills_dir()
    if not d:
        raise ToolError("Skills folder not found. Set SHOWRUNNER_SKILLS to the repo's skills directory.")
    rows = []
    for sd in sorted(d.iterdir()):
        f = sd / "SKILL.md"
        if f.is_file():
            fm = _frontmatter(f)
            rows.append({"name": fm.get("name", sd.name), "description": fm.get("description", "")})
    lines = ["SKILLS (%d). Fetch one with skill_get." % len(rows), "=" * 78]
    for r in rows:
        lines.append("%-22s %s" % (r["name"], truncate(r["description"], 100)))
    return "\n".join(lines), {"skills": rows}


def h_skill_get(p):
    d = skills_dir()
    if not d:
        raise ToolError("Skills folder not found. Set SHOWRUNNER_SKILLS to the repo's skills directory.")
    name = p["name"]
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
        raise ToolError("Skill names are lowercase letters, digits and hyphens.")
    sd = d / name
    f = sd / "SKILL.md"
    if not f.is_file():
        raise ToolError("No skill '%s'. Call skill_list." % name)
    ref = p.get("reference")
    if ref:
        target = (sd / "references" / ref).resolve()
        if not str(target).startswith(str((sd / "references").resolve()) + os.sep) or not target.is_file():
            raise ToolError("No reference '%s' in %s." % (ref, name))
        return target.read_text(encoding="utf-8-sig", errors="replace"), {"skill": name, "reference": ref}
    body = f.read_text(encoding="utf-8-sig", errors="replace")
    refs = sorted(x.name for x in (sd / "references").glob("*.md")) if (sd / "references").is_dir() else []
    tail = ("\n\n---\nReference files you can fetch with skill_get(name, reference): " + ", ".join(refs)) if refs else ""
    return body + tail, {"skill": name, "references": refs}


def h_doctor(p):
    prof_exists = store.profile_path().exists()
    w = hooks.load_weights()
    m = facts.meta()
    d = skills_dir()
    n_skills = len([x for x in d.iterdir() if (x / "SKILL.md").is_file()]) if d else 0
    problems = facts.check()
    rows = [
        ("showrunner", VERSION),
        ("python", sys.version.split()[0]),
        ("home", str(store.home())),
        ("profile", "saved" if prof_exists else "not saved yet"),
        ("hook weights", str(w.get("_source", "default"))),
        ("facts", "%d, database as of %s, %d past review window" % (len(facts.all_facts()), m.get("as_of", "?"), len(facts.stale()))),
        ("fact data check", "ok" if not problems else "%d problem(s): %s" % (len(problems), "; ".join(problems[:3]))),
        ("facts without a link", "%d (each is a good first pull request, see CONTRIBUTING.md)" % len(facts.unlinked())),
        ("playbooks", str(len(playbooks.list_all()))),
        ("data packs", ", ".join("%s %s" % (pk["id"], pk.get("version", "")) for pk in packs()) or "none"),
        ("skills folder", "%s (%d skills)" % (d, n_skills) if d else "not found (fine if you only use the CLI)"),
        ("ffmpeg", shutil.which("ffmpeg") or "not found (only needed to run the clip commands)"),
    ]
    text = "DOCTOR\n" + "=" * 78 + "\n" + "\n".join("%-16s %s" % r for r in rows)
    return text, {k: v for k, v in rows}


# ---------------------------------------------------------------- registry

TEXT = lambda what, help_="": P("text", "string", help_ or what, bulk=True, positional=True)  # noqa: E731

TOOLS: List[Tool] = [
    Tool("intake_questions", "questions", "The questions to ask before recommending anything.",
         "Returns the intake questions (what to make, for whom, where, goal, stage, hours, on camera). Call this first when the person has not told you what they want to create, who it is for and where it will go. Ask one or two at a time, in the person's own words.",
         [], h_intake_questions),
    Tool("intake_recommend", "intake", "Turn the answers into a hub, spokes, weekly load and first 7 days.",
         "Given the person's answers, ranks platforms for their goal, format and audience, picks one hub and one or two spokes, sizes the weekly load to their real hours, and lists the first seven days. The scoring table is an editable opinion, not a prediction. Missing answers are filled from the saved profile when there is one.",
         [P("content_types", "string_list", "What they want to make.", enum=CONTENT_TYPES),
          P("audience", "string", "Who it is for, in a sentence."),
          P("goal", "string", "audience, leads, authority, income or community (or plain words)."),
          P("stage", "string", "Where they are now.", enum=STAGES),
          P("hours_per_week", "number", "Honest hours per week, filming and editing included."),
          P("platforms", "string_list", "Platforms they named, if any.", enum=PLATFORMS),
          P("on_camera", "boolean", "Willing to be on camera?")],
         h_intake_recommend),
    Tool("hook_score", "hook", "Score hooks for first-seconds strength and say what to fix.",
         "Scores one or more hooks (the first line or first three seconds), one per line, on six checks: specificity, front-loading, who it is addressed to, curiosity, stakes and brevity. Flags dealbreakers like greetings, begging and preamble. This is a text heuristic that has not been validated against views, so use it to rank and to find the weak part, not to predict results.",
         [TEXT("hooks", "The hooks, one per line."), _file_param("text"),
          P("platform", "string", "short for vertical video, long for YouTube, text for posts.", default="short", enum=["short", "long", "text"])],
         h_hook_score),
    Tool("hook_formulas", "hook-shapes", "List proven hook shapes with a fill-in template.",
         "Lists the hook shapes the scorer recognises (number plus outcome, mistake, contrarian, story open and so on) with a template, an example and what ruins each.",
         [P("platform", "string", "Filter by where it will run.", enum=["short", "long", "text"])],
         h_hook_formulas),
    Tool("title_score", "title", "Score YouTube titles (and check them against thumbnail text).",
         "Scores one or more video titles, one per line: length, keyword placement, specificity, curiosity and clarity, plus a promise-risk flag. Pass thumbnail_text to check that the thumbnail says something different from the title, and get a test plan.",
         [TEXT("titles", "The titles, one per line."), _file_param("text"),
          P("keyword", "string", "The search phrase the video should rank for."),
          P("thumbnail_text", "string", "The words on the thumbnail. Adds a check that it does not just repeat the title.")],
         h_title_score),
    Tool("script_beats", "beats", "Time a script and flag hooks that run long and dead stretches.",
         "Breaks a spoken script into beats with estimated seconds at a given speaking pace, and flags a hook over three seconds, beats over four, filler runs, a missing loop, an early call to action, and distance from the target length.",
         [TEXT("script", "The script text."), _file_param("text"),
          P("target_seconds", "number", "The length you are aiming for."),
          P("wpm", "number", "Words per minute you speak at.", default=165.0)],
         h_script_beats),
    Tool("caption_check", "caption", "Check a caption against a platform's limits and preview cut.",
         "Shows what the feed shows before the 'more' cut, then checks length, first line, a concrete number or name in the visible window, hashtag count, number of asks, search terms, links and readability for the chosen platform.",
         [TEXT("caption", "The caption text."), _file_param("text"),
          P("platform", "string", "Where it will be posted.", default="instagram", enum=CAPTION_PLATFORMS),
          P("keywords", "string_list", "Search terms it should contain.")],
         h_caption_check),
    Tool("text_humanize", "humanize", "Clean AI-sounding patterns out of a draft.",
         "A style editor for your own drafts. Removes invisible characters, em dashes and curly quotes, cuts or replaces stock phrases, lists the structural habits a script cannot fix, and shows the before and after style score. It makes no claim about AI detectors and should not be used to hide AI use where a platform or employer requires disclosure.",
         [TEXT("text", "The draft."), _file_param("text"),
          P("emdash", "string", "What to do with em dashes.", default="comma", enum=["comma", "period", "hyphen", "keep"]),
          P("keep_quotes", "boolean", "Keep curly quotes."),
          P("banned_phrases", "string_list", "Extra phrases to cut. Defaults to the profile's list.")],
         h_text_humanize),
    Tool("text_detect", "detect", "Style check: burstiness, specificity, stock phrases, fingerprints.",
         "Runs five local style checks on a draft and reports a score with reasons. These are heuristics, not the verdict of any detector service.",
         [TEXT("text", "The draft."), _file_param("text")], h_text_detect),
    Tool("outliers_rank", "outliers", "Rank posts by how far they beat their own account's median.",
         "Takes a table of posts (CSV or TSV with views and caption or title columns, an account column if you have several) and ranks them by multiple over each account's median, so a small account's breakout is not buried under a big account's average. Finds the hook shapes and topics that recur among the outliers. You supply the data; nothing is scraped.",
         [TEXT("table", "CSV or TSV with a header row."), _file_param("table"),
          P("platform", "string", "Hook platform for scoring.", default="short", enum=["short", "long", "text"]),
          P("top", "integer", "How many outliers to show.", default=15),
          P("format", "string", "report, or swipe for a markdown swipe file.", default="report", enum=["report", "swipe"])],
         h_outliers_rank),
    Tool("retention_read", "retention", "Find the cliffs and rewatch bumps in a retention curve.",
         "Takes a retention table (time or percent through, and percent still watching) exported from your analytics and locates drop-offs, rewatch spikes and the overall shape, with a plain-English fix for each.",
         [TEXT("table", "CSV or TSV with time and retention columns."), _file_param("table"),
          P("duration_seconds", "number", "Video length, if the table is in percent of video."),
          P("cliff", "number", "Drop in points that counts as a cliff.", default=5.0)],
         h_retention_read),
    Tool("subtitles_analyze", "subtitles", "Words per minute, dead air and filler words from an SRT or VTT.",
         "Reads a subtitle file and reports pace, long pauses (cut candidates) and filler words with timestamps.",
         [TEXT("srt", "SRT or VTT text."), _file_param("srt"),
          P("pause", "number", "Seconds of silence that count as a pause.", default=0.7),
          P("fillers", "string_list", "Filler words to look for. Defaults to a built-in English list.")],
         h_subtitles_analyze),
    Tool("subtitles_rechunk", "rechunk", "Re-time subtitles into short punchy lines for vertical video.",
         "Splits a subtitle file into 3 to 5 word chunks with proportional timing. Returns SRT.",
         [TEXT("srt", "SRT or VTT text."), _file_param("srt"),
          P("words_per_chunk", "integer", "Words per caption.", default=4),
          P("max_chars", "integer", "Maximum characters per caption.", default=28)],
         h_subtitles_rechunk),
    Tool("clips_find", "clips", "Find the best vertical clips in a long video's transcript.",
         "Scores windows of a transcript on opening hook, self-containment, density and payoff, then returns the best few with timestamps, a ready-to-run ffmpeg command for a 9:16 cut and a caption file. It scores the text only; watch each clip before posting.",
         [TEXT("srt", "SRT or VTT transcript."), _file_param("srt"),
          P("min_seconds", "number", "Shortest clip.", default=20),
          P("max_seconds", "number", "Longest clip.", default=60),
          P("count", "integer", "How many clips.", default=5),
          P("target_seconds", "number", "Ideal length.", default=35),
          P("source", "string", "The video file name for the ffmpeg command.", default="input.mp4"),
          P("crop", "string", "center crop or pad (blurred bars).", default="center", enum=["center", "pad"])],
         h_clips_find),
    Tool("calendar_build", "calendar", "Build a content calendar that fits real weekly hours.",
         "Lays out several weeks of posts for a hub and spokes, sized to the hours the person actually has, with hub pieces first and spoke versions adapted the next day. Defaults come from the saved profile. Output as markdown, CSV, an .ics file, or JSON.",
         [P("hub", "string", "The main platform.", enum=PLATFORMS),
          P("spokes", "string_list", "Secondary platforms.", enum=PLATFORMS),
          P("hours_per_week", "number", "Hours available per week."),
          P("stage", "string", "Account stage.", enum=STAGES),
          P("content_type", "string_list", "Formats you make (one or several).", enum=CAL_TYPES),
          P("weeks", "integer", "How many weeks.", default=4),
          P("start", "string", "Start date, YYYY-MM-DD. Defaults to next Monday."),
          P("pillars", "string_list", "Content pillars to rotate through."),
          P("slots", "string", "Posting times, like instagram=18:30,youtube=17:00. Use your own analytics, not a guess."),
          P("format", "string", "Output format.", default="markdown", enum=["markdown", "csv", "ics", "json"])],
         h_calendar_build),
    Tool("ideas_score", "ideas", "Rank a list of content ideas and flag near-duplicates.",
         "One idea per line, optionally followed by | pain | proof | novelty | fit | effort, each rated 1 to 5. Ranks by a weighted score and flags near-duplicate ideas. Unrated ideas get neutral scores and are marked.",
         [TEXT("ideas", "One idea per line."), _file_param("text")], h_ideas_score),
    Tool("ideas_matrix", "matrix", "Seed brainstorming with pillar by angle prompts.",
         "Crosses content pillars with twelve proven angles (mistake, myth, story, teardown, checklist and so on) so the person has prompts to answer from their own experience.",
         [P("pillars", "string_list", "Two to five content pillars.", required=True),
          P("limit", "integer", "How many prompts.", default=36)],
         h_ideas_matrix),
    Tool("facts_search", "facts", "Look up a platform fact with its source, status and age.",
         "Searches the sourced facts database: limits, formats, policy, ranking signals, tool interop. Every fact has a status (official, reported, inferred or study), a source URL and an as-of date. Use this instead of stating a platform rule from memory.",
         [P("id", "string", "Exact fact id such as youtube.hashtags.cap, or an id prefix such as x.ranking."),
          P("platform", "string", "Platform or general or tooling."), P("topic", "string", "limits, policy, signals, formats, distribution, features, interop, tools or context."),
          P("text", "string", "Words to search for."), P("status", "string", "Filter by status.", enum=["official", "reported", "inferred", "study"])],
         h_facts_search),
    Tool("facts_stale", "stale", "List facts past their review window.",
         "Lists facts older than the review window (90 days by default). Re-verify these before relying on them.",
         [P("days", "integer", "Override the window in days.")], h_facts_stale),
    Tool("calibrate_run", "calibrate", "Test whether the hook score separates YOUR winners from your misses.",
         "Takes a table of your own posts with hook text and views, splits them at each account's median, and reports for each check how often a winner outscores a miss (AUC with a 90% interval). Needs 30 or more posts before it will write calibrated weights.",
         [TEXT("table", "CSV or TSV with views and hook text."), _file_param("table"),
          P("write_weights", "boolean", "Save calibrated weights for the scorer to use (needs 30+ posts)."),
          P("platform", "string", "Hook platform.", default="short", enum=["short", "long", "text"])],
         h_calibrate_run),
    Tool("playbook_list", "playbook list", "List the orchestration playbooks.",
         "Lists the multi-step playbooks: zero to first 1,000, weekly sprint, one source to many pieces, YouTube video launch, profile makeover, monthly review, two-week campaign.",
         [], h_playbook_list),
    Tool("playbook_show", "playbook show", "Show every step of a playbook.",
         "Shows each step with the skill to run and its gate (approve, human, data or auto).",
         [P("playbook", "string", "Playbook id.", required=True, positional=True)], h_playbook_show),
    Tool("playbook_start", "playbook start", "Start a playbook run and get step one.",
         "Starts a run, saved on disk so it survives closing the chat. Returns the first step.",
         [P("playbook", "string", "Playbook id.", required=True, positional=True), P("name", "string", "A name for this run.")],
         h_playbook_start, stateful=True),
    Tool("playbook_next", "playbook next", "Get the next pending step.",
         "Returns the next pending step of the latest run, with notes carried forward from earlier steps.",
         [P("run", "string", "Run id. Defaults to the latest unfinished run.")], h_playbook_next, stateful=True),
    Tool("playbook_done", "playbook done", "Mark a step done and get the next one.",
         "Marks a step done (or skipped) with a note of what was decided, then returns the next step. Only mark a step done after its gate was met: a person approved it, did it, or supplied the data.",
         [P("step", "string", "Step id.", required=True, positional=True), P("note", "string", "What was decided or made."),
          P("run", "string", "Run id."), P("skip", "boolean", "Skip instead of done.")], h_playbook_done, stateful=True),
    Tool("playbook_status", "playbook status", "Show progress through a run.",
         "Shows every step of a run with its status and notes.",
         [P("run", "string", "Run id.")], h_playbook_status, stateful=True),
    Tool("experiment_new", "exp new", "Write down a hypothesis before you post.",
         "Creates an experiment with a hypothesis, the one variable you are changing and the metric you will read.",
         [P("hypothesis", "string", "What you think will happen and why.", required=True),
          P("variable", "string", "The single thing you are changing.", required=True),
          P("metric", "string", "The number you will read.", required=True), P("platform", "string", "Where.")],
         h_experiment_new, stateful=True),
    Tool("experiment_log", "exp log", "Record one post's result for a variant.",
         "Logs the metric value for one post under variant A or B.",
         [P("experiment", "string", "Experiment id, like exp-001.", required=True, positional=True), P("variant", "string", "A or B.", required=True, positional=True),
          P("value", "number", "The metric value.", required=True, positional=True), P("ref", "string", "Link or title of the post."), P("note", "string", "Anything unusual.")],
         h_experiment_log, stateful=True),
    Tool("experiment_review", "exp review", "Read the experiments with an honest significance check.",
         "Compares variants with a permutation test on ranks (views are heavy-tailed), and reports the ratio of medians as the effect size. With fewer than 4 posts per variant it says the sample is too small instead of guessing.",
         [P("experiment", "string", "One experiment id, or leave empty for all.", positional=True)], h_experiment_review, stateful=True),
    Tool("profile_get", "profile get", "Show the saved creator profile.",
         "Returns the saved profile (niche, audience, goal, stage, platforms, hours, pillars, proof, voice).", [], h_profile_get, stateful=True),
    Tool("profile_save", "profile save", "Save or update the creator profile.",
         "Saves the profile so later tools can use it as defaults. Pass the intake answers with the same flags intake takes, a JSON object of fields, or both. Fields: name, niche, audience {who, region, languages, level}, goal, stage, platforms, hub, hours_per_week, on_camera, tools, pillars, proof, voice {banned_phrases, banned_chars, notes}, content_type, best_times, lessons (list of one-line findings). Only save what the person told you.",
         [P("profile", "object", "Fields to save, as a JSON object."),
          P("content_types", "string_list", "What they make. Several are saved as mix.", enum=CONTENT_TYPES),
          P("audience", "string", "Who it is for, in a sentence."),
          P("niche", "string", "The topic, in a few words."),
          P("goal", "string", "audience, leads, authority, income or community (or plain words)."),
          P("stage", "string", "Where they are now.", enum=STAGES),
          P("hours_per_week", "number", "Honest hours per week, filming and editing included."),
          P("platforms", "string_list", "Platforms they post on or want to.", enum=PLATFORMS),
          P("hub", "string", "The hub platform the intake picked.", enum=PLATFORMS),
          P("on_camera", "boolean", "Willing to be on camera?"),
          P("replace", "boolean", "Replace the whole profile instead of merging.")],
         h_profile_save, stateful=True),
    Tool("skill_list", "skills", "List the skills in this repo.", "Lists every skill with its description. For hosts that connect to Showrunner as a tool server and have no native skill loader.",
         [], h_skill_list),
    Tool("skill_get", "skill", "Read a skill's instructions.", "Returns a skill's SKILL.md, or one of its reference files. Follow the instructions you get back.",
         [P("name", "string", "Skill name.", required=True, positional=True), P("reference", "string", "A file from the skill's references folder.")],
         h_skill_get),
    Tool("doctor", "doctor", "Check the install.", "Reports version, Python, where state is kept, whether a profile exists, fact data health, and whether ffmpeg is on the path.", [], h_doctor),
]

BY_NAME: Dict[str, Tool] = {t.name: t for t in TOOLS}
BY_CLI: Dict[str, Tool] = {t.cli: t for t in TOOLS}


def run(name: str, params: Optional[Dict[str, Any]] = None, allow_files: bool = True, readonly: bool = False) -> Dict[str, Any]:
    """Run one tool. Never raises for user errors: returns {"ok": False, "error": "..."}."""
    tool = BY_NAME.get(name)
    if not tool:
        return {"ok": False, "error": "No tool called '%s'." % name}
    try:
        if not allow_files and (params or {}).get("file"):
            raise ToolError("File paths are disabled in this mode. Pass the text itself in 'text'.")
        p = _coerce(tool, dict(params or {}))
        if not allow_files:
            p["_no_files"] = True
            p.pop("file", None)
        if readonly:
            p["_readonly"] = True
        text, data = tool.handler(p)
        data = json.loads(json.dumps(data, default=str, ensure_ascii=False))
        return {"ok": True, "text": text, "data": data}
    except ToolError as e:
        return {"ok": False, "error": str(e)}
    except (ValueError, KeyError) as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    except OSError as e:
        return {"ok": False, "error": "File problem: %s" % e}
