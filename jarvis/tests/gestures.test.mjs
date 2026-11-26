// node --test jarvis/tests
import test from "node:test";
import assert from "node:assert/strict";
import { classify, Holder, pinchInfo } from "../gestures.js";

// synthetic right hand, palm facing camera, fingers pointing up (image y grows down)
export function makeHand(ext, { pinch = false, ox = 0.5, oy = 0.8, s = 0.2 } = {}) {
  const P = (x, y, z = 0) => ({ x: ox + x * s, y: oy - y * s, z: z * s });
  const lm = [P(0, 0)];
  const fingerBase = { index: -0.35, middle: -0.1, ring: 0.12, pinky: 0.32 };
  // thumb 1-4
  lm.push(P(-0.3, 0.2), P(-0.5, 0.4), ext.thumb ? P(-0.7, 0.55) : P(-0.3, 0.55), ext.thumb ? P(-0.9, 0.7) : P(-0.1, 0.6));
  for (const [f, x] of Object.entries(fingerBase)) {
    if (ext[f]) lm.push(P(x, 1), P(x, 1.35), P(x, 1.6), P(x, 1.85));
    else lm.push(P(x, 1), P(x, 1.3, -0.2), P(x, 1.05, -0.3), P(x, 0.85, -0.2));
  }
  if (pinch) { lm[8] = P(-0.4, 1.2, -0.1); lm[7] = P(-0.4, 1.35); lm[4] = P(-0.42, 1.18, -0.08); lm[3] = P(-0.5, 0.9); }
  return lm;
}
const H = (s) => Object.fromEntries(["thumb", "index", "middle", "ring", "pinky"].map((k, i) => [k, s[i] === "1"]));

test("classifies static poses", () => {
  assert.equal(classify(makeHand(H("11111"))), "open");
  assert.equal(classify(makeHand(H("00000"))), "fist");
  assert.equal(classify(makeHand(H("10000"))), "thumbs_up");
  assert.equal(classify(makeHand(H("01000"))), "point");
  assert.equal(classify(makeHand(H("01100"))), "victory");
  assert.equal(classify(makeHand(H("01110"))), "three");
  assert.equal(classify(makeHand(H("01001"))), "rock");
  assert.equal(classify(makeHand(H("01111"))), "four");
});

test("pinch detected, fist is not a pinch", () => {
  assert.equal(classify(makeHand(H("00111"), { pinch: true })), "pinch");
  assert.equal(pinchInfo(makeHand(H("00000"))).pinching, false);
});

test("scale and position invariant", () => {
  for (const s of [0.08, 0.2, 0.4]) for (const ox of [0.2, 0.8]) {
    assert.equal(classify(makeHand(H("01100"), { s, ox })), "victory");
  }
});

test("holder fires once after hold, honors cooldown", () => {
  const h = new Holder(1000, 3000);
  assert.equal(h.update("fist", 0).fire, null);
  assert.equal(h.update("fist", 500).fire, null);
  assert.equal(h.update("fist", 1000).fire, "fist");
  assert.equal(h.update("fist", 1500).fire, null);
  h.update("victory", 1600);
  assert.equal(h.update("victory", 2700).fire, null); // cooldown
  assert.equal(h.update("victory", 4100).fire, "victory");
  h.update("pinch", 5000);
  assert.equal(h.update("pinch", 9000).fire, null);
  assert.equal(classify([]), "none");
});
