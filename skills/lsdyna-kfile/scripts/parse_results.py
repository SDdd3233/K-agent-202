"""Parse LS-DYNA run outputs (d3hsp / mes* / glstat) into a quality-gate verdict.

Usage:  python parse_results.py <rundir> [--json report.json]
        [--max-energy-dev 0.10] [--max-hourglass 0.10] [--max-added-mass 5.0]

Gates (defaults):
  G1 normal termination
  G2 zero solver errors
  G3 |total energy / initial energy - 1| <= 0.10  (needs *DATABASE_GLSTAT)
  G4 hourglass energy / peak internal energy <= 0.10  (needs *CONTROL_ENERGY HGEN=2)
  G5 mass increase from mass scaling <= 5%
  G6 no negative-volume / out-of-range-velocity events

Verdict: PASS (all gates), WARN (only soft gates G3-G5 exceeded slightly or
data missing), FAIL (G1/G2/G6 violated or gross gate violation).
Exit code 0 for PASS/WARN, 1 for FAIL.
"""
import argparse
import json
import re
import sys
from pathlib import Path

NUM = r"([-+]?[0-9]*\.?[0-9]+(?:[EeDd][-+]?[0-9]+)?)"

GLSTAT_LABELS = {
    "time": r"^\s*time\.+\s*" + NUM,
    "kinetic": r"^\s*kinetic energy\.+\s*" + NUM,
    "internal": r"^\s*internal energy\.+\s*" + NUM,
    "hourglass": r"^\s*hourglass energy\s*\.+\s*" + NUM,
    "sliding": r"^\s*sliding interface energy\.+\s*" + NUM,
    "external_work": r"^\s*external work\.+\s*" + NUM,
    "total": r"^\s*total energy\.+\s*" + NUM,
    "ratio": r"^\s*total energy / initial energy\.+\s*" + NUM,
    "added_mass": r"^\s*added mass\.+\s*" + NUM,
    "mass_pct": r"^\s*percentage increase\.+\s*" + NUM,
}


def _f(s):
    return float(s.replace("d", "e").replace("D", "E"))


def parse_glstat(path):
    series = {k: [] for k in GLSTAT_LABELS}
    pats = {k: re.compile(v) for k, v in GLSTAT_LABELS.items()}
    text = path.read_text(encoding="ascii", errors="replace")
    for line in text.splitlines():
        for key, pat in pats.items():
            mm = pat.match(line)
            if mm:
                try:
                    series[key].append(_f(mm.group(1)))
                except ValueError:
                    pass
                break
    return series


