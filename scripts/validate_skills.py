#!/usr/bin/env python3
"""Check every skill against the Agent Skills spec and against this repository.

    python scripts/validate_skills.py

Checks the spec (name, description, sizes), that referenced files exist, that every tool, CLI
command, fact id and skill name mentioned in a SKILL.md is real, and that the shim is in sync.
Exits 1 on any error. Warnings do not fail the run.
"""
import argparse
import glob
import io
import json
import os
import re
import shlex
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKILLS = os.path.join(ROOT, "skills")
sys.path.insert(0, os.path.join(ROOT, "engine"))

from showrunner import cli, facts, tools  # noqa: E402

NAME_RX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FACT_ID_RX = re.compile(r"^(youtube|instagram|tiktok|facebook|linkedin|x|threads|general|tooling)\.[a-z0-9_.]+$")
ERRORS = []
WARNINGS = []


def err(skill, msg):
    ERRORS.append("%s: %s" % (skill, msg))


def warn(skill, msg):
    WARNINGS.append("%s: %s" % (skill, msg))


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return None, text
    fm, cur_key = {}, None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        if line.startswith("  ") and cur_key and isinstance(fm.get(cur_key), dict):
            k, _, v = line.strip().partition(":")
            fm[cur_key][k.strip()] = v.strip().strip('"')
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if v == "":
            fm[k] = {}
            cur_key = k
        else:
            fm[k] = v
            cur_key = None
    return fm, m.group(2)


def known_tokens():
    names = set()
    for t in tools.TOOLS:
        names.add(t.name)
        for p in t.params:
            names.add(p["name"])
    return names


