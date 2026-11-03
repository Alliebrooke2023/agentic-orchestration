"""Ollama client over HTTP (stdlib). Falls back to Offline when Ollama is down."""
import json
import urllib.request

HOST = "http://127.0.0.1:11434"
# Quantized, CPU-friendly defaults. First one that is installed wins.
MODELS = ["qwen2.5:1.5b-instruct-q4_K_M", "llama3.2:1b", "qwen2.5:0.5b", "gemma3:1b"]


class Offline:
    """No-model backend: returns '' so agents use their rule-based fallback."""
    name = "offline"

    def chat(self, system, user, json_mode=False):
        return ""


class Ollama:
    def __init__(self, model=None, host=HOST, timeout=180):
        self.host, self.timeout, self.model = host, timeout, model
        have = self.installed()
        if not self.model:
            self.model = next((m for m in MODELS if m in have),
                              next(iter(have), None))
        if not self.model:
            raise RuntimeError("no Ollama model installed")
        self.name = f"ollama:{self.model}"

    def _req(self, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.host + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def installed(self):
        try:
            return [m["name"] for m in self._req("/api/tags").get("models", [])]
        except Exception:
            return []

    def chat(self, system, user, json_mode=False):
        body = {"model": self.model, "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 2048, "num_predict": 400},
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        if json_mode:
            body["format"] = "json"
        return self._req("/api/chat", body)["message"]["content"]


def connect(model=None, host=HOST):
    try:
        return Ollama(model, host)
    except Exception:
        return Offline()
