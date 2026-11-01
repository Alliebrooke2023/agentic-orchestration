import json
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swarm.core import Swarm
from swarm.llm import Offline
from swarm.ollama_ops import OllamaOps
from swarm.sunshine_ops import SunshineOps

PULLED = []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send({"version": "0.9"} if "version" in self.path else
                   {"models": [{"name": "llama3.2:1b", "size": 1.3e9}]})

    def do_POST(self):
        n = int(self.headers["Content-Length"])
        PULLED.append(json.loads(self.rfile.read(n))["model"])
        self._send({"status": "success"})


class Ollama(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.host = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_status_pull_fit(self):
        o = OllamaOps(self.host, ram_gb=lambda: 8)
        self.assertIn("UP", o.run("ollama status"))
        self.assertIn("llama3.2:1b", o.run("ollama status"))
        self.assertEqual(o.run("pull qwen2.5:0.5b"), "pulled qwen2.5:0.5b")
        self.assertEqual(PULLED, ["qwen2.5:0.5b"])
        self.assertIn("recommend", o.run("ollama ram fit"))

    def test_down_and_low_ram(self):
        self.assertIn("DOWN", OllamaOps("http://127.0.0.1:1", ram_gb=lambda: 0.2).run("ollama"))
        self.assertIn("nothing fits", OllamaOps("http://127.0.0.1:1", ram_gb=lambda: 0.2).run("ram"))


class Sunshine(unittest.TestCase):
    def test_states(self):
        conf = Path(tempfile.mkdtemp()) / "sunshine.conf"
        conf.write_text("sunshine_name = Compaq\nsecret = x\n")
        before = conf.read_text()
        up = SunshineOps(lambda c: "STATE : 4 RUNNING" if c[0] == "sc" else "active",
                         lambda p: True, [str(conf)])
        out = up.run("sunshine status")
        self.assertIn("open", out)
        self.assertIn("sunshine_name=Compaq", out)
        self.assertNotIn("secret", out)
        self.assertEqual(conf.read_text(), before)
        down = SunshineOps(lambda c: "inactive", lambda p: False, ["/nope"]).run("sunshine")
        self.assertIn("Run yourself", down)
        self.assertIn("no sunshine.conf", down)


class Stack(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(Path(__file__).resolve().parents[1] / "agents", self.d / "agents")
        self.s = Swarm(self.d, llm=Offline())

    def test_routing(self):
        for task, agent in [("ollama status", "ollama-ops"), ("sunshine status", "sunshine-ops"),
                            ("build stack media", "stack-ops"), ("stack status", "stack-ops"),
                            ("blueprint a media stack", "blueprinter")]:
            self.assertEqual(self.s.router.pick(task), agent, task)

    def test_learning_does_not_hijack_routing(self):
        self.s.do("ollama status")
        for task, agent in [("sunshine status", "sunshine-ops"), ("stack status", "stack-ops")]:
            self.assertEqual(self.s.do(task)[0], agent)

    def test_build_no_overwrite(self):
        self.assertEqual(self.s.do("build stack media")[0], "stack-ops")
        self.assertTrue((self.d / "stacks/media/stack.json").exists())
        self.assertIn("ollama-ops", (self.d / "stacks/media/stack.json").read_text())
        self.s.do("build stack media")
        self.assertTrue((self.d / "stacks/media/stack_1.json").exists())

    def test_status(self):
        _, out = self.s.do("stack status")
        self.assertIn("ollama-ops: built", out)



class Health(unittest.TestCase):
    def test_report(self):
        d = Path(tempfile.mkdtemp())
        shutil.copytree(Path(__file__).resolve().parents[1] / "agents", d / "agents")
        s = Swarm(d, llm=Offline())
        s.team["ollama-ops"].host = "http://127.0.0.1:1"
        agent, out = s.do("morning report")
        self.assertEqual(agent, "health-report")
        f = next((d / "outbox").glob("health_*.md"))
        txt = f.read_text()
        self.assertIn("Ollama: CHECK", txt)
        self.assertIn("Disk free", txt)
        self.assertEqual(s.router.pick("ollama status"), "ollama-ops")

    def test_flags_exact_state(self):
        from swarm.health_report import HealthReport

        class O:
            status = staticmethod(lambda: "ollama 0.9 UP, 1 models")
            fit = staticmethod(lambda: "ok")

        d = Path(tempfile.mkdtemp())
        s = Swarm(d, llm=Offline())
        for state, want in [("inactive", "CHECK"), ("active", "OK"),
                            ("failed", "CHECK")]:
            sun = SunshineOps(lambda c, st=state: f"STATE : 1 {st}" if c[0] == "sc" else st,
                              lambda p: False, ["/nope"])
            txt = HealthReport(s.jail, s.mem, O(), sun).build()
            self.assertIn(f"Sunshine: {want}", txt, state)
            self.assertIn("Ollama: OK", txt)


if __name__ == "__main__":
    unittest.main()
