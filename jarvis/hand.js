// jarvis/hand.js -- HUD logic. Camera turns ON only by a tap. Nothing is stored or sent.
import * as THREE from "./vendor/three.module.js";
import { classify, pinchInfo, Holder } from "./gestures.js";
import { camOptions, pickCam } from "./cams.js";
const $ = (id) => document.getElementById(id), TEST = location.search.includes("test=1");
const log = (h) => { $("log").innerHTML = h + "\n" + $("log").innerHTML.slice(0, 6000); };
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);

// ---- scene
const r = new THREE.WebGLRenderer({ canvas: $("c"), antialias: true, alpha: true, preserveDrawingBuffer: true });
r.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
cam.position.z = 6;
const C = 0x3df2ff, W = 0xffb547, mat = (c, o = 1) => new THREE.MeshBasicMaterial({ color: c, wireframe: true, transparent: true, opacity: o });
const holo = new THREE.Group(); scene.add(holo);
holo.add(new THREE.Mesh(new THREE.IcosahedronGeometry(1, 1), mat(C, 0.9)));
holo.add(new THREE.Mesh(new THREE.IcosahedronGeometry(0.45, 0), mat(W, 0.9)));
for (let i = 0; i < 3; i++) {
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.5 + i * 0.25, 0.008, 6, 96), new THREE.MeshBasicMaterial({ color: C, transparent: true, opacity: 0.5 - i * 0.12 }));
  ring.rotation.x = Math.PI / 2 + i * 0.5; ring.rotation.y = i * 0.7; holo.add(ring);
}
const pts = new THREE.BufferGeometry(), pa = new Float32Array(600 * 3);
for (let i = 0; i < pa.length; i++) pa[i] = (Math.random() - 0.5) * 9;
pts.setAttribute("position", new THREE.BufferAttribute(pa, 3));
scene.add(new THREE.Points(pts, new THREE.PointsMaterial({ color: C, size: 0.02, transparent: true, opacity: 0.5 })));
const BONES = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[0,17],[17,18],[18,19],[19,20]];
const hands = [0, 1].map(() => {
  const g = new THREE.Group(), joints = [];
  for (let i = 0; i < 21; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry([4,8,12,16,20].includes(i) ? 0.06 : 0.04, 10, 8), new THREE.MeshBasicMaterial({ color: C })); g.add(m); joints.push(m); }
  const lg = new THREE.BufferGeometry(); lg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(BONES.length * 6), 3));
  const lines = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: C, transparent: true, opacity: 0.8 })); g.add(lines);
  scene.add(g); return { g, joints, lines };
});
function resize() { r.setSize(innerWidth, innerHeight); cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); }
addEventListener("resize", resize); resize();
// normalized landmark -> world, mirrored like a selfie view. Matches the <video> object-fit:cover crop,
// so a 4:3 webcam on a 16:9 screen keeps the skeleton on top of your real hand.
function toWorld(p) {
  const h = 2 * Math.tan((cam.fov * Math.PI) / 360) * cam.position.z, w = h * cam.aspect;
  const v = $("v"), va = v.videoWidth && v.videoHeight ? v.videoWidth / v.videoHeight : cam.aspect;
  const fw = Math.max(w, h * va), fh = Math.max(h, w / va);
  return new THREE.Vector3((0.5 - p.x) * fw, (0.5 - p.y) * fh, -(p.z || 0) * fw * 1.5);
}

