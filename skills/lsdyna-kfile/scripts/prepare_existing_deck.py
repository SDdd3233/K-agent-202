"""Prepare an isolated repair workspace for an existing LS-DYNA deck.

Copies the main deck and its recursive *INCLUDE closure into:

    repair_<deck-stem>/
      source/
      working/
      iterations/
      deck-manifest.json
      repair-history.json

The original deck directory is never modified.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


DECK_EXTS = {".k", ".key", ".dyn", ".inc"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def include_targets(path):
    """Yield raw include paths from common single-line *INCLUDE blocks."""
    lines = path.read_text(encoding="ascii", errors="replace").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("$") or not line.upper().startswith("*INCLUDE"):
            i += 1
            continue
        i += 1
        while i < len(lines):
            raw = lines[i].strip()
            if not raw or raw.startswith("$"):
                i += 1
                continue
            if raw.startswith("*"):
                break
            yield raw.strip("\"'")
            i += 1
            break


def collect_include_graph(main_deck):
    main_deck = Path(main_deck).resolve()
    queue = [main_deck]
    seen = set()
    records = []
    missing = []

    while queue:
        deck = queue.pop(0)
        if deck in seen:
            continue
        seen.add(deck)
        if not deck.is_file():
            missing.append(str(deck))
            continue
        includes = []
        for raw in include_targets(deck):
            resolved = (deck.parent / raw).resolve()
            includes.append({"raw": raw, "resolved": str(resolved)})
            if resolved not in seen:
                queue.append(resolved)
        records.append(
            {
                "path": str(deck),
                "relative_to_main": _safe_rel(deck, main_deck.parent),
                "sha256": sha256(deck),
                "includes": includes,
            }
        )
    return records, sorted(set(missing))


def _safe_rel(path, base):
    try:
        return str(Path(path).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return str(Path(path).resolve().name)


def _copy_records(records, target_dir, main_parent):
    copied = []
    used = set()
    for record in records:
        src = Path(record["path"])
        rel = _safe_rel(src, main_parent)
        dst = target_dir / rel
        if dst in used:
            stem = dst.stem
            dst = dst.with_name(f"{stem}_{len(used)}{dst.suffix}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        used.add(dst)
        copied.append({"source": str(src), "copy": str(dst), "sha256": record["sha256"]})
    return copied


def prepare(main_deck, outdir=None, objective="preserve original physical intent"):
    main_deck = Path(main_deck).resolve()
    if not main_deck.is_file():
        raise FileNotFoundError(f"deck not found: {main_deck}")
    if main_deck.suffix.lower() not in DECK_EXTS:
        raise ValueError(f"unexpected LS-DYNA deck extension: {main_deck.suffix}")

    base = Path(outdir).resolve() if outdir else main_deck.parent / f"repair_{main_deck.stem}"
    source_dir = base / "source"
    working_dir = base / "working"
    iterations_dir = base / "iterations"
    for folder in (source_dir, working_dir, iterations_dir):
        folder.mkdir(parents=True, exist_ok=True)

    records, missing = collect_include_graph(main_deck)
    source_copies = _copy_records(records, source_dir, main_deck.parent)
    working_copies = _copy_records(records, working_dir, main_deck.parent)
    main_copy = next(item["copy"] for item in working_copies if Path(item["source"]) == main_deck)

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "existing-deck-repair",
        "main_deck": str(main_deck),
        "working_main_deck": main_copy,
        "objective": objective,
        "include_graph": records,
        "missing_includes": missing,
        "source_copies": source_copies,
        "working_copies": working_copies,
    }
    manifest_path = base / "deck-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    history_path = base / "repair-history.json"
    if not history_path.exists():
        history_path.write_text(
            json.dumps({"schema_version": 1, "iterations": []}, indent=2),
            encoding="utf-8",
        )

    return {
        "workspace": str(base),
        "manifest": str(manifest_path),
        "history": str(history_path),
        "working_main_deck": main_copy,
        "missing_includes": missing,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck")
    ap.add_argument("--outdir")
    ap.add_argument("--objective", default="preserve original physical intent")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args(argv)

    result = prepare(args.deck, args.outdir, args.objective)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if result["missing_includes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
