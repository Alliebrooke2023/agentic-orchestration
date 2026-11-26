# C:\swarm\jarvis\jarvis.py -- 3D hand-motion HUD for the swarm. Stdlib only.
"""python jarvis.py            fetch libs (first run), serve on 127.0.0.1:8770, open browser
python jarvis.py --fetch    only download libs into vendor/
python jarvis.py --no-open  serve without opening a browser"""
import argparse
import base64
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor"
NPM = [  # (tarball, sha512 integrity, {member in tgz: saved name})
    ("https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-0.10.14.tgz",
     "vOifgZhkndgybdvoRITzRkIueWWSiCKuEUXXK6Q4FaJsFvRJuwgg++vqFUMlL0Uox62U5aEXFhHxlhV7Ja5e3Q==",
     {"package/vision_bundle.mjs": "vision_bundle.mjs",
      "package/wasm/vision_wasm_internal.js": "wasm/vision_wasm_internal.js",
      "package/wasm/vision_wasm_internal.wasm": "wasm/vision_wasm_internal.wasm",
      "package/wasm/vision_wasm_nosimd_internal.js": "wasm/vision_wasm_nosimd_internal.js",
      "package/wasm/vision_wasm_nosimd_internal.wasm": "wasm/vision_wasm_nosimd_internal.wasm"}),
    ("https://registry.npmjs.org/three/-/three-0.160.0.tgz",
     "DLU8lc0zNIPkM7rH5/e1Ks1Z8tWCGRq6g8mPowdDJpw1CFBJMU7UoJjC6PefXW7z//SSl0b2+GCw14LB+uDhng==",
     {"package/build/three.module.js": "three.module.js"}),
]
MODEL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
         "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1")
TYPES = {".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript",
         ".wasm": "application/wasm", ".task": "application/octet-stream", ".json": "application/json"}
STATIC = {"hand.html", "gestures.js"}


def _get(url):
    with urllib.request.urlopen(url, timeout=120) as r:  # nosec B310 - fixed https URLs above
        return r.read()


def fetch(force=False):
    if VENDOR.joinpath("hand_landmarker.task").exists() and not force:
        return
    for url, integ, members in NPM:
        print("fetch", url)
        data = _get(url)
        if base64.b64encode(hashlib.sha512(data).digest()).decode() != integ:
            sys.exit(f"integrity mismatch: {url}")
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            for m, name in members.items():
                out = VENDOR / name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(tf.extractfile(m).read())
    print("fetch", MODEL[0])
    data = _get(MODEL[0])
    if hashlib.sha256(data).hexdigest() != MODEL[1]:
        sys.exit("integrity mismatch: hand model")
    VENDOR.joinpath("hand_landmarker.task").write_bytes(data)


def find_swarm(arg):
    for p in ([Path(arg)] if arg else []) + [HERE.parent / "swarm", HERE.parent, Path(r"C:\swarm")]:
        if (p / "swarm" / "__main__.py").exists():
            return p.resolve()
    return None


class App:
    def __init__(self, swarm_dir, cfg_path=HERE / "jarvis.json", cooldown=3.0):
        self.swarm_dir, self.cooldown, self.last, self.lock = swarm_dir, cooldown, 0.0, threading.Lock()
        self.commands = json.loads(Path(cfg_path).read_text(encoding="utf-8"))["commands"]

    def run(self, gesture):
        cmd = self.commands.get(gesture)
        if not cmd:
            return 400, {"error": f"no command for '{gesture}'"}
        if not self.swarm_dir:
            return 503, {"error": "swarm folder not found (use --swarm PATH)"}
        with self.lock:
            if time.time() - self.last < self.cooldown:
                return 429, {"error": "cooldown"}
            self.last = time.time()
        try:
            r = subprocess.run([sys.executable, "-m", "swarm", cmd], cwd=self.swarm_dir,  # nosec B603 - whitelisted
                               capture_output=True, text=True, timeout=180)
            return 200, {"gesture": gesture, "command": cmd, "output": (r.stdout + r.stderr).strip()[-4000:]}
        except subprocess.TimeoutExpired:
            return 504, {"error": "swarm timed out", "command": cmd}


def make_handler(app, port):
    allowed = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json"):
            if isinstance(body, dict):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?")[0].lstrip("/") or "hand.html"
            if path == "config":
                return self.send(200, {"commands": app.commands, "swarm": bool(app.swarm_dir)})
            f = (HERE / path).resolve()
            ok = path in STATIC or (f.is_relative_to(VENDOR.resolve()) and f.is_file())
            if not ok or f.suffix not in TYPES:
                return self.send(404, {"error": "not found"})
            self.send(200, f.read_bytes(), TYPES[f.suffix])

        def do_POST(self):
            if self.path != "/cmd":
                return self.send(404, {"error": "not found"})
            if self.headers.get("Origin") not in allowed:  # blocks other websites poking localhost
                return self.send(403, {"error": "bad origin"})
            try:
                n = min(int(self.headers.get("Content-Length", 0)), 4096)
                gesture = json.loads(self.rfile.read(n) or b"{}").get("gesture", "")
            except (ValueError, AttributeError):
                return self.send(400, {"error": "bad json"})
            self.send(*app.run(str(gesture)))
    return H


def serve(app, port, host="127.0.0.1"):
    return ThreadingHTTPServer((host, port), make_handler(app, port))


def main():
    ap = argparse.ArgumentParser(prog="jarvis")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--swarm", help="folder that contains the swarm package (default: auto)")
    ap.add_argument("--fetch", action="store_true", help="re-download libs and exit")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        return fetch(force=True)
    fetch()
    app = App(find_swarm(a.swarm))
    srv = serve(app, a.port)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"[jarvis] {url}  swarm: {app.swarm_dir or 'NOT FOUND'}  (Ctrl+C to stop)")
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