// ---- interaction state
const holder = new Holder(1000, 1500), vel = { x: 0.004, y: 0.006 };
let target = 1, lastPinch = null, lastTwo = null, map = {};
const goal = new THREE.Vector3(); // point = the object follows your index fingertip in 3D
fetch("config").then((x) => x.json()).then((c) => {
  map = c.commands || {};
  $("map").innerHTML = Object.entries(map).map(([g, cmd]) => `<div>${esc(g)} → ${esc(cmd)}</div>`).join("") + "<div>hold 1s to propose · thumbs-up = YES · open palm = NO/reset</div><div>pinch+drag → rotate · 2-hand pinch → zoom</div>" + (c.swarm ? "" : "<div style='color:var(--w)'>swarm not found: commands disabled</div>");
}).catch(() => {});
// ---- YES gate: a gesture only proposes; thumbs-up or the YES button runs it. One action, one yes.
let pending = null, pendTimer = 0;
function ask(g) {
  pending = g; $("askq").textContent = `Run "${map[g]}"?`; $("ask").classList.add("on");
  clearTimeout(pendTimer); pendTimer = setTimeout(() => answer(false), 8000);
}
async function answer(yes) {
  const g = pending; pending = null; $("ask").classList.remove("on"); clearTimeout(pendTimer);
  if (!g) return;
  if (!yes) return log(`<b>${esc(g)}</b> cancelled`);
  log(`<b>${esc(g)}</b> → ${esc(map[g])} …`);
  try {
    const res = await fetch("cmd", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ gesture: g }) });
    const j = await res.json(); log(esc(j.output || j.error || ""));
  } catch (e) { log("error: " + esc(e)); }
}
$("yes").onclick = () => answer(true);
$("no").onclick = () => answer(false);
function fire(g) {
  if (pending) { if (g === "thumbs_up") answer(true); else if (g === "open") answer(false); return; }
  if (g === "open") { holo.rotation.set(0, 0, 0); holo.position.set(0, 0, 0); goal.set(0, 0, 0); target = 1; vel.x = 0.004; vel.y = 0.006; return log("<b>reset</b>"); }
  if (map[g]) ask(g);
}

function onHands(list, now) {
  hands.forEach((h, i) => {
    const lm = list[i]; h.g.visible = !!lm; if (!lm) return;
    const v = lm.map(toWorld), pinch = pinchInfo(lm).pinching, col = pinch ? W : C;
    v.forEach((p, j) => { h.joints[j].position.copy(p); h.joints[j].material.color.setHex(col); });
    const a = h.lines.geometry.attributes.position;
    BONES.forEach(([s, e], k) => { a.setXYZ(k * 2, v[s].x, v[s].y, v[s].z); a.setXYZ(k * 2 + 1, v[e].x, v[e].y, v[e].z); });
    a.needsUpdate = true; h.lines.material.color.setHex(col);
  });
  const gs = list.map(classify), pin = list.map((lm) => pinchInfo(lm));
  if (pin.length === 2 && pin[0].pinching && pin[1].pinching) {
    const d = Math.hypot(pin[0].point.x - pin[1].point.x, pin[0].point.y - pin[1].point.y);
    if (lastTwo) target = Math.min(3, Math.max(0.3, target * (d / lastTwo)));
    lastTwo = d; lastPinch = null;
  } else if (pin[0]?.pinching) {
    lastTwo = null; const p = pin[0].point;
    if (lastPinch) { vel.y = -(p.x - lastPinch.x) * 6; vel.x = (p.y - lastPinch.y) * 6; }
    lastPinch = p;
  } else { lastPinch = lastTwo = null; }
  if (gs[0] === "point") {
    const tip = toWorld(list[0][8]);
    goal.set(tip.x * 0.8, tip.y * 0.8, Math.max(-3, Math.min(2, tip.z * 2)));
  }
  const g = gs[0] || "none", st = holder.update(g, now);
  $("g").textContent = gs.length ? gs.join(" + ") : "no hands";
  $("bar").firstChild.style.width = (["none", "unknown", "pinch"].includes(g) ? 0 : st.progress * 100) + "%";
  if (st.fire) fire(st.fire);
}

