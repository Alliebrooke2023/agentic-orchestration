"""Agents. Each = rule-based core (always works) + optional small-LLM assist."""
import json
import re
import time
from pathlib import Path

ROUTES = {
    "ollama-ops": r"\b(ollama|pull|models?|ram)\b",
    "sunshine-ops": r"\b(sunshine|moonlight|stream(ing)?)\b",
    "stack-ops": r"\b(stack-ops|(build|scaffold)\s+(a\s+)?stack|stacks?\s+(list|status))\b",
    "mover": r"\b(move|copy|list|ls|organi[sz]e|sort|files?|folder)\b",
    "blueprinter": r"\b(blueprint|outline|design|plan|spec|architecture|stack)\b",
    "handoff": r"\b(handoff|hand off|package|transfer|sync|send)\b",
}


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


class Router:
    name = "router"

    def __init__(self, llm, memory):
        self.llm, self.mem = llm, memory

    def pick(self, task):
        learned = self.mem.vote(task)          # 1. what worked before
        if learned:
            return learned
        scores = {a: len(re.findall(p, task, re.I)) for a, p in ROUTES.items()}
        best = max(scores, key=scores.get)     # 2. keywords
        if scores[best]:
            return best
        shots = "\n".join(f'{r["task"]} -> {r["agent"]}'
                          for r in self.mem.similar(task, 3, ok=True))
        out = parse_json(self.llm.chat(      # 3. small model, few-shot from memory
            'Pick one agent: mover, blueprinter, handoff, ollama-ops, sunshine-ops, stack-ops. Reply JSON {"agent":"..."}.\n'
            + shots, task, json_mode=True))
        return out["agent"] if out and out.get("agent") in ROUTES else "blueprinter"


class Mover:
    name = "mover"

    def __init__(self, jail):
        self.j = jail

    def run(self, task):
        t = task.strip()
        m = re.search(r"\b(move|copy)\s+(\S+)\s+(?:to|into)\s+(\S+)", t, re.I)
        if m:
            op, a, b = m.groups()
            fn = self.j.move if op.lower() == "move" else self.j.copy
            return f"{op.lower()}d -> {fn(a, b)}"
        if re.search(r"\b(organi[sz]e|sort)\b", t, re.I):
            src = (re.search(r"\b(?:organi[sz]e|sort)\s+(\S+)", t, re.I) or [None, "inbox"])[1]
            n = 0
            for f in list(self.j.p(src).iterdir()):
                if f.is_file():
                    ext = f.suffix.lstrip(".").lower() or "noext"
                    self.j.p(f"sorted/{ext}").mkdir(parents=True, exist_ok=True)
                    self.j.move(f"{src}/{f.name}", f"sorted/{ext}")
                    n += 1
            return f"sorted {n} files into sorted/<ext>/"
        m = re.search(r"\b(?:list|ls)\s+(\S+)", t, re.I)
        return "\n".join(self.j.ls(m.group(1) if m else "."))


class Blueprinter:
    name = "blueprinter"

    def __init__(self, jail, llm, agents_dir):
        self.j, self.llm, self.dir = jail, llm, Path(agents_dir)

    def run(self, task):
        roster = [json.loads(p.read_text()) for p in sorted(self.dir.glob("*.json"))]
        known = ", ".join(r["name"] for r in roster)
        slug = re.sub(r"\W+", "-", task.lower()).strip("-")[:40] or "blueprint"
        prose = self.llm.chat(
            "You write short build blueprints: goal, agents, steps, risks. Max 12 lines.",
            f"Task: {task}\nAvailable agents: {known}") or (
            f"# Blueprint: {task}\n\nGoal: {task}\nAgents available: {known}\n"
            "Steps:\n1. Define inputs/outputs\n2. Assign agents from roster\n"
            "3. Run on small model, record outcome in memory\n4. Hand off via outbox/\n"
            "Risks: model too small for long plans -> keep steps short.\n")
        return "wrote " + self.j.write(f"blueprints/{slug}.md", prose)


class Handoff:
    name = "handoff"

    def __init__(self, jail, memory):
        self.j, self.mem = jail, memory

    def run(self, task):
        recent = self.mem.all()[-10:]
        body = [f"# Handoff {time.strftime('%Y-%m-%d %H:%M')}", f"Request: {task}", "",
                "## Recent activity"]
        body += [f'- [{"ok" if r["ok"] else "FAIL"}] {r["agent"]}: {r["task"]} -> {r["action"][:80]}'
                 for r in recent] or ["- none"]
        body += ["", "## Files", *[f"- {x}" for x in self.j.ls(".")],
                 "", "Paste this into the next session/agent as context."]
        return "wrote " + self.j.write(f"outbox/handoff_{int(time.time())}.md", "\n".join(body))
