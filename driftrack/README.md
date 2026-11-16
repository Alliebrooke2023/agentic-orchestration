# DriftRack

The night market for pre-loved style. A second-hand fashion marketplace:
list items, browse, save, make offers, chat, buy, ship, review.

- **Zero installs.** Python 3.9+ standard library only. SQLite database.
- **Sandbox build.** Runs on your own machine at `127.0.0.1`. Payments are simulated.
- **Self-contained.** Everything lives in this folder. Nothing else in the repo touches it.

## Run

```powershell
cd driftrack
python app.py --seed
```

Open http://127.0.0.1:8750 - demo seller login is `demo` / `demo123`.
Or run `.\start.ps1` for a menu (install check / run / test).

## Test

```powershell
python -m unittest discover -s tests -v
```

## Files

| Path | What it is |
| --- | --- |
| `app.py` | Server, database, every API route |
| `seed.py` | Demo sellers, listings, sales |
| `static/` | The whole front end (HTML, CSS, JS) |
| `tests/test_api.py` | End-to-end API tests |
| `MANUAL.md` | How everything works, for the owner |
| `CLAUDE.md` | Rules for AI agents working on this code |
| `.claude/skills/` | Reusable agent skills (run, add feature, re-theme) |
| `data/` | Your database and photos (created on first run, not in git) |
