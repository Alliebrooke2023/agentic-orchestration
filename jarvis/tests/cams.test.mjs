// node --test jarvis/tests/cams.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { camOptions, pickCam } from "../cams.js";

const dev = (deviceId, label, kind = "videoinput") => ({ deviceId, label, kind });

test("labels built-in vs usb, skips audio", () => {
  const o = camOptions([dev("a", "HP TrueVision HD Camera"), dev("m", "Mic", "audioinput"), dev("b", "Logitech C920")]);
  assert.deepEqual(o.map((x) => x.kind), ["built-in", "usb"]);
  assert.equal(o[1].text, "USB · Logitech C920");
});

test("no labels before permission", () => {
  const o = camOptions([dev("", ""), dev("", "")]);
  assert.deepEqual(o.map((x) => x.label), ["Camera 1", "Camera 2"]);
  assert.equal(o[0].kind, "unknown");
});

test("pick: saved, then usb, then first", () => {
  const o = camOptions([dev("a", "Integrated Webcam"), dev("b", "USB2.0 Camera")]);
  assert.equal(pickCam(o, "a"), "a");
  assert.equal(pickCam(o, "gone"), "b");
  assert.equal(pickCam(camOptions([dev("a", "Integrated Webcam")]), null), "a");
  assert.equal(pickCam([], "a"), null);
});
