"""Build an immutable LS-DYNA case from reviewed parameters and a baseline.

The project JSON declares a fixed baseline and guarded field-level mappings.
Each mapping identifies one keyword occurrence, one data line, one field, and
the value expected in the baseline.  A mismatch fails closed instead of
guessing where a parameter belongs.

Usage:
    python build_parameterized_case.py project.json confirmed.json --out cases/case-001
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parameter_contract import (  # noqa: E402
    ContractError,
    load_contract,
    parameter_digest,
    validate_extraction,
)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _within(root, relative, label):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ContractError(f"{label} escapes its allowed root: {relative!r}") from exc
    return candidate


def validate_mapping_contract(project):
    baseline = project.get("baseline")
    if not isinstance(baseline, dict) or not baseline.get("root") or not baseline.get("main_deck"):
        raise ContractError("baseline.root and baseline.main_deck are required")
    mappings = project.get("keyword_mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ContractError("keyword_mappings must be a non-empty list")
    parameter_ids = {item["parameter_id"] for item in project["parameters"]}
    seen = set()
    required = {item["parameter_id"] for item in project["parameters"] if item.get("required")}
    for index, mapping in enumerate(mappings):
        label = f"keyword_mappings[{index}]"
        parameter_id = mapping.get("parameter_id")
        if parameter_id not in parameter_ids:
            raise ContractError(f"{label}: parameter_id {parameter_id!r} is not whitelisted")
        identity = (
            mapping.get("target_file"), mapping.get("keyword"), mapping.get("occurrence", 1),
            mapping.get("data_line"), mapping.get("field"),
        )
        if identity in seen:
            raise ContractError(f"{label}: duplicate target field mapping")
        seen.add(identity)
        if not mapping.get("target_file") or not mapping.get("keyword"):
            raise ContractError(f"{label}: target_file and keyword are required")
        for key in ("occurrence", "data_line", "field"):
            if not isinstance(mapping.get(key, 1), int) or mapping.get(key, 1) < 1:
                raise ContractError(f"{label}: {key} must be a positive integer")
        if mapping.get("format") not in ("csv", "fixed"):
            raise ContractError(f"{label}: format must be 'csv' or 'fixed'")
        if mapping.get("format") == "fixed" and (
            not isinstance(mapping.get("width", 10), int) or mapping.get("width", 10) < 1
        ):
            raise ContractError(f"{label}: width must be a positive integer")
        if "expected" not in mapping:
            raise ContractError(f"{label}: expected baseline value is required")
    mapped = {mapping["parameter_id"] for mapping in mappings}
    missing = sorted(required - mapped)
    if missing:
        raise ContractError(f"required parameters have no keyword mapping: {missing}")


def load_project(path):
    project = load_contract(path)
    validate_mapping_contract(project)
    return project


def _keyword_blocks(lines):
    blocks = []
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith("*"):
            continue
        keyword = stripped[1:].strip().split(",", 1)[0].upper()
        end = len(lines)
        for following in range(index + 1, len(lines)):
            if lines[following].lstrip().startswith("*"):
                end = following
                break
        data_indices = [line_index for line_index in range(index + 1, end)
                        if lines[line_index].strip() and not lines[line_index].lstrip().startswith("$")]
        blocks.append({"keyword": keyword, "line": index, "data_indices": data_indices})
    return blocks


def _format_value(value, mapping):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ContractError("mapped value must be a finite number")
    format_spec = mapping.get("value_format", ".9g")
    try:
        return format(value, format_spec)
    except (ValueError, TypeError) as exc:
        raise ContractError(f"invalid value_format {format_spec!r}") from exc


def _equivalent_expected(actual, expected):
    actual = actual.strip()
    expected = str(expected).strip()
    if actual == expected:
        return True
    try:
        return math.isclose(
            float(actual.replace("D", "E").replace("d", "e")),
            float(expected.replace("D", "E").replace("d", "e")),
            rel_tol=1e-12,
            abs_tol=1e-15,
        )
    except ValueError:
        return False


def apply_mapping(text, mapping, value):
    newline = "\r\n" if "\r\n" in text else "\n"
    trailing_newline = text.endswith(("\n", "\r"))
    lines = text.splitlines()
    keyword = mapping["keyword"].lstrip("*").upper()
    matches = [block for block in _keyword_blocks(lines) if block["keyword"] == keyword]
    occurrence = mapping.get("occurrence", 1)
    if len(matches) < occurrence:
        raise ContractError(f"keyword *{keyword} occurrence {occurrence} was not found")
    block = matches[occurrence - 1]
    data_line = mapping["data_line"]
    if len(block["data_indices"]) < data_line:
        raise ContractError(f"*{keyword} has no data line {data_line}")
    line_index = block["data_indices"][data_line - 1]
    line = lines[line_index]
    field_index = mapping["field"] - 1
    replacement = _format_value(value, mapping)

    if mapping["format"] == "csv":
        if "," not in line:
            raise ContractError(f"*{keyword} data line {data_line} is not comma-separated")
        fields = line.split(",")
        if field_index >= len(fields):
            raise ContractError(f"*{keyword} data line {data_line} has no field {field_index + 1}")
        actual = fields[field_index]
        if not _equivalent_expected(actual, mapping["expected"]):
            raise ContractError(
                f"baseline guard failed for *{keyword} field {field_index + 1}: "
                f"expected {mapping['expected']!r}, found {actual.strip()!r}"
            )
        leading = actual[:len(actual) - len(actual.lstrip())]
        trailing = actual[len(actual.rstrip()):]
        fields[field_index] = leading + replacement + trailing
        lines[line_index] = ",".join(fields)
    else:
        width = mapping.get("width", 10)
        start = field_index * width
        end = start + width
        if len(line) < end:
            line = line.ljust(end)
        actual = line[start:end]
        if not _equivalent_expected(actual, mapping["expected"]):
            raise ContractError(
                f"baseline guard failed for *{keyword} field {field_index + 1}: "
                f"expected {mapping['expected']!r}, found {actual.strip()!r}"
            )
        if len(replacement) > width:
            raise ContractError(f"formatted value {replacement!r} exceeds fixed field width {width}")
        align = mapping.get("align", "right")
        if align not in ("left", "right"):
            raise ContractError("fixed field align must be 'left' or 'right'")
        formatted = replacement.ljust(width) if align == "left" else replacement.rjust(width)
        lines[line_index] = line[:start] + formatted + line[end:]

    rendered = newline.join(lines)
    return rendered + newline if trailing_newline else rendered


def _file_inventory(root):
    records = []
    for path in sorted(item for item in Path(root).rglob("*") if item.is_file()):
        records.append({
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256(path),
        })
    return records


def build_case(project_path, confirmed_path, outdir, case_id=None):
    project_path = Path(project_path).resolve()
    project = load_project(project_path)
    document = json.loads(Path(confirmed_path).read_text(encoding="utf-8"))
    checked = validate_extraction(project, document)
    if not checked["validation"]["valid"]:
        raise ContractError("confirmed parameter document no longer passes validation")
    if document.get("state") != "confirmed" or document.get("review", {}).get("status") != "confirmed":
        raise ContractError("parameter document has not been explicitly confirmed")
    expected_digest = document.get("review", {}).get("parameter_digest")
    if not expected_digest or expected_digest != parameter_digest(document):
        raise ContractError("confirmed parameter values were changed after review")
    for parameter_id, record in document.get("parameters", {}).items():
        if record.get("review_status") != "confirmed":
            raise ContractError(f"parameter {parameter_id!r} is not confirmed")

    project_root = project_path.parent
    baseline_root = _within(project_root, project["baseline"]["root"], "baseline.root")
    if not baseline_root.is_dir():
        raise ContractError(f"baseline root is not a directory: {baseline_root}")
    baseline_main = _within(baseline_root, project["baseline"]["main_deck"], "baseline.main_deck")
    if not baseline_main.is_file():
        raise ContractError(f"baseline main deck was not found: {baseline_main}")

    outdir = Path(outdir).resolve()
    if outdir.exists():
        raise ContractError(f"case output already exists: {outdir}")
    try:
        outdir.relative_to(baseline_root)
    except ValueError:
        pass
    else:
        raise ContractError("case output cannot be located inside the baseline directory")

    mapped_parameter_ids = {mapping["parameter_id"] for mapping in project["keyword_mappings"]}
    unmapped = sorted(set(document["parameters"]) - mapped_parameter_ids)
    if unmapped:
        raise ContractError(f"confirmed parameters have no keyword mapping: {unmapped}")

    # Render and guard every edit before creating the case directory.  A bad
    # mapping therefore cannot leave a half-built case that looks usable.
    rendered_files = {}
    planned_changes = []
    values = document["parameters"]
    for mapping in project["keyword_mappings"]:
        parameter_id = mapping["parameter_id"]
        if parameter_id not in values:
            continue
        source = _within(baseline_root, mapping["target_file"], "keyword_mappings.target_file")
        if not source.is_file():
            raise ContractError(f"mapping target file was not found: {source}")
        relative = source.relative_to(baseline_root).as_posix()
        text = rendered_files.get(relative)
        if text is None:
            text = source.read_text(encoding="ascii", errors="strict")
        rendered_files[relative] = apply_mapping(
            text, mapping, values[parameter_id]["normalized_value"]
        )
        planned_changes.append((mapping, parameter_id, relative, sha256(source)))

    output_parent = outdir.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    deck_dir = outdir / "deck"
    input_dir = outdir / "input"
    shutil.copytree(baseline_root, deck_dir)
    input_dir.mkdir(parents=True)
    shutil.copy2(confirmed_path, input_dir / "confirmed-parameters.json")

    for relative, rendered in rendered_files.items():
        (deck_dir / relative).write_text(rendered, encoding="ascii", newline="")

    changes = []
    for mapping, parameter_id, relative, before_hash in planned_changes:
        target = deck_dir / relative
        changes.append({
            "parameter_id": parameter_id,
            "target_file": relative,
            "keyword": mapping["keyword"],
            "occurrence": mapping.get("occurrence", 1),
            "data_line": mapping["data_line"],
            "field": mapping["field"],
            "before_sha256": before_hash,
            "after_sha256": sha256(target),
            "normalized_value": values[parameter_id]["normalized_value"],
            "normalized_unit": values[parameter_id]["normalized_unit"],
        })

    created_at = datetime.now(timezone.utc).isoformat()
    case_id = case_id or f"case-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{expected_digest[:8]}"
    manifest = {
        "schema_version": 1,
        "case_id": case_id,
        "project_id": project["project_id"],
        "created_at": created_at,
        "state": "rendered",
        "main_deck": (Path("deck") / baseline_main.relative_to(baseline_root)).as_posix(),
        "review": document["review"],
        "parameter_digest": expected_digest,
        "baseline_inventory": _file_inventory(baseline_root),
        "case_inventory": _file_inventory(deck_dir),
        "changes": changes,
    }
    manifest_path = outdir / "case-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"case_dir": str(outdir), "manifest": str(manifest_path), "main_deck": str(outdir / manifest["main_deck"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("confirmed")
    parser.add_argument("--out", required=True)
    parser.add_argument("--case-id")
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args(argv)
    try:
        result = build_case(args.project, args.confirmed, args.out, args.case_id)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.json_out:
            Path(args.json_out).write_text(payload, encoding="utf-8")
        print(payload, end="")
        return 0
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
