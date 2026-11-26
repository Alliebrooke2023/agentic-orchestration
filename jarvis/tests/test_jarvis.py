# python -m unittest discover -s jarvis/tests
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jarvis  # noqa: E402


def call(url, body=None, origin=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None)
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        pkg = cls.tmp / "swarm"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "__main__.py").write_text("import sys; print('FAKE', ' '.join(sys.argv[1:]))")
        cls.app = jarvis.App(cls.tmp, cooldown=0)
        cls.srv = jarvis.serve(cls.app, 0)
        port = cls.srv.server_address[1]
        cls.srv.RequestHandlerClass = jarvis.make_handler(cls.app, port)
        cls.base, cls.origin = f"http://127.0.0.1:{port}", f"http://127.0.0.1:{port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_page_and_config(self):
        self.assertEqual(call(self.base + "/")[0], 200)
        self.assertEqual(call(self.base + "/gestures.js")[0], 200)
        code, body = call(self.base + "/config")
        self.assertEqual(json.loads(body)["commands"]["fist"], "health report")

    def test_traversal_blocked(self):
        for p in ["/jarvis.py", "/../swarm/swarm/core.py", "/vendor/../jarvis.py", "/%2e%2e/README.md"]:
            self.assertEqual(call(self.base + p)[0], 404, p)

    def test_cmd_runs_whitelisted(self):
        code, body = call(self.base + "/cmd", {"gesture": "fist"}, self.origin)
        self.assertEqual(code, 200)
        self.assertIn("FAKE health report", json.loads(body)["output"])

    def test_unmapped_and_bad_origin(self):
        self.assertEqual(call(self.base + "/cmd", {"gesture": "rm -rf"}, self.origin)[0], 400)
        self.assertEqual(call(self.base + "/cmd", {"gesture": "fist"}, "http://evil.example")[0], 403)
        self.assertEqual(call(self.base + "/cmd", {"gesture": "fist"})[0], 403)

    def test_cooldown(self):
        app = jarvis.App(self.tmp, cooldown=60)
        self.assertEqual(app.run("fist")[0], 200)
        self.assertEqual(app.run("fist")[0], 429)

    def test_find_swarm(self):
        self.assertEqual(jarvis.find_swarm(str(self.tmp)), self.tmp.resolve())


if __name__ == "__main__":
    unittest.main()
