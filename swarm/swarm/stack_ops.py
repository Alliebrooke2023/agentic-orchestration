"""stack-ops: list/status the agent roster and scaffold a stack folder."""
import json
import re


class StackOps:
    name = "stack-ops"

    def __init__(self, jail, agents_dir):
        self.j, self.dir = jail, agents_dir

    def roster(self):
        return [json.loads(p.read_text()) for p in sorted(self.dir.glob("*.json"))]

    def status(self):
        r = self.roster()
        lines = [f"  {a['name']}: {a.get('status', '?')} - {a['role']}" for a in r]
        bps = sorted(p.name for p in self.j.p("blueprints").glob("*.md")) \
            if self.j.p("blueprints").is_dir() else []
        return "agents:\n" + "\n".join(lines) + "\nblueprints: " + (", ".join(bps) or "none")

    def build(self, name):
        name = re.sub(r"[^\w\-]+", "-", name.lower()).strip("-")
        if not name:
            raise ValueError("give the stack a name: build stack <name>")
        built = [a for a in self.roster() if a.get("status") == "built"]
        base = f"stacks/{name}"
        made = [self.j.write(f"{base}/stack.json", json.dumps(
            {"name": name, "agents": [a["name"] for a in built]}, indent=2))]
        for a in built:
            made.append(self.j.write(f"{base}/agents/{a['name']}.json", json.dumps(a, indent=2)))
        made.append(self.j.write(f"{base}/README.md",
                                 f"# {name}\n\nScaffolded by stack-ops. Agents: "
                                 + ", ".join(a["name"] for a in built) + "\n"))
        return f"scaffolded {len(made)} files in {base}/"

    def run(self, task):
        m = re.search(r"\b(?:build|scaffold|create)\s+(?:a\s+)?(?:stack\s+)?([\w\-]+)\s*$", task, re.I)
        if m and re.search(r"\b(build|scaffold)\b", task, re.I) and m.group(1).lower() != "stack":
            return self.build(m.group(1))
        return self.status()
