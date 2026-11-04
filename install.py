#!/usr/bin/env python3
"""Install the Showrunner skills into an agent's skills folder.

    python install.py --target claude              ~/.claude/skills
    python install.py --target claude --scope project   ./.claude/skills
    python install.py --target cursor              ~/.cursor/skills
    python install.py --target gemini              ~/.gemini/skills
    python install.py --target agents              ~/.agents/skills (shared folder several agents read)
    python install.py --dest /any/folder           anywhere else
    python install.py --list                       show what would be installed

Each installed skill carries its own copy of the engine in scripts/_engine, so it works on its own.
Needs Python 3.9 or newer and nothing else. Existing copies of the same skills are replaced.
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.join(ROOT, "skills")
ENGINE = os.path.join(ROOT, "engine", "showrunner")

TARGETS = {
    "claude": (".claude", "skills"),
    "cursor": (".cursor", "skills"),
    "gemini": (".gemini", "skills"),
    "agents": (".agents", "skills"),
}


def ignore(_dir, names):
    # data/packs holds local add-on packs; they are never copied out with the free skills
    return [n for n in names if n in ("__pycache__", "packs") or n.endswith(".pyc")]


def skill_names():
    return sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def main() -> int:
    ap = argparse.ArgumentParser(description="Install the Showrunner skills.")
    ap.add_argument("--target", choices=sorted(TARGETS), help="Which agent's folder to use.")
    ap.add_argument("--scope", choices=["user", "project"], default="user", help="Your home folder, or the current folder.")
    ap.add_argument("--dest", help="Install into this folder instead.")
    ap.add_argument("--only", help="Comma separated skill names to install.")
    ap.add_argument("--list", action="store_true", help="List the skills and exit.")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen.")
    a = ap.parse_args()

    names = skill_names()
    if a.only:
        want = [x.strip() for x in a.only.split(",") if x.strip()]
        missing = [x for x in want if x not in names]
        if missing:
            sys.stderr.write("No such skill: %s\n" % ", ".join(missing))
            return 2
        names = want
        if "showrunner" not in names:
            print("Note: the conductor skill 'showrunner' is not in this list, so the guided flow will not start.")
    if a.list:
        for n in names:
            print(n)
        return 0

    if a.dest:
        dest = os.path.abspath(os.path.expanduser(a.dest))
    elif a.target:
        base = os.path.expanduser("~") if a.scope == "user" else os.getcwd()
        dest = os.path.join(base, *TARGETS[a.target])
    else:
        ap.error("choose --target or --dest")
        return 2

    print("Installing %d skills into %s" % (len(names), dest))
    if a.dry_run:
        return 0
    os.makedirs(dest, exist_ok=True)
    for n in names:
        out = os.path.join(dest, n)
        if os.path.isdir(out):
            shutil.rmtree(out)
        shutil.copytree(os.path.join(SKILLS, n), out, ignore=ignore)
        shutil.copytree(ENGINE, os.path.join(out, "scripts", "_engine", "showrunner"), ignore=ignore)
    if "showrunner" in names:
        print("Done. Start a new session in your agent and say: I want to grow my channel.")
    else:
        print("Done. Start a new session in your agent.")
    print("Check the install any time with: " + check_command(dest, names))
    return 0


def check_command(dest, names):
    """The doctor command for an installed skill, quoted so it survives spaces (C:\\Users\\Jane Doe\\...)."""
    skill = "showrunner" if "showrunner" in names else names[0]
    return 'python "%s" doctor' % os.path.join(dest, skill, "scripts", "sr.py")


if __name__ == "__main__":
    sys.exit(main())
