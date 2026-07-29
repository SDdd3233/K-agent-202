"""Run LS-DYNA (SMP or MPP) on a keyword deck, with timeout and status detection.

Usage:
    python run_dyna.py deck.k [--mode smp|mpp] [--precision sp|dp] [--ncpu 4]
                       [--memory 100m] [--timeout 1800] [--endtim 1e-5] [--no-clean]

--endtim X  : write <deck>_trial.k with *CONTROL_TERMINATION ENDTIM overridden to X
              and run that instead (L1 short initialization run).
--endcyc N  : same, but stop after N cycles (preferred for L1: no dt estimate
              needed; combine with --endtim or use alone).
Runs in the deck's directory. Prints a JSON result line at the end:
    {"status": "normal|error|timeout|crashed", "elapsed_s": ..., "log": ..., "rundir": ...}
Exit code: 0 only for normal termination.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kagent_config import solver_path, mpiexec_path  # noqa: E402

SCRATCH = ("d3plot*", "d3hsp", "d3dump*", "messag*", "mes[0-9]*", "glstat", "matsum", "rcforc",
           "nodout", "elout", "sleout", "rwforc", "binout*", "adptmp", "d3full*",
           "kill_by_pid", "bndout", "spcforc", "nlbsout", "abstat", "sphout",
           "dbsensor", "d3thdt", "runrsf", "dyna.*", "lsda*", "mpptbin*",
           "load_profile*", "cont_profile*", "core", "status.out", "d3kil")


def clean_rundir(rundir):
    removed = 0
    for pat in SCRATCH:
        for f in Path(rundir).glob(pat):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def override_termination(kfile, endtim=None, endcyc=None):
    """Write <deck>_trial.k with ENDTIM and/or ENDCYC of *CONTROL_TERMINATION
    overridden. ENDCYC (cycle count) is the handier L1 knob: the deck stops
    after that many cycles regardless of dt, no time estimate needed."""
    src = Path(kfile)
    lines = src.read_text(encoding="ascii", errors="replace").splitlines()
    out = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if line.strip().upper().startswith("*CONTROL_TERMINATION"):
            j = i + 1
            while j < len(lines) and lines[j].startswith("$"):
                out.append(lines[j])
                j += 1
            if j < len(lines):
                card = lines[j]
                if "," in card:
                    fields = card.split(",")
                    while len(fields) < 2:
                        fields.append("")
                    if endtim is not None:
                        fields[0] = f"{endtim:.4E}"
                    if endcyc is not None:
                        fields[1] = str(endcyc)
                    out.append(",".join(fields))
                else:
                    card = card.ljust(20)
                    f1 = f"{endtim:10.3E}" if endtim is not None else card[:10]
                    f2 = f"{endcyc:10d}" if endcyc is not None else card[10:20]
                    out.append(f1 + f2 + card[20:])
                replaced = True
                i = j + 1
                continue
        i += 1
    if not replaced:
        raise SystemExit("could not find *CONTROL_TERMINATION card to override")
    dst = src.with_name(src.stem + "_trial.k")
    dst.write_text("\n".join(out) + "\n", encoding="ascii")
    return dst


def detect_status(rundir, log_text):
    corpus = log_text
    for name in ("d3hsp", "messag", "mes0000"):
        f = Path(rundir) / name
        if f.is_file():
            try:
                corpus += f.read_text(encoding="ascii", errors="replace")[-20000:]
            except OSError:
                pass
    if "N o r m a l" in corpus:
        return "normal"
    if "E r r o r" in corpus:
        return "error"
    return "crashed"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kfile")
    ap.add_argument("--mode", choices=["smp", "mpp"], default="smp")
    ap.add_argument("--precision", choices=["sp", "dp"], default="sp")
    ap.add_argument("--ncpu", type=int, default=4)
    ap.add_argument("--memory", default="200m")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--endtim", type=float, default=None)
    ap.add_argument("--endcyc", type=int, default=None,
                    help="L1 trial: stop after N cycles (no dt estimate needed)")
    ap.add_argument("--no-clean", action="store_true")
    a = ap.parse_args(argv)

    kfile = Path(a.kfile).resolve()
    if not kfile.is_file():
        raise SystemExit(f"deck not found: {kfile}")
    rundir = kfile.parent
    if a.endtim is not None or a.endcyc is not None:
        kfile = override_termination(kfile, a.endtim, a.endcyc)
    if not a.no_clean:
        clean_rundir(rundir)

    exe = solver_path(a.mode, a.precision)
    if a.mode == "smp":
        cmd = [exe, f"i={kfile.name}", f"ncpu={a.ncpu}", f"memory={a.memory}"]
    else:
        cmd = [mpiexec_path(), "-n", str(a.ncpu), exe,
               f"i={kfile.name}", f"memory={a.memory}"]

    log_path = rundir / "run.log"
    t0 = time.time()
    status = None
    with open(log_path, "w", encoding="ascii", errors="replace") as log:
        try:
            proc = subprocess.Popen(cmd, cwd=str(rundir), stdout=log,
                                    stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL)
            proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
            status = "timeout"
        except FileNotFoundError as e:
            raise SystemExit(f"solver not found: {e}")
    elapsed = time.time() - t0

    log_text = log_path.read_text(encoding="ascii", errors="replace")
    if status is None:
        status = detect_status(rundir, log_text)

    tail = "\n".join(log_text.splitlines()[-12:])
    print(tail)
    print(json.dumps({"status": status, "elapsed_s": round(elapsed, 1),
                      "log": str(log_path), "rundir": str(rundir),
                      "deck": kfile.name, "mode": a.mode,
                      "precision": a.precision}))
    return 0 if status == "normal" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