let hasHands = false;
function frame(now) {
  holo.rotation.x += vel.x; holo.rotation.y += vel.y;
  if (!lastPinch) { vel.x += (0.002 - vel.x) * 0.02; vel.y += (0.004 - vel.y) * 0.02; }
  const s = holo.scale.x + (target - holo.scale.x) * 0.15; holo.scale.setScalar(s);
  holo.position.lerp(goal, 0.12);
  r.render(scene, cam); requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
window.jarvis = { feed: (list) => onHands(list, performance.now()), classify, holo, goal, answer, get pending() { return pending; } };

// ---- vision: OFF by default. Only a tap turns it ON. Code may turn it OFF, never ON.
let stream = null, lmk = null, live = false, lastSeen = 0, raf = 0;
const IDLE_OFF_MS = 5 * 60 * 1000;
function lamp(on) {
  $("lamp").textContent = on ? "CAMERA LIVE" : "CAMERA OFF"; $("lamp").classList.toggle("on", on);
  $("vis").textContent = on ? "Vision OFF" : "Vision ON";
}
function visionOff(why) {
  live = false; cancelAnimationFrame(raf);
  if (stream) stream.getTracks().forEach((t) => t.stop());
  stream = null; $("v").srcObject = null; lamp(false); onHands([], performance.now());
  $("g").textContent = "vision off"; if (why) log("vision off: " + esc(why));
}
async function loadModel() {
  const { FilesetResolver, HandLandmarker } = await import("./vendor/vision_bundle.mjs");
  const files = await FilesetResolver.forVisionTasks(new URL("vendor/wasm", location.href).href);
  const opts = (delegate) => ({ baseOptions: { modelAssetPath: "vendor/hand_landmarker.task", delegate }, runningMode: "VIDEO", numHands: 2 });
  try { return await HandLandmarker.createFromOptions(files, opts("GPU")); }
  catch { log("GPU busy or missing, using CPU"); return HandLandmarker.createFromOptions(files, opts("CPU")); }
}
// ---- camera picker: built-in or USB. Labels show once the browser has camera permission.
const store = { get: () => { try { return localStorage.getItem("jarvis.cam"); } catch { return null; } },
                set: (v) => { try { localStorage.setItem("jarvis.cam", v); } catch { /* private mode */ } } };
async function refreshCams() {
  let devs = [];
  try { devs = await navigator.mediaDevices.enumerateDevices(); } catch { /* no media api */ }
  const opts = camOptions(devs), sel = $("cam"), cur = sel.value || store.get();
  sel.innerHTML = opts.length ? "" : "<option value=''>no camera found</option>";
  for (const o of opts) { const el = document.createElement("option"); el.value = o.id; el.textContent = o.text; sel.appendChild(el); }
  const pick = pickCam(opts, cur); if (pick !== null) sel.value = pick;
  window.jarvis.cams = opts;
  return opts;
}
navigator.mediaDevices?.addEventListener?.("devicechange", () => refreshCams().then((o) => log(`cameras: ${o.length}`)));
$("cam").onchange = () => { store.set($("cam").value); if (live) { visionOff(); visionOn(); } }; // user's own pick
refreshCams();

async function visionOn() { // called only from a user action (button tap or camera pick while live)
  try {
    $("g").textContent = "starting";
    lmk = lmk || (await loadModel());
    const id = $("cam").value;
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, ...(id ? { deviceId: { exact: id } } : {}) }, audio: false });
    const label = stream.getVideoTracks()[0].label;
    await refreshCams(); // labels appear after permission
    const now = stream.getVideoTracks()[0].getSettings().deviceId; if (now) { $("cam").value = now; store.set(now); }
    log("camera: " + esc(label));
    const v = $("v"); v.srcObject = stream; await v.play();
    live = true; lastSeen = performance.now(); lamp(true); $("g").textContent = "online";
    stream.getVideoTracks()[0].onended = () => visionOff("camera ended");
    let lt = -1;
    const loop = () => {
      if (!live) return;
      const now = performance.now();
      if (v.currentTime !== lt) {
        lt = v.currentTime;
        const res = lmk.detectForVideo(v, now), found = res.landmarks || [];
        if (found.length) lastSeen = now;
        onHands(found, now); window.jarvis.frames = (window.jarvis.frames || 0) + 1;
      }
      if (now - lastSeen > IDLE_OFF_MS) return visionOff("no hands for 5 min");
      raf = requestAnimationFrame(loop);
    };
    loop();
  } catch (e) { visionOff(); $("err").textContent = "camera/model error: " + e; }
}
$("vis").onclick = () => (live ? visionOff("tap") : visionOn());
document.addEventListener("visibilitychange", () => { if (document.hidden && live) visionOff("tab hidden"); });
addEventListener("keydown", (e) => { if (e.key === "Escape" && live) visionOff("Esc"); });
lamp(false);
$("g").textContent = TEST ? "test mode" : "vision off";
