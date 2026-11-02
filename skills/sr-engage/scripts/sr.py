#!/usr/bin/env python3
"""Runs the Showrunner engine from inside a skill. The same file ships in every skill.

It looks for the engine in this order:
  1. the folder named by $SHOWRUNNER_ENGINE
  2. ./_engine next to this file (bundled when a skill is downloaded as a zip)
  3. ../../../engine (this repository's layout)
  4. a pip-installed `showrunner` package

Usage:  python scripts/sr.py <command> [options]      (python scripts/sr.py --help)
Needs Python 3.9 or newer. No other dependencies.
"""
import os
import sys

if sys.version_info < (3, 9):
    sys.stderr.write("Showrunner needs Python 3.9 or newer (this is %d.%d).\n" % sys.version_info[:2])
    sys.exit(3)

_here = os.path.dirname(os.path.abspath(__file__))
for _cand in (
    os.environ.get("SHOWRUNNER_ENGINE"),
    os.path.join(_here, "_engine"),
    os.path.normpath(os.path.join(_here, "..", "..", "..", "engine")),
):
    if _cand and os.path.isdir(os.path.join(_cand, "showrunner")):
        sys.path.insert(0, _cand)
        break

# Let `skills` and `doctor` find the sibling skills wherever this skill was installed.
os.environ.setdefault("SHOWRUNNER_SKILLS", os.path.normpath(os.path.join(_here, "..", "..")))

try:
    from showrunner.cli import main
except ImportError:
    sys.stderr.write(
        "Could not find the Showrunner engine.\n"
        "Fix one of: set SHOWRUNNER_ENGINE to the repo's engine folder, run `pip install .` from the repository root, "
        "or download the skill zip that bundles it.\n"
    )
    sys.exit(3)

if __name__ == "__main__":
    sys.exit(main())
