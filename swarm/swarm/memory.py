"""Self-learning memory: append-only JSONL of outcomes, retrieved by word overlap.
Good outcomes become few-shot examples; bad ones become 'avoid' hints."""
import json
import re
import time
from pathlib import Path


def _words(s):
    return set(re.findall(r"[a-z0-9_]{3,}", s.lower()))


class Memory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def all(self):
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def add(self, task, agent, action, ok):
        rec = {"t": time.time(), "task": task, "agent": agent,
               "action": action, "ok": bool(ok)}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        return rec

    def similar(self, task, k=3, ok=None):
        q = _words(task)
        scored = []
        for r in self.all():
            if ok is not None and r["ok"] != ok:
                continue
            w = _words(r["task"])
            if q and w:
                s = len(q & w) / len(q | w)
                if s > 0:
                    scored.append((s, r))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:k]]

    def vote(self, task):
        """Agent that most often succeeded on similar tasks (None if no data)."""
        tally = {}
        for r in self.similar(task, k=5):
            tally[r["agent"]] = tally.get(r["agent"], 0) + (1 if r["ok"] else -1)
        best = max(tally.items(), key=lambda x: x[1], default=None)
        return best[0] if best and best[1] > 0 else None
