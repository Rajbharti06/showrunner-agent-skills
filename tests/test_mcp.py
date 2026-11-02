import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from _paths import ENGINE, ROOT  # noqa: F401


def rpc(i, method, params=None):
    m = {"jsonrpc": "2.0", "id": i, "method": method}
    if params is not None:
        m["params"] = params
    return m


class StdioClient:
    def __init__(self, env_extra=None):
        env = dict(os.environ, SHOWRUNNER_HOME=tempfile.mkdtemp(), PYTHONPATH=ENGINE, SHOWRUNNER_SKILLS=os.path.join(ROOT, "skills"))
        env.update(env_extra or {})
        self.p = subprocess.Popen([sys.executable, "-m", "showrunner.mcp_server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=env, cwd=ENGINE)

    def call(self, msg):
        self.p.stdin.write((json.dumps(msg) + "\n").encode())
        self.p.stdin.flush()
        if "id" not in msg:
            return None
        line = self.p.stdout.readline()
        return json.loads(line)

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)
        self.p.stdout.close()
        self.p.stderr.close()


class TestStdio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = StdioClient()

    @classmethod
    def tearDownClass(cls):
        cls.c.close()

    def test_01_handshake(self):
        r = self.c.call(rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}))
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", r["result"]["capabilities"])
        self.assertEqual(r["result"]["serverInfo"]["name"], "showrunner")
        self.assertIn("intake_questions", r["result"]["instructions"])
        self.assertIsNone(self.c.call({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_02_unknown_version_gets_ours(self):
        r = self.c.call(rpc(2, "initialize", {"protocolVersion": "1999-01-01"}))
        self.assertIn(r["result"]["protocolVersion"], ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"])

    def test_03_tools_list(self):
        r = self.c.call(rpc(3, "tools/list"))
        names = {t["name"] for t in r["result"]["tools"]}
        for need in ("intake_questions", "intake_recommend", "hook_score", "text_humanize", "calendar_build", "playbook_start", "skill_get", "facts_search"):
            self.assertIn(need, names)
        for t in r["result"]["tools"]:
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertIn("readOnlyHint", t["annotations"])
            self.assertNotIn("file", t["inputSchema"]["properties"], "stdio hides file paths unless SHOWRUNNER_MCP_FILES=1")
            self.assertTrue(t["description"])

    def test_04_call_returns_text_and_structured(self):
        r = self.c.call(rpc(4, "tools/call", {"name": "hook_score", "arguments": {"text": "I sat in on 41 interviews. 33 failed the same way.\nHey guys welcome back"}}))
        res = r["result"]
        self.assertFalse(res["isError"])
        self.assertIn("HOOK SCORES", res["content"][0]["text"])
        results = res["structuredContent"]["results"]
        self.assertEqual(len(results), 2)
        self.assertGreater(results[0]["score"], results[1]["score"])

    def test_05_tool_errors_are_results_not_crashes(self):
        r = self.c.call(rpc(5, "tools/call", {"name": "hook_score", "arguments": {}}))
        self.assertTrue(r["result"]["isError"])
        self.assertIn("Nothing to read", r["result"]["content"][0]["text"])
        r = self.c.call(rpc(6, "tools/call", {"name": "caption_check", "arguments": {"text": "x", "platform": "myspace"}}))
        self.assertTrue(r["result"]["isError"])
        r = self.c.call(rpc(7, "tools/call", {"name": "hook_score", "arguments": {"text": "x", "bogus": 1}}))
        self.assertTrue(r["result"]["isError"])
        self.assertIn("Unknown parameter", r["result"]["content"][0]["text"])

    def test_06_protocol_errors(self):
        r = self.c.call(rpc(8, "tools/call", {"name": "nope", "arguments": {}}))
        self.assertEqual(r["error"]["code"], -32602)
        r = self.c.call(rpc(9, "does/not/exist"))
        self.assertEqual(r["error"]["code"], -32601)
        self.c.p.stdin.write(b"{not json\n")
        self.c.p.stdin.flush()
        r = json.loads(self.c.p.stdout.readline())
        self.assertEqual(r["error"]["code"], -32700)

    def test_07_files_are_refused(self):
        r = self.c.call(rpc(10, "tools/call", {"name": "text_detect", "arguments": {"file": "/etc/passwd"}}))
        self.assertTrue(r["result"]["isError"])
        self.assertIn("disabled", r["result"]["content"][0]["text"])

    def test_08_prompts_and_ping(self):
        r = self.c.call(rpc(11, "prompts/list"))
        self.assertIn("start", {p["name"] for p in r["result"]["prompts"]})
        r = self.c.call(rpc(12, "prompts/get", {"name": "start"}))
        self.assertIn("intake_questions", r["result"]["messages"][0]["content"]["text"])
        self.assertEqual(self.c.call(rpc(13, "ping"))["result"], {})

    def test_09_state_survives_between_calls(self):
        r = self.c.call(rpc(14, "tools/call", {"name": "profile_save", "arguments": {"profile": {"niche": "test", "stage": "zero"}}}))
        self.assertFalse(r["result"]["isError"], r)
        r = self.c.call(rpc(15, "tools/call", {"name": "profile_get", "arguments": {}}))
        self.assertEqual(r["result"]["structuredContent"]["profile"]["niche"], "test")

    def test_10_utf8_roundtrip(self):
        r = self.c.call(rpc(16, "tools/call", {"name": "text_detect", "arguments": {"text": "Naam Raj hai. Yeh ek test hai — हिन्दी भी chalega. Dekho, kitna acha hai."}}))
        self.assertFalse(r["result"]["isError"])


class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ENGINE)
        os.environ["SHOWRUNNER_HOME"] = tempfile.mkdtemp()
        from showrunner import mcp_server
        cls.ms = mcp_server
        cls.token = "t0ken"
        srv = mcp_server.Server(allow_files=False, readonly=True, expose_stateful=False)
        cls.httpd = mcp_server.ThreadingHTTPServer(("127.0.0.1", 0), mcp_server.make_handler(srv, "/mcp/abc", cls.token, []))
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def post(self, body, path="/mcp/abc", token="t0ken", headers=None):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            return e.code, None

    def test_auth_and_path(self):
        self.assertEqual(self.post(rpc(1, "ping"), token=None)[0], 401)
        self.assertEqual(self.post(rpc(1, "ping"), token="wrong")[0], 401)
        self.assertEqual(self.post(rpc(1, "ping"), path="/mcp")[0], 404)
        self.assertEqual(self.post(rpc(1, "ping"), headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.post(rpc(1, "ping"))[0], 200)

    def test_notification_gets_202(self):
        self.assertEqual(self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})[0], 202)

    def test_read_only_surface(self):
        st, r = self.post(rpc(2, "tools/list"))
        names = {t["name"] for t in r["result"]["tools"]}
        self.assertIn("hook_score", names)
        self.assertNotIn("profile_save", names)
        self.assertNotIn("playbook_start", names)
        for t in r["result"]["tools"]:
            self.assertNotIn("file", t["inputSchema"]["properties"])
            self.assertTrue(t["annotations"]["readOnlyHint"])
        st, r = self.post(rpc(3, "tools/call", {"name": "profile_save", "arguments": {"profile": {"niche": "x"}}}))
        self.assertEqual(r["error"]["code"], -32602)

    def test_calls_work_over_http(self):
        st, r = self.post(rpc(4, "tools/call", {"name": "title_score", "arguments": {"text": "How I Got 3 Job Offers in 30 Days", "keyword": "job offers"}}))
        self.assertEqual(st, 200)
        self.assertFalse(r["result"]["isError"])
        self.assertEqual(r["result"]["structuredContent"]["titles"][0]["chars"], 33)

    def test_calibrate_cannot_write_in_readonly(self):
        rows = "account,views,hook\n" + "\n".join("a,%d,hook number %d" % (100 + i * 37, i) for i in range(40))
        st, r = self.post(rpc(5, "tools/call", {"name": "calibrate_run", "arguments": {"text": rows, "write_weights": True}}))
        self.assertTrue(r["result"]["isError"])
        self.assertIn("read-only", r["result"]["content"][0]["text"])

    def test_get_is_405(self):
        req = urllib.request.Request("http://127.0.0.1:%d/mcp/abc" % self.port, headers={"Authorization": "Bearer t0ken"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(cm.exception.code, 405)


if __name__ == "__main__":
    unittest.main()
