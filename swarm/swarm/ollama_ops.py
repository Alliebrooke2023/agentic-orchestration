"""ollama-ops: status, pull, and RAM-fit for quantized models."""
import json
import os
import re
import urllib.request

from .llm import HOST, MODELS


def free_ram_gb():
    if os.name == "nt":
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong),
                        ("tot", ctypes.c_ulonglong), ("avail", ctypes.c_ulonglong),
                        ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                        ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong),
                        ("e", ctypes.c_ulonglong)]
        m = MS()
        m.l = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.avail / 1e9
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable"):
                return int(line.split()[1]) / 1e6
    return 0.0


class OllamaOps:
    name = "ollama-ops"

    def __init__(self, host=HOST, ram_gb=free_ram_gb, timeout=600):
        self.host, self.ram, self.timeout = host, ram_gb, timeout

    def _req(self, path, body=None, timeout=5):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.host + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def status(self):
        try:
            ver = self._req("/api/version")["version"]
            models = self._req("/api/tags").get("models", [])
        except Exception:
            return ("ollama is DOWN at " + self.host +
                    ". Start it: `ollama serve` (Windows: open the Ollama app).")
        rows = [f"  {m['name']}  {m.get('size', 0) / 1e9:.1f} GB" for m in models]
        return f"ollama {ver} UP, {len(models)} models\n" + "\n".join(rows)

    def fit(self):
        gb = self.ram()
        # rough sizes (GB) of the default quantized models, x1.3 for context/overhead
        size = {"qwen2.5:1.5b-instruct-q4_K_M": 1.0, "llama3.2:1b": 1.3,
                "qwen2.5:0.5b": 0.4, "gemma3:1b": 0.8}
        fits = [m for m in MODELS if size.get(m, 2) * 1.3 <= gb]
        pick = fits[0] if fits else None
        return (f"free RAM {gb:.1f} GB -> " +
                (f"fits: {', '.join(fits)}; recommend {pick}" if pick
                 else "nothing fits; close apps or use qwen2.5:0.5b"))

    def pull(self, model):
        try:
            self._req("/api/pull", {"model": model, "stream": False}, self.timeout)
        except Exception as e:
            return f"pull failed for {model}: {e}"
        return f"pulled {model}"

    def run(self, task):
        m = re.search(r"\bpull\s+([\w.:\-/]+)", task, re.I)
        if m:
            return self.pull(m.group(1))
        if re.search(r"\b(ram|fit|memory)\b", task, re.I):
            return self.fit()
        return self.status() + "\n" + self.fit()
