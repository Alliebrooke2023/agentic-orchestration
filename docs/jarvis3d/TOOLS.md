# Jarvis 3D tools and models

What each part of the build runs on. All local; nothing leaves the machine at run time.

## Runtime

| Piece                  | Version / source                                 | Used for                                  |
| ---------------------- | ------------------------------------------------ | ----------------------------------------- |
| Python                 | 3.9+ (CI uses 3.12), stdlib only                 | `jarvis.py` server on 8481                |
| MediaPipe Tasks Vision | `@mediapipe/tasks-vision` 0.10.14, sha512 pinned | hand tracking in the browser              |
| Hand model             | `hand_landmarker.task` float16 v1, sha256 pinned | 21 joints x 2 hands                       |
| three.js               | 0.160.0, sha512 pinned                           | 3D hologram + hand skeleton               |
| Browser                | Chrome / Edge with webcam permission             | runs the HUD, GPU then CPU                |
| Swarm                  | `swarm/` package, `python -m swarm <cmd>`        | commands behind the YES gate              |
| Ollama (optional)      | `127.0.0.1:11434`                                | swarm LLM backend; offline fallback works |

Libs download once into `jarvis/vendor/` (`python jarvis.py --fetch`, about 38 MB).

## Build and test

| Tool                      | Used for                                               |
| ------------------------- | ------------------------------------------------------ |
| `python -m unittest`      | server tests (`jarvis/tests/test_jarvis.py`)           |
| `node --test` (Node 22)   | gesture + camera-list tests                            |
| GitHub Actions            | `ci.yml`, `swarm.yml`, `jarvis.yml` (ubuntu + windows) |
| Playwright (repo dev dep) | planned browser smoke test (plan step 6)               |

## Agents / models working the plan

| Step    | Agent                               | Model                                                |
| ------- | ----------------------------------- | ---------------------------------------------------- |
| 1       | You (merge)                         | none                                                 |
| 2       | Thread: Build and test Jarvis HUD   | Claude                                               |
| 3       | Thread: Wire Jarvis HUD into JARVIS | Claude; JARVIS uses its own swappable local backends |
| 5, 8, 9 | New thread after PR #8 merges       | Claude                                               |
| 6       | Step 2 thread or new thread         | Claude + headless Chromium                           |
| 7       | You on Cortex                       | none                                                 |

## Ports

| Port  | Service             |
| ----- | ------------------- |
| 8481  | Jarvis HUD          |
| 8479  | Aria Eyes           |
| 5055  | JARVIS / dash agent |
| 8765  | CamWall             |
| 11434 | Ollama              |
