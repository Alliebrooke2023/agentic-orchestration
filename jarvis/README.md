# Jarvis — 3D hand motion for the swarm

Webcam hand tracking (MediaPipe, 21 joints x 2 hands) drawn as a 3D hologram (three.js).
Gestures drive a holographic object and fire swarm commands. Runs fully local after first install.

## Run (Windows)
    cd C:\swarm\jarvis
    .\jarvis.bat        (1 = install, 2 = run)
or
    python jarvis.py

Opens http://127.0.0.1:8770 — allow the camera.

## Gestures
| gesture | does |
|---|---|
| pinch + drag | rotate hologram |
| pinch with both hands | zoom |
| open palm (hold 1s) | reset |
| fist (hold 1s) | `health report` |
| victory | `ollama status` |
| three fingers | `sunshine status` |
| thumbs up | `stack status` |
| rock (index + pinky) | `process mail` |

Edit `jarvis.json` to remap. Only commands listed there can run.

## Safety
- Binds 127.0.0.1 only. Rejects command requests from other websites (Origin check).
- Downloads are pinned and hash-checked (npm sha512, model sha256) into `vendor/`.
- 3s cooldown between commands.

## Swarm location
Auto-finds `..\swarm`, `..`, or `C:\swarm`. Override: `python jarvis.py --swarm D:\path`.

## Tests
    python -m unittest discover -s tests
    node --test tests/gestures.test.mjs
