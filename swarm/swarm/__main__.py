import argparse

from .core import Swarm


def main():
    ap = argparse.ArgumentParser(prog="swarm")
    ap.add_argument("task", nargs="*", help="one-shot task; omit for interactive")
    ap.add_argument("--root", default=".", help="swarm folder (jail for file ops)")
    ap.add_argument("--model", help="Ollama model tag")
    a = ap.parse_args()
    s = Swarm(a.root, a.model)
    print(f"[swarm] backend: {s.llm.name}")
    if a.task:
        agent, res = s.do(" ".join(a.task))
        print(f"[{agent}] {res}")
        return
    print("type a task. 'good' / 'bad' teaches it. 'quit' exits.")
    while True:
        try:
            line = input("swarm> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line in ("quit", "exit"):
            break
        if line in ("good", "bad"):
            print(s.feedback(line == "good"))
        elif line:
            agent, res = s.do(line)
            print(f"[{agent}] {res}")


main()
