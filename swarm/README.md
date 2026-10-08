# Swarm — self-learning agents for CPU + quantized models

Stdlib-only Python. Talks to Ollama on :11434. Works with no model too (rule fallback).

## Agents
- router — picks agent; learns from past outcomes
- mover — move/copy/list/sort files (jailed, never deletes/overwrites)
- blueprinter — writes blueprints to `blueprints/`
- handoff — writes session handoff to `outbox/`
- planned (specs in `agents/`): ollama-ops, sunshine-ops, stack-builder

## Self-learning
Every task is logged to `state/memory.jsonl`. Type `good` / `bad` after a result.
Router trusts routes that worked on similar tasks, avoids ones rated bad.

## Run (Windows PowerShell)
    cd C:\swarm
    .\install.ps1
    python -m swarm
    python -m swarm "sort inbox"

## Not integrated
Lives in `swarm/`, separate from the Next.js app in the repo root. No shared code.
