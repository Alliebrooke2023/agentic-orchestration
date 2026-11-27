# AI Agent Builder for ASAP Protocol

Platform for building, configuring, and running AI agents with tool execution, workflows, and integrations.

## What it does

- **Agents & runs** — Manage agents and view execution history
- **Workflow builder** — Visual editor for workflow orchestration (React Flow)
- **Connectors** — Central registry for data and tool connections (OAuth, APIs, MCP)
- **Cross-platform integration** — Navigation and auth hand-off with ASAP Protocol
- **MCP** — Model Context Protocol server and tool management
- **Marketplace** — Discover and install integrations
- **Templates** — Reusable workflow and agent templates

## Tech stack

- **Runtime:** Next.js 16 (App Router), React 19, TypeScript
- **Styling:** Tailwind CSS 4
- **Backend / auth:** Supabase (PostgreSQL, Auth, Realtime)
- **AI:** Vercel AI SDK (`ai`, `@ai-sdk/react`)
- **UI:** Radix UI, shadcn-style components, Lucide icons
- **Forms / validation:** React Hook Form, Zod
- **Data:** SWR, Recharts
- **Workflow canvas:** React Flow (`@xyflow/react`)

### Cross-platform integration with ASAP Protocol

This app is integrated with ASAP Protocol to provide a unified marketplace and navigation experience.

Use the `/setup` route after starting the app to validate the connection and run migrations if needed.

## Jarvis 3D hand HUD

Webcam hand tracking (MediaPipe, 21 joints x 2 hands) drawn as a three.js hologram.
Gestures propose `swarm/` commands; nothing runs without a thumbs-up or the YES button.
Lives in `jarvis/`, separate from the Next.js app. Full guide: [`jarvis/README.md`](jarvis/README.md).

- Port: `127.0.0.1:8481` (local only)
- Camera: off on load, on only by your tap
- Ships inside the Cortex installer (`swarm-cortex.zip` -> `C:\swarm\jarvis`, setup menu option `J`)

Run (Windows):

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
node tests/smoke_hud.mjs
```

`smoke_hud.mjs` is the headless browser check (needs `vendor/` and Playwright; skips without them).

Rebuild the installer after changing `swarm/` or `jarvis/`:

```powershell
python .github/scripts/swarm_bundle.py build
```
