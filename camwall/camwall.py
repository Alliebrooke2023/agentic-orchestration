# C:\forge\camwall\camwall.py
"""CamWall: multi-camera wall + remote control + recording.

Sources: USB / DVI-HDMI capture cards (UVC indexes), Cortex cam + local IoT cams
(RTSP/HTTP/MJPEG URLs, ONVIF/SSDP discovery), Bluetooth scan (BLE, via bleak),
and demo:N synthetic feeds for sandbox testing.
"""
import argparse, json, os, socket, threading, time, secrets
from datetime import datetime
import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, abort, redirect

HERE = os.path.dirname(os.path.abspath(__file__))
REC_DIR = os.path.join(HERE, "recordings")
CFG = os.path.join(HERE, "sources.json")
os.makedirs(REC_DIR, exist_ok=True)


class Cam:
    def __init__(self, cid, name, src, kind):
        self.id, self.name, self.src, self.kind = cid, name, src, kind
        self.frame = None
        self.ok = False
        self.fps = 0.0
        self.writer = None
        self.rec_path = None
        self.lock = threading.Lock()
        self.stop = False
        self.t = threading.Thread(target=self.loop, daemon=True)
        self.t.start()

    def open(self):
        if str(self.src).startswith("demo:"):
            return None
        s = self.src
        if isinstance(s, str) and s.isdigit():
            s = int(s)
        cap = cv2.VideoCapture(s, cv2.CAP_DSHOW) if (isinstance(s, int) and os.name == "nt") else cv2.VideoCapture(s)
        return cap if cap.isOpened() else None

    def demo_frame(self, n):
        seed = int(str(self.src).split(":")[1] or 0)
        img = np.zeros((360, 640, 3), np.uint8)
        img[:] = ((40 + seed * 50) % 200, 60, (120 + seed * 70) % 255)
        x = int((n * 6 + seed * 100) % 600)
        cv2.circle(img, (x + 20, 180), 30, (255, 255, 255), -1)
        cv2.putText(img, time.strftime("%H:%M:%S"), (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
        return img

    def loop(self):
        n = 0
        while not self.stop:
            cap = self.open()
            demo = cap is None and str(self.src).startswith("demo:")
            if cap is None and not demo:
                self.ok = False
                time.sleep(3)
                continue
            last = time.time()
            while not self.stop:
                if demo:
                    f, r = self.demo_frame(n), True
                    time.sleep(1 / 20)
                else:
                    r, f = cap.read()
                if not r:
                    break
                n += 1
                f = cv2.resize(f, (640, 360)) if f.shape[1] != 640 else f
                now = time.time()
                self.fps = 0.9 * self.fps + 0.1 / max(now - last, 1e-3)
                last = now
                with self.lock:
                    self.frame, self.ok = f, True
                    if self.writer:
                        self.writer.write(f)
            self.ok = False
            if cap:
                cap.release()
            time.sleep(1)

    def jpeg(self):
        with self.lock:
            f = self.frame
        if f is None or not self.ok:
            f = np.zeros((360, 640, 3), np.uint8)
            cv2.putText(f, "NO SIGNAL", (190, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (80, 80, 255), 3)
        return cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()

    def rec_start(self):
        with self.lock:
            if self.writer or self.frame is None:
                return False
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.rec_path = os.path.join(REC_DIR, f"{self.name.replace(' ', '_')}_{ts}.mp4")
            self.writer = cv2.VideoWriter(self.rec_path, cv2.VideoWriter_fourcc(*"mp4v"), 15, (640, 360))
            return True

    def rec_stop(self):
        with self.lock:
            if self.writer:
                self.writer.release()
                self.writer = None

    def snap(self):
        p = os.path.join(REC_DIR, f"{self.name.replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M%S}.jpg")
        with open(p, "wb") as fh:
            fh.write(self.jpeg())
        return p

    def info(self):
        return dict(id=self.id, name=self.name, src=str(self.src), kind=self.kind,
                    ok=self.ok, fps=round(self.fps, 1), rec=bool(self.writer))


cams = {}


def add_cam(name, src, kind="usb"):
    cid = f"c{len(cams) + 1}"
    cams[cid] = Cam(cid, name, src, kind)
    save_cfg()
    return cid


def save_cfg():
    with open(CFG, "w") as fh:
        json.dump([dict(name=c.name, src=c.src, kind=c.kind) for c in cams.values()], fh, indent=2)


# ---------- discovery ----------
def scan_local(maxn=6):
    """USB webcams + DVI/HDMI capture cards (both show up as UVC indexes)."""
    out = []
    for i in range(maxn):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(i)
        if cap.isOpened():
            ok, f = cap.read()
            out.append(dict(src=str(i), name=f"Local video {i}", kind="usb/dvi", live=bool(ok)))
        cap.release()
    return out


def scan_onvif(timeout=2.5):
    """WS-Discovery for ONVIF IP/IoT cameras on the LAN."""
    msg = ('<?xml version="1.0"?><e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
           'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
           'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
           'xmlns:dn="http://www.onvif.org/ver10/network/wsdl"><e:Header><w:MessageID>uuid:%s</w:MessageID>'
           '<w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
           '<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header>'
           '<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body></e:Envelope>'
           % secrets.token_hex(8)).encode()
    found = {}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.sendto(msg, ("239.255.255.250", 3702))
        end = time.time() + timeout
        while time.time() < end:
            try:
                data, addr = s.recvfrom(65535)
                found[addr[0]] = dict(src=f"rtsp://{addr[0]}:554/", name=f"IoT cam {addr[0]}", kind="onvif")
            except socket.timeout:
                pass
    except OSError:
        pass
    return list(found.values())


def scan_bluetooth(timeout=4):
    try:
        import asyncio
        from bleak import BleakScanner
        devs = asyncio.run(BleakScanner.discover(timeout=timeout))
        return [dict(src="", name=f"BT {d.name or '?'} {d.address}", kind="bluetooth") for d in devs]
    except Exception as e:
        return [dict(src="", name=f"Bluetooth unavailable ({type(e).__name__})", kind="bluetooth")]


# ---------- web ----------
app = Flask(__name__)
TOKEN = ""
COOKIE = "camwall_auth"
ALLOWED_SCHEMES = ("rtsp://", "rtsps://", "http://", "https://", "demo:")


def valid_src(src):
    """Camera sources only: device index or network/demo URL. Blocks local file paths."""
    src = str(src).strip()
    return src.isdigit() or src.lower().startswith(ALLOWED_SCHEMES)


def token_ok(value):
    return bool(value) and secrets.compare_digest(str(value), TOKEN)


@app.before_request
def auth():
    """Every route needs the token. The token is never put in the page: a valid
    ?t= link sets an HttpOnly, SameSite=Strict cookie and redirects without it."""
    if token_ok(request.args.get("t")) and request.method == "GET" and request.path == "/":
        resp = redirect("/")
        resp.set_cookie(COOKIE, TOKEN, httponly=True, samesite="Strict")
        return resp
    if not (token_ok(request.cookies.get(COOKIE)) or token_ok(request.headers.get("X-Token"))):
        abort(401)


@app.route("/")
def index():
    return open(os.path.join(HERE, "ui.html"), encoding="utf-8").read()


@app.route("/api/cams")
def api_cams():
    return jsonify([c.info() for c in cams.values()])


@app.route("/api/add", methods=["POST"])
def api_add():
    d = request.json or {}
    if not valid_src(d.get("src", "")):
        abort(400, "source must be a camera index or rtsp/http(s) URL")
    return jsonify(id=add_cam(d["name"], d["src"], d.get("kind", "url")))


@app.route("/api/discover")
def api_discover():
    return jsonify(local=scan_local(), onvif=scan_onvif(), bluetooth=scan_bluetooth())


@app.route("/api/rec/<cid>/<act>", methods=["POST"])
def api_rec(cid, act):
    targets = list(cams.values()) if cid == "all" else [cams[cid]]
    for c in targets:
        c.rec_start() if act == "start" else c.rec_stop()
    return jsonify(ok=True, cams=[c.info() for c in cams.values()])


@app.route("/api/snap/<cid>", methods=["POST"])
def api_snap(cid):
    return jsonify(path=cams[cid].snap())


@app.route("/api/recordings")
def api_recs():
    return jsonify(sorted(os.listdir(REC_DIR)))


@app.route("/stream/<cid>")
def stream(cid):
    c = cams[cid]

    def gen():
        while True:
            yield b"--f\r\nContent-Type: image/jpeg\r\n\r\n" + c.jpeg() + b"\r\n"
            time.sleep(0.07)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=f")


def main():
    global TOKEN
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", type=int, default=0, help="add N synthetic cams")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--token", default="", help="access token (random one is generated if omitted)")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--auto", action="store_true", help="auto-add discovered local+ONVIF cams")
    a = ap.parse_args()
    TOKEN = a.token or secrets.token_urlsafe(16)
    if os.path.exists(CFG) and not a.demo:
        for s in json.load(open(CFG)):
            if valid_src(s["src"]):
                add_cam(s["name"], s["src"], s["kind"])
    if a.auto:
        for d in scan_local() + scan_onvif():
            add_cam(d["name"], d["src"], d["kind"])
    for i in range(a.demo):
        add_cam(f"Demo {i + 1}", f"demo:{i + 1}", "demo")
    url = f"http://localhost:{a.port}/?t={TOKEN}"
    print(f"CamWall open: {url}\nPhone/remote: http://<this-pc-ip>:{a.port}/?t={TOKEN}  (keep this link private)")
    if not a.no_browser:
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
