import argparse

from .core import Swarm


def main():
    ap = argparse.ArgumentParser(prog="swarm")
    ap.add_argument("task", nargs="*", help="one-shot task; omit for interactive")
    ap.add_argument("--root", default=".", help="swarm folder (jail for file ops)")
    ap.add_argument("--model", help="Ollama model tag")
    ap.add_argument("--sync", help="copy reports to this folder (e.g. your OneDrive)")
    ap.add_argument("--ntfy", help="ntfy topic for phone pings, or 'auto' to make one")
    a = ap.parse_args()
    if a.sync or a.ntfy:
        from . import notify
        topic = notify.new_topic() if a.ntfy == "auto" else a.ntfy
        cfg = notify.save(a.root, sync_dir=a.sync, ntfy_topic=topic)
        print("saved swarm.json:", cfg)
        if topic:
            print(f"On your phone: install ntfy, subscribe to topic: {topic}")
        return
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
