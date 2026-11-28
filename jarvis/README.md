# Jarvis — 3D hand motion for the swarm / Aria stack

Webcam hand tracking (MediaPipe, 21 joints x 2 hands) drawn as a 3D hologram (three.js).
Gestures drive the hologram and propose swarm commands behind a YES gate.

## Run (Windows)
    cd C:\swarm\jarvis
    .\jarvis.bat        (1 = install, 2 = run)
or
    python jarvis.py

Opens http://127.0.0.1:8481. Pick a camera (top right), tap **Vision ON**.

## Camera: PC or USB
- The dropdown lists every camera: built-in (laptop) and USB webcams.
- Names show after the first permission prompt. Before that: "Camera 1, 2…".
- Default: your last pick, else a USB cam, else the first one. Remembered per browser.
- Plug in a USB cam while running: the list refreshes by itself.
- Switch cameras while live: pick another one, the stream restarts on it.
- Capture cards (DVI/HDMI) show up here too if Windows sees them as a webcam.

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
| point (index only) | move hologram — it follows your fingertip in 3D |
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
    node --test tests/gestures.test.mjs tests/cams.test.mjs tests/real_hands.test.mjs
    node tests/smoke_hud.mjs      (headless browser: YES gate, camera-off, no outside calls; needs Playwright)
