"""CI: fail if swarm-cortex.zip or the installer payload drift from swarm/."""
import base64
import re
import subprocess
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]  # repo root
tracked = subprocess.run(["git", "ls-files", "swarm"], cwd=root, capture_output=True,
                         text=True, check=True).stdout.split()
zf = zipfile.ZipFile(root / "swarm-cortex.zip")
errors = []
names = set(zf.namelist())
for f in sorted(set(tracked) - names):
    errors.append(f"missing from zip: {f}")
for f in sorted(names - set(tracked)):
    errors.append(f"in zip but not in repo: {f}")
for f in sorted(names & set(tracked)):
    if zf.read(f) != (root / f).read_bytes():
        errors.append(f"stale in zip: {f}")
ps1 = (root / "swarm-cortex-setup.ps1").read_text()
m = re.search(r'FromBase64String\("([^"]*)"\)', ps1)
if not m or base64.b64decode(m.group(1)) != (root / "swarm-cortex.zip").read_bytes():
    errors.append("swarm-cortex-setup.ps1 payload != swarm-cortex.zip")
print("\n".join(errors) or "bundle in sync")
sys.exit(1 if errors else 0)