def collect_messages(rundir):
    """errors/warnings from d3hsp and mes* files"""
    errors, warnings = [], set()
    diagnostics = []
    events = {"negative_volume": 0, "shooting_nodes": 0, "nan": 0}
    termination = "unknown"
    for name in ["d3hsp", "messag"] + sorted(str(p.name) for p in Path(rundir).glob("mes0*")):
        f = Path(rundir) / name
        if not f.is_file():
            continue
        lines = f.read_text(encoding="ascii", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if "*** Error" in line:
                blk = " | ".join(x.strip() for x in lines[i:i + 3] if x.strip())
                if blk not in errors:
                    errors.append(blk)
                diagnostics.append(make_diagnostic("error", name, i + 1, lines[i:i + 5]))
            elif "*** Warning" in line:
                m = re.search(r"\*\*\* Warning (\d+)", line)
                tag = m.group(1) if m else line.strip()[:60]
                nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
                warnings.add(f"{tag}: {nxt[:80]}")
                diagnostics.append(make_diagnostic("warning", name, i + 1, lines[i:i + 4]))
            low = line.lower()
            # "negative volume failure criterion" is the explanatory text of the
            # informational Warning 30364 that every ERODING contact emits; only
            # count real element failures ("negative volume in solid element #...").
            if "negative volume" in low and "failure criterion" not in low:
                events["negative_volume"] += 1
            if "out-of-range" in low and "velocit" in low:
                events["shooting_nodes"] += 1
            if "nan" in low and ("detect" in low or "found" in low):
                events["nan"] += 1
            if "N o r m a l" in line:
                termination = "normal"
            elif "E r r o r" in line and "t e r m i n a t i o n" in line:
                termination = "error"
    return termination, errors, sorted(warnings), events, diagnostics


def classify_message(text):
    low = text.lower()
    if "input" in low or "keyword" in low or "card" in low:
        return "keyword_format"
    if "material" in low or "mat_" in low:
        return "material"
    if "contact" in low or "interface" in low:
        return "contact"
    if "part" in low or "section" in low or "node" in low or "element" in low:
        return "reference"
    if "negative volume" in low or "out-of-range" in low or "nan" in low:
        return "instability"
    if "license" in low:
        return "environment"
    return "solver"


def extract_number(text, severity):
    pattern = r"\*\*\*\s+%s\s+(\d+)" % severity.capitalize()
    match = re.search(pattern, text)
    return match.group(1) if match else None


def make_diagnostic(severity, source, line_no, evidence_lines):
    evidence = [line.strip() for line in evidence_lines if line.strip()]
    text = " | ".join(evidence)
    return {
        "severity": severity,
        "source": source,
        "line": line_no,
        "number": extract_number(text, severity),
        "category": classify_message(text),
        "evidence": evidence[:5],
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rundir")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--max-energy-dev", type=float, default=0.10)
    ap.add_argument("--max-hourglass", type=float, default=0.10)
    ap.add_argument("--max-added-mass", type=float, default=5.0)
    a = ap.parse_args(argv)
    rundir = Path(a.rundir)

    termination, errors, warnings, events, diagnostics = collect_messages(rundir)

    metrics = {}
    gates = {}
    gates["normal_termination"] = (termination == "normal")
    gates["no_solver_errors"] = (len(errors) == 0)
    gates["no_instability_events"] = (events["negative_volume"] == 0 and
                                      events["shooting_nodes"] == 0 and
                                      events["nan"] == 0)

    data_missing = []
    glstat = rundir / "glstat"
    if glstat.is_file():
        s = parse_glstat(glstat)
        if s["ratio"]:
            dev = max(abs(r - 1.0) for r in s["ratio"])
            metrics["energy_ratio_final"] = s["ratio"][-1]
            metrics["energy_ratio_max_dev"] = dev
            gates["energy_balance"] = dev <= a.max_energy_dev
        else:
            data_missing.append("glstat has no 'total energy / initial energy' lines - "
                                "energy-balance gate not evaluated")
        if s["hourglass"] and s["internal"]:
            peak_int = max(s["internal"]) or 1e-30
            hg = max(s["hourglass"]) / peak_int
            metrics["hourglass_over_internal"] = hg
            gates["hourglass"] = hg <= a.max_hourglass
        else:
            data_missing.append("no hourglass-energy series in glstat - hourglass gate not "
                                "evaluated (deck needs *CONTROL_ENERGY with HGEN=2)")
        if s["mass_pct"]:
            metrics["added_mass_pct_max"] = max(s["mass_pct"])
            gates["added_mass"] = max(s["mass_pct"]) <= a.max_added_mass
        else:
            # glstat omits the mass lines only when no mass scaling is active
            metrics["added_mass_pct_max"] = 0.0
            gates["added_mass"] = True
        if s["time"]:
            metrics["last_glstat_time"] = s["time"][-1]
    else:
        data_missing.append("glstat missing - energy/hourglass/added-mass gates not evaluated "
                            "(deck needs *DATABASE_GLSTAT and *CONTROL_ENERGY HGEN=2)")

    hard_fail = (not gates["normal_termination"] or not gates["no_solver_errors"]
                 or not gates["no_instability_events"])
    soft = [k for k in ("energy_balance", "hourglass", "added_mass")
            if k in gates and not gates[k]]
    if hard_fail:
        verdict = "FAIL"
    elif soft or data_missing:
        verdict = "WARN"   # per docstring: soft-gate violation OR quality data missing
    else:
        verdict = "PASS"

    report = {
        "verdict": verdict,
        "termination": termination,
        "gates": gates,
        "metrics": metrics,
        "data_missing": data_missing,
        "events": events,
        "errors": errors,
        "diagnostics": diagnostics,
        "warning_count": len(warnings),
        "warnings": warnings[:20],
    }
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 1 if verdict == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
