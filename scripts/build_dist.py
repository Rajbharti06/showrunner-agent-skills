#!/usr/bin/env python3
"""Build upload-ready zip files into dist/.

    python scripts/build_dist.py

Produces:
  dist/skills/<name>.zip           one skill with the engine bundled, for ChatGPT's Skills upload
                                   or any agent that takes a zipped skill folder
  dist/showrunner-all-skills.zip   every skill plus the engine, in the repository layout
  dist/SHA256SUMS                  checksums

The zips are deterministic on one setup: sorted entries, fixed timestamps and permissions. The files inside are
identical everywhere, but the compressed bytes (and so SHA256SUMS) can differ between Python and zlib builds.
"""
import hashlib
import os
import sys
import zipfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SKILLS = os.path.join(ROOT, "skills")
ENGINE = os.path.join(ROOT, "engine", "showrunner")
DIST = os.path.join(ROOT, "dist")
STAMP = (2026, 1, 1, 0, 0, 0)


def files_under(base):
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "packs"))  # local add-on packs never ship
        for fn in sorted(files):
            if fn.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, fn)
            yield full, os.path.relpath(full, base).replace(os.sep, "/")


def add(z, full, arc):
    info = zipfile.ZipInfo(arc, STAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if arc.endswith(".py") and "/scripts/" in arc else 0o644
    info.external_attr = mode << 16
    with open(full, "rb") as fh:
        z.writestr(info, fh.read())


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def main() -> int:
    os.makedirs(os.path.join(DIST, "skills"), exist_ok=True)
    names = sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))
    outputs = []
    for n in names:
        out = os.path.join(DIST, "skills", n + ".zip")
        with zipfile.ZipFile(out, "w") as z:
            for full, rel in files_under(os.path.join(SKILLS, n)):
                add(z, full, "%s/%s" % (n, rel))
            for full, rel in files_under(ENGINE):
                add(z, full, "%s/scripts/_engine/showrunner/%s" % (n, rel))
        outputs.append(out)

    allzip = os.path.join(DIST, "showrunner-all-skills.zip")
    with zipfile.ZipFile(allzip, "w") as z:
        for n in names:
            for full, rel in files_under(os.path.join(SKILLS, n)):
                add(z, full, "skills/%s/%s" % (n, rel))
        for full, rel in files_under(ENGINE):
            add(z, full, "engine/showrunner/%s" % rel)
        for extra in ("README.md", "LICENSE", "install.py", "examples"):
            p = os.path.join(ROOT, extra)
            if os.path.isdir(p):
                for full, rel in files_under(p):
                    add(z, full, "%s/%s" % (extra, rel))
            elif os.path.isfile(p):
                add(z, p, extra)
    outputs.append(allzip)

    with open(os.path.join(DIST, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as fh:
        for o in outputs:
            fh.write("%s  %s\n" % (sha(o), os.path.relpath(o, DIST).replace(os.sep, "/")))
    print("built %d zips in %s" % (len(outputs), DIST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
