"""Orchestrator: route -> run -> remember. `feedback` teaches the swarm."""
from pathlib import Path

from .agents import Blueprinter, Handoff, Mover, Router
from .llm import connect
from .memory import Memory
from .tools import Jail


class Swarm:
    def __init__(self, root=".", model=None, llm=None):
        self.root = Path(root).resolve()
        self.llm = llm or connect(model)
        self.jail = Jail(self.root)
        self.mem = Memory(self.root / "state" / "memory.jsonl")
        self.router = Router(self.llm, self.mem)
        self.team = {"mover": Mover(self.jail),
                     "blueprinter": Blueprinter(self.jail, self.llm, self.root / "agents"),
                     "handoff": Handoff(self.jail, self.mem)}
        self.last = None

    def do(self, task):
        agent = self.router.pick(task)
        try:
            result, ok = self.team[agent].run(task), True
        except Exception as e:          # failures are lessons too
            result, ok = f"error: {e}", False
        self.last = self.mem.add(task, agent, result, ok)
        return agent, result

    def feedback(self, good):
        """Mark last result good/bad; bad runs stop being trusted for similar tasks."""
        if not self.last:
            return "nothing to rate"
        r = self.last
        self.mem.add(r["task"], r["agent"], r["action"], good and r["ok"])
        return "learned: " + ("keep doing that" if good else "avoid that route")
