// jarvis/tests/smoke_hud.mjs -- plan step 6: headless browser smoke test of the HUD.
// Needs vendor/ (python jarvis.py --fetch) and Playwright. Skips cleanly without them.
//   node tests/smoke_hud.mjs
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import assert from "node:assert/strict";
import { makeHand, H } from "./fake_hands.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url)), ROOT = path.resolve(HERE, "..");
const PORT = 8497, BASE = `http://127.0.0.1:${PORT}`;
const skip = (why) => { console.log(`SKIP smoke: ${why}`); process.exit(0); };
if (!existsSync(path.join(ROOT, "vendor", "three.module.js"))) skip("vendor/ missing - run python jarvis.py --fetch");
let chromium;
try { ({ chromium } = await import("playwright")); }
catch { try { ({ chromium } = createRequire(import.meta.url)("playwright")); } catch { skip("playwright not installed"); } }

const py = process.platform === "win32" ? "python" : "python3";
const srv = spawn(py, ["jarvis.py", "--no-open", "--port", String(PORT)],
  { cwd: ROOT, stdio: ["ignore", "pipe", "inherit"] });
await new Promise((ok, bad) => { srv.stdout.on("data", (d) => String(d).includes(BASE) && ok()); srv.on("exit", bad); });

const results = [];
const check = async (name, fn) => {
  try { await fn(); results.push(`ok   ${name}`); }
  catch (e) { results.push(`FAIL ${name}: ${e.message.split("\n")[0]}`); process.exitCode = 1; }
};
const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const outside = [], errors = [];
page.on("request", (r) => { if (!r.url().startsWith(BASE) && !r.url().startsWith("data:")) outside.push(r.url()); });
page.on("pageerror", (e) => errors.push(e.message));
await page.addInitScript(() => {
  window.__gum = 0;
  const md = navigator.mediaDevices;
  if (md) md.getUserMedia = async () => { window.__gum++; throw new Error("blocked in smoke test"); };
});
await page.goto(`${BASE}/hand.html?test=1`);
await page.waitForFunction(() => window.jarvis && document.querySelector("#map").textContent.includes("health report"));

// hold one pose for ms, feeding frames like the camera loop would
const hold = (lm, ms) => page.evaluate(async ({ lm, ms }) => {
  const end = performance.now() + ms;
  while (performance.now() < end) { window.jarvis.feed(lm ? [lm] : []); await new Promise((r) => setTimeout(r, 33)); }
}, { lm, ms });
const FIST = makeHand(H("00000")), THUMB = makeHand(H("10000")), OPEN = makeHand(H("11111")), POINT = makeHand(H("01000"), { ox: 0.25 });

await check("loads with camera OFF and never asks for it", async () => {
  assert.equal(await page.textContent("#lamp"), "CAMERA OFF");
  assert.equal(await page.evaluate(() => window.__gum), 0);
});
await check("fist held 1s proposes, does not run", async () => {
  await hold(FIST, 1200);
  assert.equal(await page.evaluate(() => window.jarvis.pending), "fist");
  assert.ok(await page.$eval("#ask", (e) => e.classList.contains("on")));
  assert.match(await page.textContent("#askq"), /health report/);
});
await check("open palm cancels (NO)", async () => {
  await hold(OPEN, 1700);
  assert.equal(await page.evaluate(() => window.jarvis.pending), null);
  assert.match(await page.textContent("#log"), /fist<\/b> cancelled|fist cancelled/);
});
await check("thumbs-up YES runs the mapped command", async () => {
  await hold(null, 300); await hold(FIST, 1700);
  assert.equal(await page.evaluate(() => window.jarvis.pending), "fist");
  const res = page.waitForResponse((r) => r.url().endsWith("/cmd"));
  await hold(THUMB, 1700);
  const r = await res; assert.equal(r.status(), 200);
  assert.equal(await page.evaluate(() => window.jarvis.pending), null);
  await page.waitForFunction(() => document.querySelector("#log").textContent.includes("[health-report]"));
});
await check("pending command times out after 8s", async () => {
  await hold(null, 300); await hold(makeHand(H("01100")), 1700);
  assert.equal(await page.evaluate(() => window.jarvis.pending), "victory");
  await page.waitForTimeout(8300);
  assert.equal(await page.evaluate(() => window.jarvis.pending), null);
});
await check("point moves the hologram toward the fingertip", async () => {
  await hold(POINT, 800);
  const x = await page.evaluate(() => window.jarvis.goal.x);
  assert.ok(Math.abs(x) > 0.3, `goal.x=${x}`);
});
await check("Vision ON tap is the only thing that asks for the camera", async () => {
  await page.click("#vis");
  await page.waitForFunction(() => window.__gum === 1 || document.querySelector("#err").textContent, null, { timeout: 60000 });
  assert.equal(await page.textContent("#lamp"), "CAMERA OFF");
});
await check("no outside requests, no page errors", async () => {
  assert.deepEqual(outside, []); assert.deepEqual(errors, []);
});
await page.screenshot({ path: path.join(HERE, "..", "smoke.png") });
await browser.close(); srv.kill();
console.log(results.join("\n"));
