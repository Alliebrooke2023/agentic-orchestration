import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swarm.core import Swarm
from swarm.llm import Offline


class T(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(Path(__file__).resolve().parents[1] / "agents", self.d / "agents")
        self.s = Swarm(self.d, llm=Offline())

    def test_move_no_overwrite(self):
        (self.d / "a.txt").write_text("1")
        (self.d / "box").mkdir()
        (self.d / "box" / "a.txt").write_text("old")
        self.assertEqual(self.s.do("move a.txt to box")[0], "mover")
        self.assertEqual((self.d / "box" / "a.txt").read_text(), "old")
        self.assertTrue((self.d / "box" / "a_1.txt").exists())

    def test_jail(self):
        _, r = self.s.do("move ../../etc/passwd to box")
        self.assertIn("error", r)

    def test_sort(self):
        (self.d / "inbox").mkdir()
        (self.d / "inbox" / "x.pdf").write_text("p")
        self.s.do("sort inbox")
        self.assertTrue((self.d / "sorted" / "pdf" / "x.pdf").exists())

    def test_blueprint_and_handoff(self):
        self.assertEqual(self.s.do("blueprint a media stack")[0], "blueprinter")
        self.assertTrue(list((self.d / "blueprints").glob("*.md")))
        self.assertEqual(self.s.do("handoff to next session")[0], "handoff")
        self.assertTrue(list((self.d / "outbox").glob("handoff_*.md")))

    def test_learning(self):
        self.s.do("blueprint a media stack")
        self.s.feedback(False)
        self.s.feedback(False)
        self.assertNotEqual(self.s.mem.vote("blueprint a media stack"), "blueprinter")
        self.s.do("blueprint a media stack")
        self.s.feedback(True)

if __name__ == "__main__":
    unittest.main()
