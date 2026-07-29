"""Solver/environment configuration for lsdyna-kagent.

Resolution order for every setting: environment variable > user config file > default.
User config file: ~/.lsdyna-kagent.json  (optional), e.g.
    {"solver_bin": "C:\\LSDYNA\\bin", "mpiexec": "C:\\Program Files\\Microsoft MPI\\Bin\\mpiexec.exe"}
"""
import json
import os
from pathlib import Path

DEFAULT_SOLVER_BIN = r"C:\Program Files\ANSYS Inc\v242\ansys\bin\winx64"
DEFAULT_MPIEXEC = r"C:\Program Files\Microsoft MPI\Bin\mpiexec.exe"

# Solver executables shipped with ANSYS 2024R2 (LS-DYNA R14.1.1)
SOLVER_EXE = {
    ("smp", "sp"): "lsdyna_sp.exe",
    ("smp", "dp"): "lsdyna_dp.exe",
    ("mpp", "sp"): "lsdyna_mpp_sp_msmpi.exe",
    ("mpp", "dp"): "lsdyna_mpp_dp_msmpi.exe",
}

SOLVER_VERSION = "R14.1.1"  # keywords newer than this release must not be used


def _user_config():
    p = Path.home() / ".lsdyna-kagent.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def solver_bin():
    cfg = _user_config()
    return os.environ.get("LSDYNA_BIN") or cfg.get("solver_bin") or DEFAULT_SOLVER_BIN


def mpiexec_path():
    cfg = _user_config()
    return os.environ.get("LSDYNA_MPIEXEC") or cfg.get("mpiexec") or DEFAULT_MPIEXEC


def solver_path(mode="smp", precision="sp"):
    exe = SOLVER_EXE[(mode, precision)]
    return str(Path(solver_bin()) / exe)


if __name__ == "__main__":
    for (mode, prec), exe in SOLVER_EXE.items():
        p = Path(solver_bin()) / exe
        print(f"{mode}/{prec}: {p}  {'OK' if p.is_file() else 'MISSING'}")
    mp = Path(mpiexec_path())
    print(f"mpiexec: {mp}  {'OK' if mp.is_file() else 'MISSING'}")
