# Jarvis 3D build plan

What's left to make the Jarvis 3D hand-motion HUD complete and usable on Cortex / Aria Base.
Code lives in `jarvis/` on PR #8 (`claude/jarvis-hands-security`). Status as of 2026-11-27.

## Where it stands

- HUD: MediaPipe hands (21 joints x 2) drawn in three.js, served by `jarvis.py` on
  `127.0.0.1:8481`.
- Gestures propose swarm commands; thumbs-up or YES runs them (YES gate).
- Tests on PR #8 head pass here: 8 Python (server) + 7 Node (gestures, camera list).
- All 5 mapped swarm commands (`health report`, `ollama status`, `sunshine status`,
  `process mail`, `stack status`) route to the right agent offline.
- CI green on PR #8 (check, test ubuntu + windows, Jarvis workflow). PR is still a draft.

## Steps

| #   | Step                                                                             | Who                          | Status                    |
| --- | -------------------------------------------------------------------------------- | ---------------------------- | ------------------------- |
| 1   | Mark PR #8 ready, merge into main                                                | You (yes needed)             | Waiting on you            |
| 2   | Build + test HUD standalone in a container, ship a download zip                  | Thread: Build and test HUD   | In progress               |
| 3   | Wire HUD into JARVIS / dash agent (port 5055)                                    | Thread: Wire HUD into JARVIS | In progress               |
| 4   | Decide PR #5: close it, or rebase after #8 (both edit camwall + lockfile)        | You                          | Open                      |
| 5   | Add `jarvis/` to the Cortex installer (`swarm-cortex.zip` + setup menu)          | Claude (this thread)         | Done on PR #8 (`d719771`) |
| 6   | Browser smoke test: load `hand.html?test=1`, feed fake landmarks, check YES gate | Claude (this thread)         | Done on PR #8: 8/8 pass   |
| 7   | Real camera test on Cortex: built-in + USB cam, GPU then CPU fallback            | You, on Cortex               | Not started               |
| 8   | Root README: add a Jarvis section (run, port 8481, tests)                        | Claude (this thread)         | Done on PR #8 (`d719771`) |
| 9   | `jarvis.bat`: fall back to `py -3` when `python` isn't on PATH                   | Claude (this thread)         | Done on PR #8 (`d719771`) |
| 10  | Optional: desktop shortcut / start-with-Windows for the HUD                      | You decide                   | Idea                      |

## Notes

- Steps 5, 6, 8, 9 were done on the PR #8 branch itself (2026-11-27), so they land with the merge.
- Installer bundle is now rebuilt with `python .github/scripts/swarm_bundle.py build`; CI runs `check`.
- PR #5 and PR #8 both change `camwall/camwall.py`, `package.json`, `pnpm-lock.yaml` and
  `src/lib/env-schema.ts`. Whichever merges second will conflict. PR #8 looks like the newer copy
  of the same camwall + dependency fixes (inferred from the diffs, not confirmed).
- Nothing here merges into main without your yes.
- Tools and models per step: see [TOOLS.md](TOOLS.md).

## Run it now (from PR #8)

```powershell
cd C:\swarm\jarvis
python jarvis.py --fetch
python jarvis.py
```

Tests:

```powershell
cd C:\swarm\jarvis
python -m unittest discover -s tests
node --test tests/gestures.test.mjs tests/cams.test.mjs
```
