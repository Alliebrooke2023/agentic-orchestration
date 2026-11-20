---
name: driftrack-add-feature
description: Add a feature to DriftRack end to end (database, API, UI, test). Use for any new marketplace capability such as bundles, shipping options, reports or follows.
---

# Add a DriftRack feature

1. **Schema** - add `CREATE TABLE IF NOT EXISTS` (or a guarded `ALTER TABLE`) in `SCHEMA`
   in `app.py`. Existing databases must keep working.
2. **API** - write `h_<name>(ctx, ...)`. Call `ctx.auth()` if login is needed, validate
   with `need()`, use `?` SQL parameters, check ownership before any change. Add to `ROUTES`.
3. **UI** - add a `page*` function or extend one in `static/app.js`. Wrap handlers in
   `guard()`, run every dynamic value through `esc()`, write a real empty state.
4. **Test** - add a case to `tests/test_api.py` covering success, a bad input,
   and another user trying to do it.
5. **Docs** - update the matching section of `MANUAL.md`.
6. Run the `driftrack-run` skill before calling it done.
