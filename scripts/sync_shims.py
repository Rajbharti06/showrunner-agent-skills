#!/usr/bin/env python3
"""Copy scripts/sr_shim.py into every skill as scripts/sr.py.

    python scripts/sync_shims.py           copy
    python scripts/sync_shims.py --check   exit 1 if any copy differs (used in CI)
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(ROOT, "scripts", "sr_shim.py")
SKILLS = os.path.join(ROOT, "skills")


def main() -> int:
    check = "--check" in sys.argv
    with open(SRC, "rb") as fh:
        want = fh.read()
    bad = []
    for name in sorted(os.listdir(SKILLS)):
        d = os.path.join(SKILLS, name)
        if not os.path.isfile(os.path.join(d, "SKILL.md")):
            continue
        dest = os.path.join(d, "scripts", "sr.py")
        have = None
        if os.path.exists(dest):
            with open(dest, "rb") as fh:
                have = fh.read()
        if have == want:
            continue
        bad.append(name)
        if not check:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(want)
            os.chmod(dest, 0o755)
    if check:
        if bad:
            sys.stderr.write("Shim out of date in: %s\nRun python scripts/sync_shims.py\n" % ", ".join(bad))
            return 1
        print("shims in sync")
        return 0
    print("updated %d skill(s)" % len(bad) if bad else "shims already in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
