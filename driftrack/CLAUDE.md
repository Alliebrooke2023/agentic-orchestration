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
- Defaults stay sandbox-safe: payments simulated unless `STRIPE_SECRET_KEY` is set,
  server binds to 127.0.0.1 unless `DRIFTRACK_HOST` is set. Never change the defaults
  and never deploy publicly until the owner says to launch.
- Seller orders/revenue queries must filter with `VALID_ORDER` (excludes unpaid checkouts).
- Owner-only routes call `owner_only(ctx)`. Login-style routes call `rate_hit(...)`.
- Modules: `app.py` (server + routes), `payments.py` (Stripe), `mailer.py` (SMTP), `seed.py`.
