---
name: driftrack-theme
description: Re-skin DriftRack - colours, name, tagline, motion, sale-ad band. Use when asked to rebrand, restyle or change the look.
---

# Re-theme DriftRack

- **Palette**: edit the variables in `:root` of `static/style.css`. `--grad` drives buttons,
  chips and accents. Keep body text contrast at 4.5:1 or better on `--bg`.
- **Background motion**: `.aurora` (colour clouds) in CSS, `startSky()` (floating lights) in `app.js`.
- **Ad band**: `.ticker` in CSS; speed is set in `loadTicker()`.
- **Dashboard banner**: `.dash-hero` gradient and `.wordwall`; words come from `wall` in `pageDashboard()`.
- **Name**: `static/index.html` (title, brand), hero copy in `pageHome()`, `static/logo.svg`.
- Seed images take their colours from `PALETTES` in `seed.py`.

Always keep the `prefers-reduced-motion` block working, then screenshot desktop (1280px)
and phone (390px) to check the result.
