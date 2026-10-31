"""sunshine-ops: read-only health check for the Sunshine game-stream host."""
import os
import re
import socket
import subprocess
from pathlib import Path

PORTS = {47990: "web UI (https)", 47984: "stream (https)", 47989: "stream (http)"}
CONFS = [r"C:\Program Files\Sunshine\config\sunshine.conf",
         str(Path.home() / ".config/sunshine/sunshine.conf")]
KEYS = ("sunshine_name", "port", "gamepad", "encoder", "adapter_name", "output_name")


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return f"unavailable: {e}"


def _probe(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


class SunshineOps:
    name = "sunshine-ops"

    def __init__(self, runner=_run, probe=_probe, confs=None):
        self.run_cmd, self.probe, self.confs = runner, probe, confs or CONFS

    def service(self):
        if os.name == "nt":
            out = self.run_cmd(["sc", "query", "SunshineService"])
            state = re.search(r"STATE\s*:\s*\d+\s+(\w+)", out)
            return state.group(1) if state else "NOT INSTALLED"
        out = self.run_cmd(["systemctl", "--user", "is-active", "sunshine"])
        return out.splitlines()[-1] if out else "unknown"

    def config(self):
        for c in self.confs:
            p = Path(c)
            if p.is_file():                      # read only, never written
                kv = {}
                for line in p.read_text(errors="replace").splitlines():
                    k, _, v = line.partition("=")
                    if k.strip() in KEYS:
                        kv[k.strip()] = v.strip()
                return f"{p}: " + (", ".join(f"{k}={v}" for k, v in kv.items()) or "defaults")
        return "no sunshine.conf found (defaults in use or not installed)"

    def run(self, task):
        svc = self.service()
        ports = [f"  {p} {d}: {'open' if self.probe(p) else 'closed'}" for p, d in PORTS.items()]
        lines = [f"sunshine service: {svc}", *ports, self.config()]
        if svc.upper() not in ("RUNNING", "ACTIVE"):
            fix = ("Start-Service SunshineService  (admin PowerShell)" if os.name == "nt"
                   else "systemctl --user start sunshine")
            lines.append("not running. Run yourself: " + fix)
        return "\n".join(lines)
