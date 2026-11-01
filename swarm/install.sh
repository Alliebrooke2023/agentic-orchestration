#!/usr/bin/env sh
# Linux: sh install.sh
set -e
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:1.5b-instruct-q4_K_M
ollama pull llama3.2:1b
python3 -m unittest discover tests
echo "Done. Run: python3 -m swarm"
