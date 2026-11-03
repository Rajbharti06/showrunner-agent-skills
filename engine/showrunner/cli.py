"""Command line for Showrunner. Generated from the same tool registry the MCP server uses.

    python -m showrunner                     # what is here
    python -m showrunner questions           # the intake questions
    python -m showrunner hook "I lost 40 pounds in 90 days, here is the one thing I changed"
    cat draft.txt | python -m showrunner humanize
    python -m showrunner outliers --file posts.csv
"""
from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import tools
from .util import have_stdout_utf8, jdump

GROUP_ORDER = [
    ("START HERE", ["questions", "intake", "doctor"]),
    ("MAKE", ["hook", "hook-shapes", "title", "beats", "caption", "ideas", "matrix"]),
    ("POLISH", ["humanize", "detect"]),
    ("STUDY WHAT WORKS", ["outliers", "retention", "subtitles", "rechunk", "clips"]),
    ("PLAN", ["calendar", "playbook list", "playbook show", "playbook start", "playbook next", "playbook done", "playbook status"]),
    ("LEARN FROM YOUR NUMBERS", ["exp new", "exp log", "exp review", "calibrate"]),
    ("REFERENCE", ["facts", "stale", "profile get", "profile save", "skills", "skill"]),
]


def _flag(name: str) -> str:
    return "--" + name.replace("_", "-")


_YES = {"yes", "y", "true", "1", "on"}
_NO = {"no", "n", "false", "0", "off"}


def _normalise_bools(argv: List[str]) -> List[str]:
    """Let boolean flags take a word as well: --on-camera no, --on-camera=yes. Agents write these often.

    A following word is only taken as the value when it is a yes or no word, so `--skip voice` still works."""
    flags = {_flag(p["name"]) for t in tools.TOOLS for p in t.params if p["type"] == "boolean" and not p["positional"]}
    out: List[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        name, eq, val = tok.partition("=")
        if name in flags:
            if not eq and i + 1 < len(argv) and argv[i + 1].lower() in _YES | _NO:
                val = argv[i + 1]
                i += 1
            if val.lower() in _NO:
                tok = "--no-" + name[2:]
            elif val.lower() in _YES or not eq:
                tok = name
        out.append(tok)
        i += 1
    return out


class _Parser(argparse.ArgumentParser):
    def parse_known_args(self, args=None, namespace=None):  # type: ignore[override]
        args = sys.argv[1:] if args is None else list(args)
        return super().parse_known_args(_normalise_bools(args), namespace)


def _read_stdin(timeout: float = 10.0) -> str:
    """Read piped input, but never hang a harness whose stdin is open and silent."""
    box: List[str] = []

    def work() -> None:
        try:
            box.append(sys.stdin.read())
        except Exception:
            box.append("")

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout)
    return box[0].lstrip("﻿") if box else ""


def _build_parser() -> argparse.ArgumentParser:
    ap = _Parser(prog="showrunner", add_help=True, description="Showrunner: orchestrate content that grows channels. Nothing here posts for you.")
    ap.add_argument("--version", action="version", version="showrunner " + tools.VERSION)
    sub = ap.add_subparsers(dest="cmd", metavar="<command>")
    groups: Dict[str, Any] = {}
    for t in tools.TOOLS:
        parts = t.cli.split()
        if len(parts) == 1:
            sp = sub.add_parser(parts[0], help=t.summary, description=t.description)
        else:
            if parts[0] not in groups:
                gp = sub.add_parser(parts[0], help="%s commands" % parts[0])
                groups[parts[0]] = gp.add_subparsers(dest="sub", metavar="<action>")
                gp.set_defaults(_group=gp)
            sp = groups[parts[0]].add_parser(parts[1], help=t.summary, description=t.description)
        sp.set_defaults(_tool=t.name)
        for p in t.params:
            if p["positional"]:
                sp.add_argument(p["name"], nargs="?", default=None, help=p["help"] + (" Use - to read stdin." if p.get("bulk") else ""))
            elif p["type"] == "boolean":
                sp.add_argument(_flag(p["name"]), dest=p["name"], action=argparse.BooleanOptionalAction, default=None, help=p["help"])
            else:
                kw: Dict[str, Any] = {"dest": p["name"], "default": None, "metavar": p["name"].upper()[:14]}
                if p["enum"] and p["type"] == "string":
                    kw["choices"] = p["enum"]
                    kw["metavar"] = "{%s}" % "|".join(p["enum"]) if len(p["enum"]) <= 6 else kw["metavar"]
                hlp = p["help"]
                if p["default"] is not None:
                    hlp += " (default: %s)" % p["default"]
                if p["type"] == "string_list":
                    hlp += " Comma separated."
                if p["type"] == "object":
                    hlp += " JSON, or @path/to/file.json."
                sp.add_argument(_flag(p["name"]), help=hlp, **kw)
        sp.add_argument("--json", dest="_json", action="store_true", help="Print the structured result as JSON.")
    return ap


def _overview() -> str:
    out = ["Showrunner %s: an engine behind the Showrunner skills. Nothing here posts for you." % tools.VERSION, ""]
    for head, names in GROUP_ORDER:
        out.append(head)
        for n in names:
            t = tools.BY_CLI.get(n)
            if t:
                out.append("  %-18s %s" % (n, t.summary))
        out.append("")
    out.append("New here? Run:  python -m showrunner questions")
    out.append("Any command takes --help, --json, and reads piped text (or --file).")
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    have_stdout_utf8()
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = _build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "_tool", None):
        grp = getattr(args, "_group", None)
        if grp is not None:
            grp.print_help()
            return 0
        print(_overview())
        return 0
    tool = tools.BY_NAME[args._tool]
    params: Dict[str, Any] = {}
    for p in tool.params:
        v = getattr(args, p["name"], None)
        if v is None:
            continue
        if p["type"] == "object" and isinstance(v, str) and v.startswith("@"):
            path = Path(v[1:]).expanduser()
            if not path.exists():
                print("error: file not found: %s" % path, file=sys.stderr)
                return 2
            v = path.read_text(encoding="utf-8-sig")
        params[p["name"]] = v
    bulk = next((p for p in tool.params if p.get("bulk")), None)
    if bulk is not None:
        val = params.get(bulk["name"])
        if val == "-":
            params[bulk["name"]] = _read_stdin()
        elif val is None and "file" not in params and not sys.stdin.isatty():
            piped = _read_stdin()
            if piped.strip():
                params[bulk["name"]] = piped
        if not params.get(bulk["name"]) and "file" not in params and tool.cli not in ("questions",):
            print("error: nothing to read. Pass the text, use --file PATH, or pipe it in.\n(Run: showrunner %s --help)" % tool.cli, file=sys.stderr)
            return 2
    res = tools.run(tool.name, params, allow_files=True, readonly=False)
    if not res["ok"]:
        print("error: " + res["error"], file=sys.stderr)
        return 1
    print(jdump(res["data"]) if getattr(args, "_json", False) else res["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
