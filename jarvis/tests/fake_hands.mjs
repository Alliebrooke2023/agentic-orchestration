// jarvis/tests/fake_hands.mjs -- synthetic MediaPipe landmarks shared by unit + smoke tests
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
export const H = (s) => Object.fromEntries(["thumb", "index", "middle", "ring", "pinky"].map((k, i) => [k, s[i] === "1"]));
