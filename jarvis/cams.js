// jarvis/cams.js -- camera list helpers (pure, testable). Built-in vs USB is a label guess.
const BUILTIN = /integrated|built-?in|internal|facetime|truevision|hp hd|hp wide|front|user facing/i;

export function camOptions(devices) {
  let n = 0;
  return devices
    .filter((d) => d.kind === "videoinput")
    .map((d) => {
      n += 1;
      const label = d.label || `Camera ${n}`;
      const kind = !d.label ? "unknown" : BUILTIN.test(label) ? "built-in" : "usb";
      return { id: d.deviceId, label, kind, text: `${kind === "unknown" ? "" : kind.toUpperCase() + " · "}${label}` };
    });
}

// keep the saved choice if it is still plugged in, else prefer USB, else first.
export function pickCam(opts, savedId) {
  if (!opts.length) return null;
  return (opts.find((o) => o.id === savedId) || opts.find((o) => o.kind === "usb") || opts[0]).id;
}
