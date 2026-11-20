# DriftRack

The night market for pre-loved style. A second-hand fashion marketplace:
list items, browse, save, make offers, chat, buy, ship, review.

- **Zero installs.** Python 3.9+ standard library only. SQLite database.
- **Sandbox by default.** Runs on `127.0.0.1` with simulated payments.
- **Launch-ready switches.** Stripe Checkout, SMTP password reset, owner admin and
  moderation, login rate limits, security headers, Docker + Render deploy files.
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
| `payments.py` | Stripe Checkout (off unless `STRIPE_SECRET_KEY` is set) |
| `mailer.py` | SMTP email for password reset (off unless configured) |
| `seed.py` | Demo sellers, listings, sales |
| `Dockerfile`, `render.yaml` | Deploy kit (see MANUAL section 12) |
| `static/` | The whole front end (HTML, CSS, JS) |
| `tests/test_api.py` | End-to-end API tests |
| `MANUAL.md` | How everything works, for the owner |
| `CLAUDE.md` | Rules for AI agents working on this code |
| `.claude/skills/` | Reusable agent skills (run, add feature, re-theme) |
| `data/` | Your database and photos (created on first run, not in git) |
