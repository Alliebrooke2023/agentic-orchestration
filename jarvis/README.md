# Jarvis — 3D hand motion for the swarm / Aria stack

Webcam hand tracking (MediaPipe, 21 joints x 2 hands) drawn as a 3D hologram (three.js).
Gestures drive the hologram and propose swarm commands behind a YES gate.

## Run (Windows)
    cd C:\swarm\jarvis
    .\jarvis.bat        (1 = install, 2 = run)
or
    python jarvis.py

Opens http://127.0.0.1:8481. Tap **Vision ON** to start the camera.

## Aria rules it follows
- **Vision ON only by your tap.** Page loads with the camera off. Lamp badge is red while live.
  Turns OFF on: tap, Esc, tab hidden, camera unplugged, 5 min with no hands. Nothing turns it ON.
- **YES gate.** A held gesture only *proposes* a command. Thumbs-up or the YES button runs it.
  Open palm, NO, or 8 s of nothing cancels. One action, one yes.
- **Local lane.** Frames and hand points stay in browser memory. Never saved, logged or sent.
  (Hand geometry counts as biometric under Illinois BIPA — this keeps none.)
- **Private build.** No CDNs, strict CSP, server binds 127.0.0.1, rejects other websites (Origin check).
  Only the one-time install downloads libs (pinned + hash-checked) into `vendor/`.
- **Weak hardware.** 640x480, tries GPU then falls back to CPU (Cortex has no usable GPU).

## Gestures
| gesture | does |
|---|---|
| pinch + drag | rotate hologram |
| pinch with both hands | zoom |
| open palm (hold 1s) | reset / NO |
| thumbs-up (hold 1s) | YES to a pending command |
| fist | propose `health report` |
| victory | propose `ollama status` |
| three fingers | propose `sunshine status` |
| rock (index + pinky) | propose `process mail` |
| pinky | propose `stack status` |

Edit `jarvis.json` to remap. Only commands listed there can run. `thumbs_up` and `open` are reserved.

## Ports
8481 (next free slot after Aria Eyes 8479). Change with `--port`.

## Swarm location
Auto-finds `..\swarm`, `..`, or `C:\swarm`. Override: `python jarvis.py --swarm D:\path`.

## Tests
    python -m unittest discover -s tests
    node --test tests/gestures.test.mjs
