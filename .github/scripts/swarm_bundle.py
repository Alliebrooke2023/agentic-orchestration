"""Cortex installer bundle: swarm/** plus jarvis/** (as swarm/jarvis/**).

  python .github/scripts/swarm_bundle.py build   rewrite swarm-cortex.zip + the setup.ps1 payload
  python .github/scripts/swarm_bundle.py check   CI: fail if either drifted from the repo
"""
import base64
import io
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ZIP = ROOT / "swarm-cortex.zip"
PS1 = ROOT / "swarm-cortex-setup.ps1"
PAYLOAD = re.compile(r'FromBase64String\("([^"]*)"\)')


def expected():
    """{zip entry: repo path} for every tracked file that belongs in the bundle."""
    files = subprocess.run(["git", "ls-files", "swarm", "jarvis"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.split()
    return {(f if f.startswith("swarm/") else "swarm/" + f): f for f in files}


def build():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry, src in sorted(expected().items()):
            info = zipfile.ZipInfo(entry, date_time=(2026, 11, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, (ROOT / src).read_bytes())
    data = buf.getvalue()
    ZIP.write_bytes(data)
    ps1 = PS1.read_text()
    if not PAYLOAD.search(ps1):
        sys.exit("payload marker not found in swarm-cortex-setup.ps1")
    b64 = base64.b64encode(data).decode()
    PS1.write_text(PAYLOAD.sub(lambda _: f'FromBase64String("{b64}")', ps1, count=1))
    print(f"built {ZIP.name}: {len(expected())} files, {len(data)} bytes")


def check():
    want, zf, errors = expected(), zipfile.ZipFile(ZIP), []
    names = set(zf.namelist())
    errors += [f"missing from zip: {e}" for e in sorted(set(want) - names)]
    errors += [f"in zip but not in repo: {e}" for e in sorted(names - set(want))]
    errors += [f"stale in zip: {e}" for e in sorted(names & set(want))
               if zf.read(e) != (ROOT / want[e]).read_bytes()]
    m = PAYLOAD.search(PS1.read_text())
    if not m or base64.b64decode(m.group(1)) != ZIP.read_bytes():
        errors.append("swarm-cortex-setup.ps1 payload != swarm-cortex.zip")
    print("\n".join(errors) or "bundle in sync")
    if errors:
        print("fix: python .github/scripts/swarm_bundle.py build")
    return 1 if errors else 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit(build() if cmd == "build" else check())
