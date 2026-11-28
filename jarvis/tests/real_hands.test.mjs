// node --test tests/real_hands.test.mjs  -- landmarks from MediaPipe on real photos (640x480), same model as the HUD
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { classify } from "../gestures.js";

const fx = JSON.parse(fs.readFileSync(new URL("./real_hands.json", import.meta.url), "utf8"));

test("real hands classify right (a real fist is not a pinch)", () => {
  for (const [want, lm] of Object.entries(fx)) assert.equal(classify(lm), want, want);
});
