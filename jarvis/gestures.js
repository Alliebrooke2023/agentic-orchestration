// jarvis/gestures.js -- pure hand-gesture math. 21 MediaPipe landmarks {x,y,z}.
export const FINGERS = { thumb: [1, 2, 3, 4], index: [5, 6, 7, 8], middle: [9, 10, 11, 12], ring: [13, 14, 15, 16], pinky: [17, 18, 19, 20] };

export function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y, (a.z || 0) - (b.z || 0));
}

// palm size: wrist -> middle-finger knuckle. Makes everything distance-independent.
export function handScale(lm) {
  return dist(lm[0], lm[9]) || 1e-6;
}

export function extended(lm) {
  const w = lm[0], s = handScale(lm), out = {};
  for (const [name, [, pip, , tip]] of Object.entries(FINGERS)) {
    if (name === "thumb") continue;
    out[name] = dist(w, lm[tip]) > dist(w, lm[pip]) * 1.15;
  }
  out.thumb = dist(lm[4], lm[9]) > s * 0.55 && dist(lm[4], lm[17]) > dist(lm[2], lm[17]) * 1.05;
  return out;
}

export function pinchInfo(lm) {
  const s = handScale(lm);
  const d = dist(lm[4], lm[8]) / s;
  // a fist also brings thumb near index: in a pinch the index tip stays out past its middle joint
  const indexOut = dist(lm[0], lm[8]) > s * 0.75 && dist(lm[0], lm[8]) > dist(lm[0], lm[6]) * 0.8;
  return {
    pinching: d < 0.28 && indexOut,
    strength: Math.max(0, Math.min(1, 1 - d / 0.6)),
    point: { x: (lm[4].x + lm[8].x) / 2, y: (lm[4].y + lm[8].y) / 2, z: ((lm[4].z || 0) + (lm[8].z || 0)) / 2 },
  };
}

export function classify(lm) {
  if (!lm || lm.length < 21) return "none";
  if (pinchInfo(lm).pinching) return "pinch";
  const e = extended(lm);
  const key = [e.index, e.middle, e.ring, e.pinky].map(Number).join("");
  if (key === "1111") return e.thumb ? "open" : "four";
  if (key === "0000") return e.thumb ? "thumbs_up" : "fist";
  return { "1000": "point", "1100": "victory", "1110": "three", "1001": "rock", "0001": "pinky" }[key] || "unknown";
}

// fires once when the same gesture is held `holdMs`; then waits `cooldownMs`.
export class Holder {
  constructor(holdMs = 1000, cooldownMs = 3000) {
    Object.assign(this, { holdMs, cooldownMs, cur: "none", since: 0, last: -1e9, fired: false });
  }
  update(g, now) {
    if (g !== this.cur) { this.cur = g; this.since = now; this.fired = false; }
    const held = now - this.since;
    const progress = Math.min(1, held / this.holdMs);
    if (!this.fired && held >= this.holdMs && now - this.last >= this.cooldownMs && !["none", "unknown", "pinch"].includes(g)) {
      this.fired = true; this.last = now;
      return { fire: g, progress };
    }
    return { fire: null, progress: this.fired ? 1 : progress };
  }
}
