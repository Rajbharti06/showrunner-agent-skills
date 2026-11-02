#!/usr/bin/env python3
"""Keep the repository's own writing free of the habits it warns people about.

    python scripts/lint_prose.py

Fails if an em dash (U+2014, or &mdash;) appears in any text file, except the few files that
need the character to do their job (the humanizer, its tests, the sample draft that demos it).
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKIP_DIRS = {".git", "__pycache__", "dist", "node_modules", ".tmp", ".venv", "build", ".pytest_cache"}
EXTS = {".md", ".txt", ".py", ".json", ".toml", ".yml", ".yaml", ".cfg", ".csv", ".srt", ".ics", ".html"}
ALLOW = {
    "scripts/lint_prose.py",
    "engine/showrunner/humanize.py",
    "engine/showrunner/util.py",
    "engine/showrunner/data/slop.json",
    "examples/draft.txt",
    "tests/test_engine.py",
    "tests/test_mcp.py",
    "skills/sr-humanize/references/slop-list.md",
}
PATTERN = re.compile(chr(0x2014) + "|&mdash;|" + chr(92) * 2 + "u2014", re.I)


def main() -> int:
    bad = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in EXTS:
                continue
            path = os.path.join(base, fn)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if rel in ALLOW:
                continue
            try:
                text = open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(text.split("\n"), 1):
                if PATTERN.search(line):
                    bad.append("%s:%d: %s" % (rel, n, line.strip()[:90]))
    for b in bad:
        print(b)
    print("prose lint: %s" % ("%d problem(s)" % len(bad) if bad else "clean"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
