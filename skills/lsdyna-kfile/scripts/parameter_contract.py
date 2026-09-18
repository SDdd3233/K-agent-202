"""Extract and validate whitelisted LS-DYNA parameters from plain text.

This module is deliberately independent from an LLM.  A language model may
help interpret a request, but only parameter IDs declared in the project JSON
can pass this boundary.  The output retains source evidence and remains in a
``pending_review`` state until an explicit confirmation step is executed.

Examples:
    python parameter_contract.py extract project.json --text-file request.txt --out extracted.json
    python parameter_contract.py validate project.json extracted.json --out validated.json
    python parameter_contract.py confirm project.json validated.json --reviewer user --out confirmed.json
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from units import DIMENSIONS, UNIT_SYSTEMS, convert  # noqa: E402


SCHEMA_VERSION = 1
NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"

# factor converts a value in the named unit to SI.  Spellings are normalized
# by _unit_key before lookup.  This intentionally stays small and explicit:
# unsupported/ambiguous units must be added deliberately, never guessed.
UNIT_TO_SI = {
    "dimensionless": {"": 1.0, "1": 1.0},
    "length": {"m": 1.0, "mm": 1e-3, "cm": 1e-2, "米": 1.0, "毫米": 1e-3, "厘米": 1e-2},
    "time": {"s": 1.0, "ms": 1e-3, "us": 1e-6, "秒": 1.0, "毫秒": 1e-3, "微秒": 1e-6},
    "velocity": {
        "m/s": 1.0, "mm/s": 1e-3, "cm/s": 1e-2, "km/h": 1.0 / 3.6,
        "mm/ms": 1.0, "cm/us": 1e4, "米/秒": 1.0, "毫米/秒": 1e-3,
        "千米/小时": 1.0 / 3.6,
    },
    "accel": {"m/s^2": 1.0, "mm/s^2": 1e-3, "m/s2": 1.0, "mm/s2": 1e-3},
    "stress": {
        "pa": 1.0, "kpa": 1e3, "mpa": 1e6, "gpa": 1e9, "mbar": 1e11,
        "帕": 1.0, "千帕": 1e3, "兆帕": 1e6, "吉帕": 1e9,
    },
    "force": {"n": 1.0, "kn": 1e3, "mn": 1e6},
    "density": {"kg/m^3": 1.0, "kg/m3": 1.0, "g/cm^3": 1e3, "g/cm3": 1e3,
                "ton/mm^3": 1e12, "ton/mm3": 1e12},
    "strain_rate": {"1/s": 1.0, "s^-1": 1.0, "/s": 1.0},
    "temperature": {"k": 1.0},
}


class ContractError(ValueError):
    """Raised when a project contract or extraction document is malformed."""


def _unit_key(value):
    value = (value or "").strip().replace("μ", "u").replace("µ", "u")
    value = value.replace("²", "^2").replace("³", "^3").replace("−", "-")
    return value.lower().replace(" ", "")


def _unit_table(dimension):
    return {_unit_key(name): factor for name, factor in UNIT_TO_SI.get(dimension, {}).items()}


def load_contract(path):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"project schema_version must be {SCHEMA_VERSION}")
    if not contract.get("project_id"):
        raise ContractError("project_id is required")
    system = contract.get("unit_system")
    if system not in UNIT_SYSTEMS:
        raise ContractError(f"unknown unit_system {system!r}; expected one of {sorted(UNIT_SYSTEMS)}")
    parameters = contract.get("parameters")
    if not isinstance(parameters, list) or not parameters:
        raise ContractError("parameters must be a non-empty list")

    ids = set()
    aliases = {}
    for index, spec in enumerate(parameters):
        prefix = f"parameters[{index}]"
        parameter_id = spec.get("parameter_id")
        if not parameter_id or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", parameter_id):
            raise ContractError(f"{prefix}.parameter_id is missing or invalid")
        if parameter_id in ids:
            raise ContractError(f"duplicate parameter_id {parameter_id!r}")
        ids.add(parameter_id)
        dimension = spec.get("dimension")
        if dimension not in DIMENSIONS:
            raise ContractError(f"{parameter_id}: unknown dimension {dimension!r}")
        if dimension not in UNIT_TO_SI:
            raise ContractError(f"{parameter_id}: input unit conversion is not implemented for {dimension!r}")
        if spec.get("type", "number") not in ("number", "integer"):
            raise ContractError(f"{parameter_id}: only number/integer parameters are supported")
        names = [spec.get("name"), parameter_id] + list(spec.get("aliases", []))
        if not spec.get("name"):
            raise ContractError(f"{parameter_id}: name is required")
        for alias in names:
            key = str(alias).strip().casefold()
            if not key:
                raise ContractError(f"{parameter_id}: aliases cannot be empty")
            if key in aliases and aliases[key] != parameter_id:
                raise ContractError(f"alias {alias!r} is shared by {aliases[key]!r} and {parameter_id!r}")
            aliases[key] = parameter_id
        default_unit = spec.get("default_input_unit")
        if default_unit is not None and _unit_key(default_unit) not in _unit_table(dimension):
            raise ContractError(f"{parameter_id}: unsupported default_input_unit {default_unit!r}")
        bounds = spec.get("allowed_range", {})
        if not isinstance(bounds, dict):
            raise ContractError(f"{parameter_id}: allowed_range must be an object")
        if "min" in bounds and "max" in bounds and bounds["min"] > bounds["max"]:
            raise ContractError(f"{parameter_id}: allowed_range min exceeds max")
    return True


def _aliases(spec):
    values = [spec["name"], spec["parameter_id"]] + list(spec.get("aliases", []))
    return sorted(set(values), key=len, reverse=True)


def _unit_pattern(dimension):
    names = set(UNIT_TO_SI[dimension])
    # Permit common typographic variants which _unit_key canonicalizes.
    names.update(name.replace("^2", "²").replace("^3", "³") for name in list(names))
    nonempty = [name for name in names if name]
    return "|".join(re.escape(name) for name in sorted(nonempty, key=len, reverse=True))


def _candidate_pattern(spec):
    aliases = "|".join(re.escape(item) for item in _aliases(spec))
    unit = _unit_pattern(spec["dimension"])
    connector = r"\s*(?:设置为|调整为|修改为|改为|设为|取值为|取值|为|是|=|:|：)?\s*"
    # Unit is optional here so that validation can produce a precise
    # missing-unit error rather than silently discarding the user's value.
    return re.compile(
        rf"(?P<alias>{aliases}){connector}(?P<value>{NUMBER_PATTERN})\s*(?P<unit>{unit})?",
        re.IGNORECASE,
    )


def _normalize_candidate(contract, spec, raw_value, raw_unit):
    dimension = spec["dimension"]
    unit = raw_unit or spec.get("default_input_unit")
    inferred = not raw_unit and unit is not None
    if dimension == "dimensionless" and unit is None:
        unit = ""
    if unit is None:
        raise ContractError("missing explicit unit")
    table = _unit_table(dimension)
    key = _unit_key(unit)
    if key not in table:
        raise ContractError(f"unit {unit!r} is not valid for dimension {dimension!r}")
    accepted = spec.get("accepted_units")
    if accepted is not None and key not in {_unit_key(item) for item in accepted}:
        raise ContractError(f"unit {unit!r} is not permitted by this parameter")
    numeric = float(raw_value)
    si_value = numeric * table[key]
    normalized = convert(contract["unit_system"], dimension, si_value)
    normalized = normalized * float(spec.get("deck_multiplier", 1.0)) + float(spec.get("deck_offset", 0.0))
    if spec.get("type", "number") == "integer":
        if not math.isclose(normalized, round(normalized), rel_tol=0.0, abs_tol=1e-9):
            raise ContractError(f"normalized value {normalized:g} is not an integer")
        normalized = int(round(normalized))
    label = "1" if dimension == "dimensionless" else UNIT_SYSTEMS[contract["unit_system"]]["labels"][dimension]
    return normalized, label, inferred


def extract_text(contract, text, source_name="inline"):
    validate_contract(contract)
    if not isinstance(text, str) or not text.strip():
        raise ContractError("input text is empty")
    parameters = {}
    conflicts = []
    global_errors = []
    global_warnings = []

    for spec in contract["parameters"]:
        parameter_id = spec["parameter_id"]
        candidates = []
        for match in _candidate_pattern(spec).finditer(text):
            evidence_start = max(0, match.start() - 30)
            evidence_end = min(len(text), match.end() + 30)
            item = {
                "raw_value": match.group("value"),
                "raw_unit": match.group("unit") or None,
                "evidence": {
                    "text": text[evidence_start:evidence_end],
                    "start": match.start(),
                    "end": match.end(),
                },
            }
            try:
                value, unit, inferred = _normalize_candidate(
                    contract, spec, item["raw_value"], item["raw_unit"]
                )
                item.update({"normalized_value": value, "normalized_unit": unit, "unit_inferred": inferred})
            except (ContractError, ValueError) as exc:
                item["error"] = str(exc)
            candidates.append(item)
        if not candidates:
            continue

        candidate_errors = [item["error"] for item in candidates if "error" in item]
        valid_candidates = [item for item in candidates if "error" not in item]
        values = []
        for item in valid_candidates:
            value = item["normalized_value"]
            if not any(math.isclose(float(value), float(old), rel_tol=1e-12, abs_tol=1e-12) for old in values):
                values.append(value)
        errors = list(candidate_errors)
        if len(values) > 1:
            message = f"{parameter_id}: conflicting normalized values {values}"
            errors.append(message)
            conflicts.append({"parameter_id": parameter_id, "values": values})
        selected = valid_candidates[-1] if valid_candidates else candidates[-1]
        record = {
            "parameter_id": parameter_id,
            "name": spec["name"],
            "candidates": candidates,
            "review_status": "pending",
            "validation": {"valid": not errors, "errors": errors, "warnings": []},
        }
        if valid_candidates:
            record["normalized_value"] = selected["normalized_value"]
            record["normalized_unit"] = selected["normalized_unit"]
            if selected.get("unit_inferred"):
                record["validation"]["warnings"].append(
                    f"{parameter_id}: unit inferred as {spec['default_input_unit']!r}"
                )
        parameters[parameter_id] = record

    missing = [spec["parameter_id"] for spec in contract["parameters"]
               if spec.get("required", False) and spec["parameter_id"] not in parameters]
    for parameter_id in missing:
        global_errors.append(f"required parameter {parameter_id!r} was not found")
    result = {
        "schema_version": SCHEMA_VERSION,
        "project_id": contract["project_id"],
        "unit_system": contract["unit_system"],
        "source": {
            "name": source_name,
            "length": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "parameters": parameters,
        "missing_required": missing,
        "conflicts": conflicts,
        "unknown_items": [],
        "validation": {"valid": False, "errors": global_errors, "warnings": global_warnings},
        "state": "extracted",
    }
    return validate_extraction(contract, result)


def validate_extraction(contract, document):
    validate_contract(contract)
    result = copy.deepcopy(document)
    errors = []
    warnings = []
    if result.get("project_id") != contract["project_id"]:
        errors.append("project_id does not match the project contract")
    if result.get("unit_system") != contract["unit_system"]:
        errors.append("unit_system does not match the project contract")
    known = {spec["parameter_id"]: spec for spec in contract["parameters"]}
    records = result.get("parameters")
    if not isinstance(records, dict):
        raise ContractError("extraction parameters must be an object keyed by parameter_id")
    unexpected = sorted(set(records) - set(known))
    if unexpected:
        errors.append(f"non-whitelisted parameters are present: {unexpected}")

    for parameter_id, record in records.items():
        if parameter_id not in known:
            continue
        spec = known[parameter_id]
        record_errors = list(record.get("validation", {}).get("errors", []))
        record_warnings = list(record.get("validation", {}).get("warnings", []))
        value = record.get("normalized_value")
        if value is None:
            record_errors.append(f"{parameter_id}: no normalized value")
        elif not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            record_errors.append(f"{parameter_id}: normalized value must be a finite number")
        else:
            bounds = spec.get("allowed_range", {})
            if "min" in bounds and value < bounds["min"]:
                record_errors.append(f"{parameter_id}: {value:g} is below minimum {bounds['min']:g}")
            if "max" in bounds and value > bounds["max"]:
                record_errors.append(f"{parameter_id}: {value:g} exceeds maximum {bounds['max']:g}")
            if spec.get("type", "number") == "integer" and not float(value).is_integer():
                record_errors.append(f"{parameter_id}: value must be an integer")
        record["validation"] = {
            "valid": not record_errors,
            "errors": list(dict.fromkeys(record_errors)),
            "warnings": list(dict.fromkeys(record_warnings)),
        }
        errors.extend(record["validation"]["errors"])
        warnings.extend(record["validation"]["warnings"])

    missing = sorted(spec["parameter_id"] for spec in contract["parameters"]
                     if spec.get("required", False) and spec["parameter_id"] not in records)
    result["missing_required"] = missing
    errors.extend(f"required parameter {item!r} was not found" for item in missing)
    if result.get("conflicts"):
        errors.append("one or more parameters contain conflicting values")
    result["validation"] = {
        "valid": not errors,
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
    }
    result["state"] = "pending_review" if not errors else "validation_failed"
    return result


def parameter_digest(document):
    """Return a stable digest of the values a reviewer is approving."""
    approved = {}
    for parameter_id, record in sorted(document.get("parameters", {}).items()):
        approved[parameter_id] = {
            "normalized_value": record.get("normalized_value"),
            "normalized_unit": record.get("normalized_unit"),
        }
    payload = json.dumps(approved, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def confirm_extraction(contract, document, reviewer, note=None):
    if not reviewer or not reviewer.strip():
        raise ContractError("reviewer is required")
    result = validate_extraction(contract, document)
    if not result["validation"]["valid"]:
        raise ContractError("cannot confirm an extraction that has validation errors")
    timestamp = datetime.now(timezone.utc).isoformat()
    for record in result["parameters"].values():
        record["review_status"] = "confirmed"
    result["review"] = {
        "status": "confirmed",
        "reviewer": reviewer.strip(),
        "confirmed_at": timestamp,
        "note": note or "",
        "parameter_digest": parameter_digest(result),
    }
    result["state"] = "confirmed"
    return result


def _write_json(data, path):
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path:
        Path(path).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    extract_cmd = sub.add_parser("extract", help="extract whitelisted parameters from text")
    extract_cmd.add_argument("project")
    source = extract_cmd.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--text-file")
    extract_cmd.add_argument("--out")

    validate_cmd = sub.add_parser("validate", help="revalidate a saved extraction")
    validate_cmd.add_argument("project")
    validate_cmd.add_argument("input")
    validate_cmd.add_argument("--out")

    confirm_cmd = sub.add_parser("confirm", help="record explicit human confirmation")
    confirm_cmd.add_argument("project")
    confirm_cmd.add_argument("input")
    confirm_cmd.add_argument("--reviewer", required=True)
    confirm_cmd.add_argument("--note")
    confirm_cmd.add_argument("--out")

    args = parser.parse_args(argv)
    try:
        contract = load_contract(args.project)
        if args.command == "extract":
            if args.text_file:
                text = Path(args.text_file).read_text(encoding="utf-8")
                source_name = str(Path(args.text_file).resolve())
            else:
                text = args.text
                source_name = "inline"
            result = extract_text(contract, text, source_name)
        else:
            document = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if args.command == "validate":
                result = validate_extraction(contract, document)
            else:
                result = confirm_extraction(contract, document, args.reviewer, args.note)
        _write_json(result, args.out)
        return 0 if result["validation"]["valid"] else 2
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
