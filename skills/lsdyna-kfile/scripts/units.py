"""Consistent unit systems for LS-DYNA and SI-based conversion.

LS-DYNA has no built-in units; the deck must use one consistent system.
Materials in knowledge/materials.json are stored in SI (m-kg-s-Pa-K) and are
converted to the target system here.

CLI:
    python units.py list
    python units.py convert <system> <dimension> <si_value>
    python units.py material <system> <material_name>          # convert whole material
"""
import json
import sys
from pathlib import Path

# length, mass, time factors: value_in_system = value_SI * factor
# e.g. 1 m = 1000 mm -> length factor 1000 for mm systems.
UNIT_SYSTEMS = {
    "m-kg-s": {
        "desc": "SI: m, kg, s, N, Pa, J; density kg/m^3 (steel 7850)",
        "L": 1.0, "M": 1.0, "T": 1.0,
        "labels": {"length": "m", "mass": "kg", "time": "s", "force": "N",
                   "stress": "Pa", "energy": "J", "density": "kg/m^3",
                   "velocity": "m/s", "accel": "m/s^2"},
        "gravity": 9.81,
    },
    "mm-ton-s": {
        "desc": "mm, ton(Mg), s, N, MPa, N*mm(mJ); density ton/mm^3 (steel 7.85e-9)",
        "L": 1.0e3, "M": 1.0e-3, "T": 1.0,
        "labels": {"length": "mm", "mass": "ton", "time": "s", "force": "N",
                   "stress": "MPa", "energy": "N*mm", "density": "ton/mm^3",
                   "velocity": "mm/s", "accel": "mm/s^2"},
        "gravity": 9810.0,
    },
    "mm-kg-ms": {
        "desc": "mm, kg, ms, kN, GPa, J; density kg/mm^3 (steel 7.85e-6); v in mm/ms = m/s",
        "L": 1.0e3, "M": 1.0, "T": 1.0e3,
        "labels": {"length": "mm", "mass": "kg", "time": "ms", "force": "kN",
                   "stress": "GPa", "energy": "J", "density": "kg/mm^3",
                   "velocity": "mm/ms", "accel": "mm/ms^2"},
        "gravity": 9.81e-3,
    },
    "cm-g-us": {
        "desc": "cm, g, us, Mbar; density g/cm^3 (steel 7.85); v in cm/us (1=10km/s). For detonation/hypervelocity",
        "L": 1.0e2, "M": 1.0e3, "T": 1.0e6,
        "labels": {"length": "cm", "mass": "g", "time": "us", "force": "1e7 N",
                   "stress": "Mbar", "energy": "1e5 J", "density": "g/cm^3",
                   "velocity": "cm/us", "accel": "cm/us^2"},
        "gravity": 9.81e-10,
    },
}

# dimension -> (M exponent, L exponent, T exponent); temperature passes through (K)
DIMENSIONS = {
    "length":        (0, 1, 0),
    "mass":          (1, 0, 0),
    "time":          (0, 0, 1),
    "density":       (1, -3, 0),
    "stress":        (1, -1, -2),   # also pressure, modulus
    "force":         (1, 1, -2),
    "energy":        (1, 2, -2),
    "velocity":      (0, 1, -1),
    "accel":         (0, 1, -2),
    "strain_rate":   (0, 0, -1),    # 1/time
    "specific_heat": (0, 2, -2),    # J/(kg*K) -> L^2 T^-2 (per K)
    "energy_per_volume": (1, -1, -2),  # e.g. EOS E0, same as stress
    "viscosity":     (1, -1, -1),   # Pa*s
    "temperature":   None,          # no conversion (Kelvin everywhere)
    "dimensionless": (0, 0, 0),
}


def factor(system, dimension):
    """Multiply an SI value by this to get the value in `system`."""
    if dimension not in DIMENSIONS:
        raise KeyError(f"unknown dimension '{dimension}'; known: {sorted(DIMENSIONS)}")
    dim = DIMENSIONS[dimension]
    if dim is None:
        return 1.0
    m, l, t = dim
    s = UNIT_SYSTEMS[system]
    return (s["M"] ** m) * (s["L"] ** l) * (s["T"] ** t)


def convert(system, dimension, si_value):
    return si_value * factor(system, dimension)


def convert_material(system, mat):
    """Convert a material dict from materials.json ({param: {value, dim, ...}}) to target system."""
    out = {"name": mat.get("name"), "model": mat.get("model"), "unit_system": system,
           "note": mat.get("note", "")}
    params = {}
    for key, spec in mat.get("params", {}).items():
        v = convert(system, spec["dim"], spec["value"])
        params[key] = v
    out["params"] = params
    if "curves" in mat:
        out["curves"] = {}
        for cname, cur in mat["curves"].items():
            fx = factor(system, cur["x_dim"])
            fy = factor(system, cur["y_dim"])
            out["curves"][cname] = {
                "x_dim": cur["x_dim"], "y_dim": cur["y_dim"],
                "points": [[x * fx, y * fy] for x, y in cur["points"]],
            }
    return out


def _materials_db():
    p = Path(__file__).resolve().parent.parent / "knowledge" / "materials.json"
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv):
    if not argv or argv[0] == "list":
        for name, s in UNIT_SYSTEMS.items():
            print(f"{name:10s} {s['desc']}  (gravity={s['gravity']:g})")
        return 0
    cmd = argv[0]
    if cmd == "convert":
        system, dimension, val = argv[1], argv[2], float(argv[3])
        print(f"{convert(system, dimension, val):.6g}")
        return 0
    if cmd == "material":
        system, name = argv[1], argv[2]
        db = _materials_db()
        if name not in db:
            print(f"unknown material '{name}'. available: {', '.join(sorted(db))}", file=sys.stderr)
            return 1
        print(json.dumps(convert_material(system, db[name]), indent=2))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
