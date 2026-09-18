"""Apply L0 and solver-submission gates to a parameterized LS-DYNA case.

Usage:
    python parameter_case_workflow.py l0 CASE_DIR
    python parameter_case_workflow.py submit CASE_DIR [--mode smp] [--ncpu 4]
    python parameter_case_workflow.py status CASE_DIR
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_parameterized_case import ContractError, sha256  # noqa: E402


SCRIPT_DIR = Path(__file__).resolve().parent


def _read_manifest(case_dir):
    case_dir = Path(case_dir).resolve()
    path = case_dir / "case-manifest.json"
    if not path.is_file():
        raise ContractError(f"case manifest was not found: {path}")
    return case_dir, path, json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(path, manifest):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_deck_integrity(case_dir, manifest):
    deck_dir = case_dir / "deck"
    expected = {item["path"]: item for item in manifest.get("case_inventory", [])}
    actual_paths = {path.relative_to(deck_dir).as_posix(): path
                    for path in deck_dir.rglob("*") if path.is_file()}
    missing = sorted(set(expected) - set(actual_paths))
    added = sorted(set(actual_paths) - set(expected))
    changed = sorted(relative for relative in set(expected) & set(actual_paths)
                     if sha256(actual_paths[relative]) != expected[relative]["sha256"])
    if missing or added or changed:
        raise ContractError(
            f"case deck integrity check failed; missing={missing}, added={added}, changed={changed}"
        )
    return True


def _main_deck(case_dir, manifest):
    main = (case_dir / manifest.get("main_deck", "")).resolve()
    deck_root = (case_dir / "deck").resolve()
    try:
        main.relative_to(deck_root)
    except ValueError as exc:
        raise ContractError("manifest main_deck escapes the case deck directory") from exc
    if not main.is_file():
        raise ContractError(f"case main deck was not found: {main}")
    return main


def run_l0(case_dir, runner=subprocess.run):
    case_dir, manifest_path, manifest = _read_manifest(case_dir)
    verify_deck_integrity(case_dir, manifest)
    main = _main_deck(case_dir, manifest)
    validation_dir = case_dir / "validation"
    validation_dir.mkdir(exist_ok=True)
    report_path = validation_dir / "l0-report.json"
    output_path = validation_dir / "l0-output.log"
    command = [sys.executable, str(SCRIPT_DIR / "check_kfile.py"), str(main), "--json", str(report_path)]
    completed = runner(command, cwd=str(main.parent), capture_output=True, text=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    output_path.write_text(output, encoding="utf-8")
    if not report_path.is_file():
        raise ContractError(f"L0 checker did not produce a report (exit {completed.returncode})")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    passed = completed.returncode == 0 and report.get("verdict") == "PASS"
    manifest["l0"] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "verdict": report.get("verdict", "FAIL"),
        "errors": len(report.get("errors", [])),
        "warnings": len(report.get("warnings", [])),
        "report": report_path.relative_to(case_dir).as_posix(),
        "report_sha256": sha256(report_path),
        "output": output_path.relative_to(case_dir).as_posix(),
    }
    manifest["state"] = "l0_passed" if passed else "l0_failed"
    _write_manifest(manifest_path, manifest)
    return {"passed": passed, "state": manifest["state"], "report": str(report_path), "details": report}


def _parse_last_json_line(output):
    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "status" in value:
            return value
    return None


def submit_case(case_dir, mode="smp", precision="sp", ncpu=4, memory="200m", timeout=1800,
                endtim=None, endcyc=None, runner=subprocess.run):
    case_dir, manifest_path, manifest = _read_manifest(case_dir)
    verify_deck_integrity(case_dir, manifest)
    if manifest.get("l0", {}).get("verdict") != "PASS":
        raise ContractError("solver submission is blocked until this exact case passes L0")
    l0_report = (case_dir / manifest["l0"].get("report", "")).resolve()
    try:
        l0_report.relative_to(case_dir)
    except ValueError as exc:
        raise ContractError("L0 report path escapes the case directory") from exc
    if not l0_report.is_file() or sha256(l0_report) != manifest["l0"].get("report_sha256"):
        raise ContractError("L0 evidence is missing or changed; rerun the L0 gate")
    main = _main_deck(case_dir, manifest)
    run_dir = case_dir / "run"
    command = [
        sys.executable, str(SCRIPT_DIR / "run_dyna.py"), str(main),
        "--rundir", str(run_dir), "--mode", mode, "--precision", precision,
        "--ncpu", str(ncpu), "--memory", memory, "--timeout", str(timeout),
    ]
    if endtim is not None:
        command.extend(["--endtim", str(endtim)])
    if endcyc is not None:
        command.extend(["--endcyc", str(endcyc)])
    completed = runner(command, cwd=str(main.parent), capture_output=True, text=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    run_dir.mkdir(exist_ok=True)
    launcher_log = run_dir / "workflow-launcher.log"
    launcher_log.write_text(output, encoding="utf-8")
    solver_result = _parse_last_json_line(output) or {
        "status": "launcher_error", "returncode": completed.returncode
    }
    manifest["submission"] = {
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "launcher_log": launcher_log.relative_to(case_dir).as_posix(),
        "result": solver_result,
    }
    manifest["state"] = "solver_normal" if solver_result.get("status") == "normal" else "solver_failed"
    _write_manifest(manifest_path, manifest)
    return {"state": manifest["state"], "result": solver_result, "returncode": completed.returncode}


def status(case_dir):
    case_dir, _, manifest = _read_manifest(case_dir)
    integrity = True
    integrity_error = None
    try:
        verify_deck_integrity(case_dir, manifest)
    except ContractError as exc:
        integrity = False
        integrity_error = str(exc)
    return {
        "case_id": manifest.get("case_id"),
        "project_id": manifest.get("project_id"),
        "state": manifest.get("state"),
        "deck_integrity": integrity,
        "integrity_error": integrity_error,
        "l0": manifest.get("l0"),
        "submission": manifest.get("submission"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    l0 = sub.add_parser("l0")
    l0.add_argument("case_dir")
    submit = sub.add_parser("submit")
    submit.add_argument("case_dir")
    submit.add_argument("--mode", choices=("smp", "mpp"), default="smp")
    submit.add_argument("--precision", choices=("sp", "dp"), default="sp")
    submit.add_argument("--ncpu", type=int, default=4)
    submit.add_argument("--memory", default="200m")
    submit.add_argument("--timeout", type=int, default=1800)
    submit.add_argument("--endtim", type=float)
    submit.add_argument("--endcyc", type=int)
    status_cmd = sub.add_parser("status")
    status_cmd.add_argument("case_dir")
    args = parser.parse_args(argv)
    try:
        if args.command == "l0":
            result = run_l0(args.case_dir)
            exit_code = 0 if result["passed"] else 2
        elif args.command == "submit":
            result = submit_case(
                args.case_dir, args.mode, args.precision, args.ncpu, args.memory,
                args.timeout, args.endtim, args.endcyc,
            )
            exit_code = 0 if result["state"] == "solver_normal" else 1
        else:
            result = status(args.case_dir)
            exit_code = 0 if result["deck_integrity"] else 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return exit_code
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
