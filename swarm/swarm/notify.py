"""Delivery of outbox files: copy to a synced folder (OneDrive/Drive) + ntfy phone ping.
Config lives in swarm.json: {"sync_dir": "...", "ntfy_topic": "..."}. Failures never break a task."""
import json
import secrets
import shutil
import urllib.request
from pathlib import Path

NTFY = "https://ntfy.sh/"


def load(root):
    try:
        return json.loads((Path(root) / "swarm.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(root, **kv):
    cfg = load(root)
    cfg.update({k: v for k, v in kv.items() if v})
    (Path(root) / "swarm.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def new_topic():
    return "swarm-" + secrets.token_hex(8)       # unguessable: ntfy topics are public by name


def _post(url, data, title):
    req = urllib.request.Request(url, data=data, headers={"Title": title})
    urllib.request.urlopen(req, timeout=10).read()


class Notifier:
    def __init__(self, root, post=_post):
        self.root, self.post = Path(root), post

    def deliver(self, rel_path, summary):
        cfg, notes = load(self.root), []
        src = self.root / rel_path
        if cfg.get("sync_dir") and src.is_file():
            try:
                d = Path(cfg["sync_dir"])
                d.mkdir(parents=True, exist_ok=True)
                dst, i = d / src.name, 1
                while dst.exists():              # never overwrite
                    dst = d / f"{src.stem}_{i}{src.suffix}"
                    i += 1
                shutil.copy2(src, dst)
                notes.append(f"synced -> {dst}")
            except OSError as e:
                notes.append(f"sync failed: {e}")
        topic = cfg.get("ntfy_topic", "")
        if topic:
            if len(topic) < 12:
                notes.append("ntfy skipped: topic too short/guessable (use --ntfy auto)")
            else:
                try:
                    self.post(NTFY + topic, summary[:400].encode("utf-8"), "Swarm report")
                    notes.append("phone ping sent")
                except Exception as e:
                    notes.append(f"ntfy failed: {e}")
        return notes