# words that appear in backticks and look like code identifiers but are not tool or parameter names
EXTRA_TOKENS = {
    "sr_shim", "write_weights", "allow_files", "readonly", "structuredcontent", "stdio", "http",
    "voice_notes", "needs_rewrite", "watch_words", "p_value", "ratio_b_over_a", "crop_pad",
    "banned_phrases", "banned_chars", "best_times", "hours_per_week", "content_type", "content_types",
    "on_camera", "hub_primary", "retention_percent",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    dirs = sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)))
    skill_names = set(dirs)
    tokens = known_tokens() | EXTRA_TOKENS
    fact_ids = {f["id"] for f in facts.all_facts()}
    parser = cli._build_parser()
    shim = open(os.path.join(ROOT, "scripts", "sr_shim.py"), "rb").read()
    mentioned_tools = set()

    for name in dirs:
        base = os.path.join(SKILLS, name)
        md = os.path.join(base, "SKILL.md")
        if not os.path.isfile(md):
            err(name, "no SKILL.md")
            continue
        text = open(md, encoding="utf-8").read()
        fm, body = parse_frontmatter(text)
        if fm is None:
            err(name, "no frontmatter")
            continue

        # ---- spec
        if fm.get("name") != name:
            err(name, "name '%s' does not match directory" % fm.get("name"))
        if not NAME_RX.match(name) or len(name) > 64:
            err(name, "name must be lowercase letters, numbers and single hyphens, 64 characters at most")
        desc = fm.get("description", "")
        if not desc:
            err(name, "description is empty")
        if len(desc) > 1024:
            err(name, "description is %d characters, the limit is 1024" % len(desc))
        if re.search(r"[<>]", desc):
            err(name, "description contains angle brackets")
        if desc and not re.search(r"\bUse\b", desc):
            warn(name, "description does not say when to use the skill")
        if len(fm.get("compatibility", "")) > 500:
            err(name, "compatibility is over 500 characters")
        meta = fm.get("metadata")
        if meta is not None and not isinstance(meta, dict):
            err(name, "metadata must be a map of strings")
        approx_tokens = len(body) / 4.0
        if approx_tokens > 5000:
            err(name, "body is about %d tokens, keep it under 5000" % approx_tokens)
        elif approx_tokens > 3800:
            warn(name, "body is about %d tokens" % approx_tokens)
        if body.count("\n") > 500:
            err(name, "body is over 500 lines")
        for forbidden in (chr(0x2014),):
            if forbidden in text:
                err(name, "contains an em dash")

        # ---- shim
        sr = os.path.join(base, "scripts", "sr.py")
        if not os.path.isfile(sr):
            err(name, "scripts/sr.py missing, run scripts/sync_shims.py")
        elif open(sr, "rb").read() != shim:
            err(name, "scripts/sr.py differs from scripts/sr_shim.py, run scripts/sync_shims.py")

        # ---- referenced files
        for rel in set(re.findall(r"`?((?:references|assets|scripts)/[A-Za-z0-9_./-]+\.[a-z]+)`?", body)):
            if not os.path.exists(os.path.join(base, rel)):
                err(name, "references missing file %s" % rel)

        # ---- skill names
        for sk in set(re.findall(r"`(sr-[a-z0-9-]+|showrunner)`", body)):
            if sk not in skill_names:
                err(name, "mentions unknown skill `%s`" % sk)

        # ---- backticked identifiers
        for tok in set(re.findall(r"`([a-z]+(?:_[a-z]+)+)`", body)):
            if tok in tokens:
                if tok in {t.name for t in tools.TOOLS}:
                    mentioned_tools.add(tok)
                continue
            err(name, "mentions `%s`, which is not a tool or parameter" % tok)
        for t in tools.TOOLS:
            if re.search(r"\b%s\b" % re.escape(t.name), body):
                mentioned_tools.add(t.name)

        # ---- fact ids and facts_search calls
        for tok in set(re.findall(r"`([a-z0-9_.]+\.[a-z0-9_.]+)`", body)):
            if FACT_ID_RX.match(tok) and tok not in fact_ids and not any(i.startswith(tok.rstrip(".") + ".") for i in fact_ids):
                err(name, "mentions fact id `%s`, which does not exist" % tok)
        for call in re.findall(r"facts_search[^`\n]*", body):
            for k, v in re.findall(r"\b(id|platform|topic|text|status)=(\"[^\"]*\"|[^\s`)]+)", call):
                v = v.strip('"')
                if k == "id" and not any(i == v or i.startswith(v.rstrip(".") + ".") for i in fact_ids):
                    err(name, "facts_search id=%s does not exist" % v)
            for k in re.findall(r"\b([a-z_]+)=", call):
                if k not in ("id", "platform", "topic", "text", "status"):
                    err(name, "facts_search has no parameter '%s'" % k)

        # ---- CLI examples
        for block in re.findall(r"```[a-z]*\n(.*?)```", body, re.S):
            for line in block.split("\n"):
                line = line.strip()
                m = re.match(r"python scripts/sr\.py\s+(.*)$", line)
                if not m:
                    continue
                argv = shlex.split(re.sub(r"<[^>]+>", "x", m.group(1)))
                # drop a shell redirection tail
                if ">" in argv:
                    argv = argv[: argv.index(">")]
                old_err = sys.stderr
                sys.stderr = io.StringIO()
                try:
                    parser.parse_args(argv)
                except SystemExit as exc:
                    if exc.code not in (0, None):
                        err(name, "CLI example does not parse: python scripts/sr.py %s" % m.group(1))
                finally:
                    sys.stderr = old_err

    # ---- playbooks point at real skills
    for f in sorted(glob.glob(os.path.join(ROOT, "engine", "showrunner", "data", "playbooks", "*.json"))):
        pb = json.load(open(f, encoding="utf-8"))
        for step in pb["steps"]:
            if step["skill"] not in skill_names:
                err("playbook " + pb["id"], "step '%s' uses unknown skill %s" % (step["id"], step["skill"]))

    # ---- every tool is described somewhere
    for t in tools.TOOLS:
        if t.name not in mentioned_tools:
            warn("tools", "%s is not mentioned in any SKILL.md" % t.name)

    for w in WARNINGS:
        print("warning: " + w)
    for e in ERRORS:
        print("ERROR: " + e)
    if not args.quiet or ERRORS:
        print("%d skills, %d errors, %d warnings" % (len(dirs), len(ERRORS), len(WARNINGS)))
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
