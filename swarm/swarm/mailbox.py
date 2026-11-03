"""mailbox: per-agent mailboxes so agents (and you) can hand jobs to each other.
mailbox/<agent>/<ts>_<sender>.json = pending. Processed mail moves to done/ (never deleted)."""
import json
import re
import time

MAX_PER_RUN = 20


class Mailbox:
    name = "mailbox"

    def __init__(self, jail, agent_names, run_agent, memory):
        self.j, self.names, self.run_agent, self.mem = jail, agent_names, run_agent, memory

    def post(self, to, body, sender="user"):
        if to not in self.names() or to == "mailbox":
            raise ValueError(f"unknown agent '{to}'. try: " + ", ".join(
                n for n in self.names() if n != "mailbox"))
        msg = {"from": sender, "to": to, "body": body, "t": time.time()}
        return self.j.write(f"mailbox/{to}/{int(time.time() * 1000)}_{sender}.json",
                            json.dumps(msg, indent=2))

    def pending(self):
        out = []
        root = self.j.p("mailbox")
        if root.is_dir():
            for d in sorted(root.iterdir()):
                out += [f for f in sorted(d.glob("*.json")) if d.is_dir()]
        return out

    def process(self):
        done = []
        for f in self.pending()[:MAX_PER_RUN]:      # snapshot: replies wait for next run
            msg = json.loads(f.read_text(encoding="utf-8"))
            try:
                result, ok = self.run_agent(msg["to"], msg["body"]), True
            except Exception as e:
                result, ok = f"error: {e}", False
            self.mem.add(msg["body"], msg["to"], result, ok)
            rel = f.relative_to(self.j.root).as_posix()
            self.j.p(f"mailbox/{msg['to']}/done").mkdir(parents=True, exist_ok=True)
            dest = self.j.move(rel, f"mailbox/{msg['to']}/done")
            self.j.write(dest + ".result.json", json.dumps({"ok": ok, "result": result}, indent=2))
            if msg["from"] not in ("user", msg["to"]) and msg["from"] in self.names():
                self.post(msg["from"], f"reply from {msg['to']}: {result[:300]}", sender=msg["to"])
            done.append(f"[{msg['to']}] {'ok' if ok else 'FAIL'}: {msg['body'][:50]}")
        return "processed %d\n" % len(done) + "\n".join(done) if done else "no mail"

    def status(self):
        counts = {}
        for f in self.pending():
            counts[f.parent.name] = counts.get(f.parent.name, 0) + 1
        return "pending: " + (", ".join(f"{a}={n}" for a, n in counts.items()) or "none")

    def run(self, task):
        m = re.match(r"\s*send\s+([\w-]+)\s*:\s*(.+)", task, re.I | re.S)
        if m:
            return "posted " + self.post(m.group(1).lower(), m.group(2).strip())
        if re.search(r"\bprocess\b", task, re.I):
            return self.process()
        return self.status()
