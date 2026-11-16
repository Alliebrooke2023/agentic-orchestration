# DriftRack - agent notes

Second-hand fashion marketplace. Self-contained in `driftrack/`. Do not import from,
or add dependencies on, anything else in this repository.

## Commands

- Run: `python app.py --seed` (http://127.0.0.1:8750, demo login `demo` / `demo123`)
- Test: `python -m unittest discover -s tests -v`

## Rules

- Python standard library only. No pip installs, no front-end build step.
- All SQL uses `?` parameters. Never format user input into SQL.
- Front end: every dynamic value goes through `esc()` before `innerHTML`.
- New API route = handler `h_*` in `app.py` + an entry in `ROUTES` + a test in `tests/test_api.py`.
- Raise `ApiError` (or use `need()`) for user-facing errors; messages are shown to shoppers.
- Money moves to a seller's balance only when the buyer confirms delivery.
- Colours come from the CSS variables at the top of `static/style.css`.
- Every animation must respect `prefers-reduced-motion`.
- `data/` holds the live database and photos. Never delete it without asking the owner.
- Sandbox status: payments are simulated, server binds to 127.0.0.1. Keep it that way
  until the owner says to launch publicly.
