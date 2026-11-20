---
name: driftrack-run
description: Launch DriftRack locally, load demo data, and verify it works. Use when asked to run, start, demo, or smoke-test the marketplace.
---

# Run DriftRack

1. From `driftrack/`: `python -m unittest discover -s tests` - must end in `OK`.
2. Start: `python app.py --seed` (port 8750; override with `DRIFTRACK_PORT`).
3. Check `GET /api/ads` returns JSON and `GET /` returns 200.
4. Browser pass: log in as `demo` / `demo123`, open `#/dashboard`, confirm the stats
   count up, the chart draws, and the ad band scrolls.
5. Check a 390px wide viewport: no sideways page scroll, tab bar visible.

Never delete `data/` to "fix" something without asking the owner first.
