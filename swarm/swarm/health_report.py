"""health-report: one-page morning status (Ollama, Sunshine, RAM, disk, recent activity)."""
import shutil
import time


class HealthReport:
    name = "health-report"

    def __init__(self, jail, memory, ollama, sunshine):
        self.j, self.mem, self.ollama, self.sunshine = jail, memory, ollama, sunshine

    def build(self):
        def safe(fn):
            try:
                return fn()
            except Exception as e:      # a broken check must not kill the report
                return f"check failed: {e}"
        du = shutil.disk_usage(self.j.root)
        recent = self.mem.all()[-5:]
        acts = [f'- [{"ok" if r["ok"] else "FAIL"}] {r["agent"]}: {r["task"]}' for r in recent]
        flag = lambda s: "OK" if ("UP" in s or "RUNNING" in s.upper() or "active" in s) else "CHECK"
        oll, sun = safe(self.ollama.status), safe(self.sunshine.service)
        lines = [f"# Morning report {time.strftime('%Y-%m-%d %H:%M')}", "",
                 f"- Ollama: {flag(oll)}", f"- Sunshine: {flag(sun)}",
                 f"- Disk free: {du.free / 1e9:.0f} GB", "",
                 "## Ollama", oll, "", "## RAM", safe(self.ollama.fit), "",
                 "## Sunshine", safe(lambda: self.sunshine.run("")), "",
                 "## Last swarm activity", *(acts or ["- none"])]
        return "\n".join(lines)

    def run(self, task):
        text = self.build()
        path = self.j.write(f"outbox/health_{time.strftime('%Y%m%d')}.md", text)
        head = text.splitlines()[2:5]
        return "wrote " + path + "\n" + "\n".join(head)
