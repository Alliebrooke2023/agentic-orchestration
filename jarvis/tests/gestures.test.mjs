// node --test jarvis/tests
import test from "node:test";
import assert from "node:assert/strict";
import { classify, Holder, pinchInfo } from "../gestures.js";
import { makeHand, H } from "./fake_hands.mjs";

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
