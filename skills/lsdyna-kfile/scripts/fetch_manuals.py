"""Download the official LS-DYNA keyword manuals (Ansys/LST, free downloads)
into knowledge/manuals/ and build the keyword page index.

Sources (https://lsdyna.ansys.com/manuals-download/):
  Vol I  - keywords          Vol II - material models
R16 chosen: closest release on the official site to the local solver (R14.1.1).
"""
import subprocess
import sys
from pathlib import Path

MANUALS = {
    "LS-DYNA_Manual_Vol_I_R16.pdf":
        "https://lsdyna.ansys.com/wp-content/uploads/2025/04/LS-DYNA_Manual_Vol_I_R16.pdf",
    "LS-DYNA_Manual_Vol_II_R16.pdf":
        "https://lsdyna.ansys.com/wp-content/uploads/2025/04/LS-DYNA_Manual_Vol_II_R16.pdf",
}

dest = Path(__file__).resolve().parent.parent / "knowledge" / "manuals"
dest.mkdir(parents=True, exist_ok=True)
for name, url in MANUALS.items():
    target = dest / name
    if target.is_file() and target.stat().st_size > 1_000_000:
        print(f"already present: {name}")
        continue
    print(f"downloading {name} ...")
    r = subprocess.run(["curl", "-sL", "-o", str(target), url])
    if r.returncode or target.stat().st_size < 1_000_000:
        print(f"FAILED: {name} (get it manually from lsdyna.ansys.com/manuals-download)")
        sys.exit(1)
print("building keyword index ...")
subprocess.run([sys.executable, str(Path(__file__).parent / "manual_index.py"), "build"])
