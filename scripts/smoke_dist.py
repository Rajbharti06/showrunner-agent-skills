#!/usr/bin/env python3
"""Unzip one built skill the way an upload would, and prove it runs with nothing else installed.

    python scripts/build_dist.py && python scripts/smoke_dist.py
"""
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def run(py, args, env):
    return subprocess.run([sys.executable, py] + args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, cwd=tempfile.gettempdir())


def main() -> int:
    zpath = os.path.join(ROOT, "dist", "skills", "sr-caption.zip")
    if not os.path.isfile(zpath):
        sys.stderr.write("dist/skills/sr-caption.zip not found. Run python scripts/build_dist.py first.\n")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
        py = os.path.join(tmp, "sr-caption", "scripts", "sr.py")
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "SHOWRUNNER_ENGINE")}
        env["SHOWRUNNER_HOME"] = os.path.join(tmp, "home")
        checks = [
            (["doctor"], "fact data check  ok"),
            (["caption", "--platform", "instagram", "-"], None),
        ]
        for args, expect in checks:
            if args[-1] == "-":
                r = subprocess.run([sys.executable, py] + args, input="I spent 3 months on one mistake.\n\nSave this.\n",
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=tmp)
            else:
                r = run(py, args, env)
            if r.returncode != 0 or (expect and expect not in r.stdout):
                sys.stderr.write("FAILED: %s\n%s\n%s\n" % (" ".join(args), r.stdout, r.stderr))
                return 1
    print("bundled skill runs on its own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
