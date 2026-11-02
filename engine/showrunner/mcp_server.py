"""Showrunner as an MCP server, so Claude, ChatGPT, Cursor and other hosts can call the engine.

    python -m showrunner.mcp_server                  # stdio: Claude Desktop, Claude Code, Cursor, Codex
    python -m showrunner.mcp_server --http 8765      # HTTP on 127.0.0.1:8765/mcp (read-only by default)

Zero dependencies. Implements the parts of MCP that tool servers need: initialize, ping,
tools/list, tools/call, prompts/list, prompts/get. Logs go to stderr, never stdout.

Safety stance:
  * The server reads text you pass it. It does not scrape, post, or open the network.
  * stdio mode may keep your profile and playbook state in SHOWRUNNER_HOME (default ~/.showrunner).
    Reading arbitrary files is OFF unless you set SHOWRUNNER_MCP_FILES=1.
  * HTTP mode is read-only and cannot read files or keep state unless you pass --stateful.
    It has no OAuth. If you expose it beyond your own machine, use --token and a private tunnel.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import __version__, tools

SUPPORTED = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
SERVER_NAME = "showrunner"

INSTRUCTIONS = (
    "Showrunner helps a person grow a channel on Instagram, YouTube, TikTok, Facebook, LinkedIn, X or Threads. "
    "It writes, scores, plans and analyses. It never posts, and it never invents numbers.\n"
    "Start: if you do not yet know what the person wants to create, for whom, and where, call intake_questions and ask "
    "them one or two at a time. Then call intake_recommend. Do not recommend a platform before you have their answers.\n"
    "Skills: call skill_list, then skill_get('showrunner') for the conductor, and follow it. Each skill names the tools "
    "it uses. Playbooks (playbook_list) chain skills into a plan with approval gates: never skip a gate, and never "
    "mark a 'human' step done for the person.\n"
    "Honesty: hook, title and caption scores are heuristics that have not been validated against views. Say so when "
    "you report them. Use facts_search for platform rules instead of stating them from memory, and tell the person "
    "how old the fact is. Do not invent analytics: if a step needs their numbers, ask for them."
)

PROMPTS = {
    "start": {
        "description": "Start here: find out what to make, for whom and where, then get a plan.",
        "text": "Use Showrunner. Read the conductor with skill_get('showrunner'), then run the intake: call intake_questions and ask me one or two questions at a time. When you have my answers, call intake_recommend and walk me through the result. Do not post anything for me.",
    },
    "weekly": {
        "description": "Run this week's content sprint.",
        "text": "Use Showrunner. Start or resume the weekly-sprint playbook (playbook_start or playbook_next). Work step by step, show me each result, and wait for my yes before you move on.",
    },
    "monthly": {
        "description": "Monthly review: what worked, what to change, next month's plan.",
        "text": "Use Showrunner. Start the monthly-review playbook. Ask me for my analytics exports where a step needs them. Do not guess numbers.",
    },
}


def _log(msg: str) -> None:
    print("[showrunner-mcp] " + msg, file=sys.stderr, flush=True)


class Server:
    def __init__(self, allow_files: bool, readonly: bool, expose_stateful: bool):
        self.allow_files = allow_files
        self.readonly = readonly
        self.expose_stateful = expose_stateful

    # ---- tool surface
    def _visible(self) -> List[tools.Tool]:
        return [t for t in tools.TOOLS if self.expose_stateful or not t.stateful]

    def _tool_def(self, t: tools.Tool) -> Dict[str, Any]:
        return {
            "name": t.name,
            "title": t.summary,
            "description": t.description,
            "inputSchema": t.schema(self.allow_files),
            "annotations": {
                "title": t.summary,
                "readOnlyHint": not t.stateful,
                "destructiveHint": False,
                "idempotentHint": not t.stateful,
                "openWorldHint": False,
            },
        }

    # ---- dispatch
    def handle(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            return self._err(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid request")
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}
        is_note = "id" not in msg
        if method is None:                    # a response from the client: nothing to do
            return None
        try:
            if method == "initialize":
                want = params.get("protocolVersion")
                ver = want if want in SUPPORTED else SUPPORTED[0]
                result: Dict[str, Any] = {
                    "protocolVersion": ver,
                    "capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "title": "Showrunner", "version": __version__},
                    "instructions": INSTRUCTIONS,
                }
            elif method in ("notifications/initialized", "notifications/cancelled") or method.startswith("notifications/"):
                return None
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": [self._tool_def(t) for t in self._visible()]}
            elif method == "tools/call":
                result = self._call(params)
            elif method == "prompts/list":
                result = {"prompts": [{"name": k, "description": v["description"]} for k, v in PROMPTS.items()]}
            elif method == "prompts/get":
                name = params.get("name")
                if name not in PROMPTS:
                    return self._err(mid, -32602, "Unknown prompt: %s" % name)
                result = {"description": PROMPTS[name]["description"],
                          "messages": [{"role": "user", "content": {"type": "text", "text": PROMPTS[name]["text"]}}]}
            elif method in ("resources/list", "resources/templates/list"):
                result = {"resources": []} if method == "resources/list" else {"resourceTemplates": []}
            else:
                if is_note:
                    return None
                return self._err(mid, -32601, "Method not found: %s" % method)
        except _ParamError as e:
            return self._err(mid, -32602, str(e))
        except Exception as e:                                  # never let one bad call kill the server
            _log("internal error: %r" % (e,))
            return self._err(mid, -32603, "Internal error: %s" % type(e).__name__)
        if is_note:
            return None
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def _call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str) or name not in {t.name for t in self._visible()}:
            raise _ParamError("Unknown tool: %s" % name)
        if not isinstance(args, dict):
            raise _ParamError("arguments must be an object")
        res = tools.run(name, args, allow_files=self.allow_files, readonly=self.readonly)
        if res["ok"]:
            data = res["data"] if isinstance(res["data"], dict) else {"result": res["data"]}
            return {"content": [{"type": "text", "text": res["text"]}], "structuredContent": data, "isError": False}
        return {"content": [{"type": "text", "text": res["error"]}], "isError": True}

    @staticmethod
    def _err(mid: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


class _ParamError(Exception):
    pass


# ------------------------------------------------------------------ stdio

def serve_stdio(server: Server) -> None:
    _log("stdio ready (showrunner %s, files %s)" % (__version__, "on" if server.allow_files else "off"))
    rd, wr = sys.stdin.buffer, sys.stdout.buffer
    for raw in iter(rd.readline, b""):
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            out: Any = server._err(None, -32700, "Parse error")
        else:
            if isinstance(msg, list):
                outs = [r for r in (server.handle(m) for m in msg) if r is not None]
                out = outs or None
            else:
                out = server.handle(msg)
        if out is not None:
            wr.write((json.dumps(out, ensure_ascii=False) + "\n").encode("utf-8"))
            wr.flush()


# ------------------------------------------------------------------ http

def make_handler(server: Server, path: str, token: Optional[str], origins: List[str]):
    class H(BaseHTTPRequestHandler):
        server_version = "Showrunner/" + __version__
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *a: Any) -> None:
            _log("%s - %s" % (self.address_string(), fmt % a))

        def _send(self, code: int, body: Optional[Dict[str, Any]] = None, extra: Optional[Dict[str, str]] = None) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else b""
            self.send_response(code)
            if body is not None:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if data:
                self.wfile.write(data)

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True                       # server-to-server callers (ChatGPT, curl) send none
            host = urlparse(origin).hostname or ""
            return origin in origins or host in ("localhost", "127.0.0.1", "::1")

        def _auth_ok(self) -> bool:
            if not token:
                return True
            return self.headers.get("Authorization", "") == "Bearer " + token

        def _gate(self) -> bool:
            if urlparse(self.path).path.rstrip("/") != path.rstrip("/"):
                self._send(404, {"error": "not found"})
                return False
            if not self._origin_ok():
                self._send(403, {"error": "origin not allowed"})
                return False
            if not self._auth_ok():
                self._send(401, {"error": "missing or wrong bearer token"}, {"WWW-Authenticate": "Bearer"})
                return False
            return True

        def do_OPTIONS(self) -> None:
            self._send(204, None, {"Allow": "POST, OPTIONS"})

        def do_GET(self) -> None:
            if self._gate():
                self._send(405, {"error": "this server does not open event streams; use POST"}, {"Allow": "POST"})

        def do_DELETE(self) -> None:
            if self._gate():
                self._send(405, {"error": "no sessions to close"}, {"Allow": "POST"})

        def do_POST(self) -> None:
            if not self._gate():
                return
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                n = 0
            if n <= 0 or n > 2_000_000:
                self._send(413 if n > 0 else 400, {"error": "body missing or over 2 MB"})
                return
            try:
                msg = json.loads(self.rfile.read(n).decode("utf-8"))
            except ValueError:
                self._send(400, Server._err(None, -32700, "Parse error"))
                return
            if isinstance(msg, list):
                outs = [r for r in (server.handle(m) for m in msg) if r is not None]
                if not outs:
                    self._send(202)
                else:
                    self._send(200, outs)  # type: ignore[arg-type]
                return
            out = server.handle(msg)
            if out is None:
                self._send(202)
            else:
                self._send(200, out)

    return H


def serve_http(server: Server, host: str, port: int, path: str, token: Optional[str], origins: List[str]) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(server, path, token, origins))
    _log("http ready at http://%s:%d%s  (read-only=%s, token=%s)" % (host, port, path, server.readonly, "on" if token else "off"))
    if host not in ("127.0.0.1", "localhost", "::1") and not token:
        _log("WARNING: listening beyond localhost with no token. Anyone who can reach this port can call the tools.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="showrunner-mcp", description="Showrunner MCP server (stdio by default).")
    ap.add_argument("--http", type=int, metavar="PORT", help="Serve streamable HTTP on this port instead of stdio.")
    ap.add_argument("--host", default="127.0.0.1", help="Bind address for --http (default 127.0.0.1).")
    ap.add_argument("--path", default="/mcp", help="URL path for --http. Use a long random path as a poor man's secret.")
    ap.add_argument("--token", default=os.environ.get("SHOWRUNNER_TOKEN"), help="Require 'Authorization: Bearer TOKEN' (or set SHOWRUNNER_TOKEN).")
    ap.add_argument("--allow-origin", action="append", default=[], help="Extra allowed Origin for browser callers. Repeatable.")
    ap.add_argument("--stateful", action="store_true", help="HTTP only: allow tools that save a profile, runs and experiments on this machine. Single user only.")
    args = ap.parse_args(argv)
    if args.http:
        if not args.path.startswith("/"):
            args.path = "/" + args.path
        srv = Server(allow_files=False, readonly=not args.stateful, expose_stateful=args.stateful)
        serve_http(srv, args.host, args.http, args.path, args.token, args.allow_origin)
    else:
        srv = Server(allow_files=os.environ.get("SHOWRUNNER_MCP_FILES") == "1", readonly=False, expose_stateful=True)
        serve_stdio(srv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
