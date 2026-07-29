"""L0 static checker for LS-DYNA keyword decks (no solver needed).

Parses the deck (following *INCLUDE), builds entity tables and cross-checks
references. Errors = deck will almost surely fail; warnings = review needed.

Usage:  python check_kfile.py main.k [--json report.json]
Exit code 0 = no errors (warnings allowed), 1 = errors found.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# fixed field widths per keyword family (default: 10-char fields)
WIDTHS = {
    "NODE": [8, 16, 16, 16, 8, 8],
    "ELEMENT_SHELL": [8] * 10,
    "ELEMENT_SOLID": [8] * 10,
    "ELEMENT_BEAM": [8] * 10,
    "ELEMENT_SPH": [8, 8, 16],
    "ELEMENT_MASS": [8, 8, 16, 8],
}

KNOWN_PREFIXES = (
    "KEYWORD", "TITLE", "END", "INCLUDE", "COMMENT", "PARAMETER",
    "CONTROL_", "DATABASE_", "NODE", "ELEMENT_", "PART", "SECTION_", "MAT_",
    "EOS_", "HOURGLASS", "SET_", "CONTACT_", "BOUNDARY_", "INITIAL_", "LOAD_",
    "DEFINE_", "RIGIDWALL_", "CONSTRAINED_", "ALE_", "DAMPING_",
    "PERTURBATION", "INTERFACE_", "RAIL_", "AIRBAG", "SENSOR_", "TERMINATION",
)


class Deck:
    def __init__(self):
        self.blocks = []          # (keyword, [datalines], file, lineno)
        self.nodes = set()
        self.dup_nodes = []
        self.elements = {}        # eid -> (etype, pid, [nids])
        self.dup_elems = []
        self.parts = {}           # pid -> dict(secid, mid, eosid, hgid)
        self.sections = set()
        self.mats = set()
        self.eos = set()
        self.hourglass = set()
        self.curves = set()
        self.tables = set()
        self.nsets = set()
        self.psets = set()
        self.segsets = set()
        self.shsets = set()
        self.sosets = set()
        self.set_node_refs = []   # (sid, [nids]) for explicit lists
        self.mat_rho = {}         # mid -> rho
        self.endtim = None
        self.has_keyword_card = False
        self.has_end = False


def _fields(line, widths):
    if "," in line:
        return [f.strip() for f in line.split(",")]
    out = []
    pos = 0
    for w in widths:
        out.append(line[pos:pos + w].strip())
        pos += w
        if pos >= len(line):
            break
    # tail beyond declared widths, in 10s
    while pos < len(line):
        out.append(line[pos:pos + 10].strip())
        pos += 10
    return out


def _int(s, default=0):
    s = (s or "").strip()
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return default


def _float(s, default=0.0):
    s = (s or "").strip()
    if not s:
        return default
    # fortran style 1.0d-3
    s = s.replace("d", "e").replace("D", "E")
    try:
        return float(s)
    except ValueError:
        return default


def read_deck(path, deck, errors, seen=None):
    seen = seen or set()
    p = Path(path).resolve()
    if p in seen:
        errors.append(f"circular *INCLUDE of {p}")
        return
    seen.add(p)
    if not p.is_file():
        errors.append(f"include file not found: {path}")
        return
    kw = None
    data = []
    kw_line = 0
    text = p.read_text(encoding="ascii", errors="replace")
    lines = text.splitlines()
    for ln, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if line.startswith("$"):
            continue
        if line.startswith("*"):
            if kw is not None:
                deck.blocks.append((kw, data, str(p), kw_line))
            kw = line[1:].strip().upper()
            data = []
            kw_line = ln
            if kw == "KEYWORD":
                deck.has_keyword_card = True
            if kw == "END":
                deck.has_end = True
            continue
        if kw is None:
            if line.strip():
                errors.append(f"{p.name}:{ln}: data before first keyword: '{line[:40]}'")
            continue
        data.append(line)
    if kw is not None:
        deck.blocks.append((kw, data, str(p), kw_line))
    # resolve includes (after this file fully read)
    for kw, data, f, ln in list(deck.blocks):
        if kw.startswith("INCLUDE") and Path(f).resolve() == p:
            for d in data:
                inc = d.strip()
                if inc:
                    read_deck(p.parent / inc, deck, errors, seen)


def base_kw(kw):
    """strip _TITLE/_ID suffixes for family matching"""
    k = kw
    for suf in ("_TITLE", "_ID"):
        if k.endswith(suf):
            k = k[: -len(suf)]
    return k


def harvest(deck, errors, warnings):
    for kw, data, f, ln in deck.blocks:
        loc = f"{Path(f).name}:{ln}"
        bk = base_kw(kw)
        rows = data[title_or_id_offset(kw, data):]

        if bk == "NODE":
            for d in rows:
                fl = _fields(d, WIDTHS["NODE"])
                nid = _int(fl[0] if fl else "")
                if nid <= 0:
                    continue
                if nid in deck.nodes:
                    deck.dup_nodes.append(nid)
                deck.nodes.add(nid)

        elif bk in ("ELEMENT_SHELL", "ELEMENT_SOLID", "ELEMENT_BEAM"):
            nn = {"ELEMENT_SHELL": 4, "ELEMENT_SOLID": 8, "ELEMENT_BEAM": 3}[bk]
            for d in rows:
                fl = _fields(d, WIDTHS[bk])
                if len(fl) < 3:
                    continue
                eid, pid = _int(fl[0]), _int(fl[1])
                if eid <= 0:
                    continue
                nids = [_int(x) for x in fl[2:2 + nn]]
                nids = [n for n in nids if n > 0]
                if eid in deck.elements:
                    deck.dup_elems.append(eid)
                deck.elements[eid] = (bk, pid, nids)

        elif bk == "ELEMENT_SPH":
            for d in rows:
                fl = _fields(d, WIDTHS["ELEMENT_SPH"])
                if len(fl) < 2:
                    continue
                nid, pid = _int(fl[0]), _int(fl[1])
                if nid <= 0:
                    continue
                deck.elements[nid] = ("ELEMENT_SPH", pid, [nid])

        elif bk == "ELEMENT_MASS":
            for d in rows:
                fl = _fields(d, WIDTHS["ELEMENT_MASS"])
                if len(fl) >= 2:
                    nid = _int(fl[1])
                    if nid > 0:
                        deck.elements[_int(fl[0])] = ("ELEMENT_MASS", 0, [nid])

        elif bk == "PART":
            # PART: title line, then pid secid mid eosid hgid ...
            i = 0
            while i + 1 < len(rows) or (len(rows) == 2 and i == 0):
                if i + 1 >= len(rows):
                    break
                title, card = rows[i], rows[i + 1]
                fl = _fields(card, [10] * 8)
                pid = _int(fl[0] if fl else "")
                if pid > 0:
                    deck.parts[pid] = {
                        "secid": _int(fl[1] if len(fl) > 1 else ""),
                        "mid": _int(fl[2] if len(fl) > 2 else ""),
                        "eosid": _int(fl[3] if len(fl) > 3 else ""),
                        "hgid": _int(fl[4] if len(fl) > 4 else ""),
                        "title": title.strip(), "loc": loc,
                    }
                i += 2

        elif bk.startswith("SECTION_"):
            if rows:
                deck.sections.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk.startswith("MAT_ADD_"):
            pass  # references an existing mid, defines nothing

        elif bk.startswith("MAT_"):
            if rows:
                fl = _fields(rows[0], [10] * 8)
                mid = _int(fl[0])
                deck.mats.add(mid)
                deck.mat_rho[mid] = _float(fl[1] if len(fl) > 1 else "")

        elif bk.startswith("EOS_"):
            if rows:
                deck.eos.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "HOURGLASS":
            if rows:
                deck.hourglass.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "DEFINE_CURVE":
            if rows:
                deck.curves.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "DEFINE_TABLE":
            if rows:
                deck.tables.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk in ("SET_NODE_LIST", "SET_NODE"):
            if rows:
                sid = _int(_fields(rows[0], [10] * 8)[0])
                deck.nsets.add(sid)
                nids = []
                for d in rows[1:]:
                    nids += [_int(x) for x in _fields(d, [10] * 8) if _int(x) > 0]
                deck.set_node_refs.append((sid, nids, loc))

        elif bk == "SET_NODE_LIST_GENERATE":
            if rows:
                deck.nsets.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "SET_PART_LIST":
            if rows:
                deck.psets.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "SET_SEGMENT":
            if rows:
                deck.segsets.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "SET_SHELL_LIST":
            if rows:
                deck.shsets.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "SET_SOLID_LIST":
            if rows:
                deck.sosets.add(_int(_fields(rows[0], [10] * 8)[0]))

        elif bk == "CONTROL_TERMINATION":
            if rows:
                deck.endtim = _float(_fields(rows[0], [10] * 8)[0])


def title_or_id_offset(kw, rows):
    """number of leading non-data lines for _TITLE/_ID variants"""
    if kw.endswith("_TITLE") or kw.endswith("_ID"):
        return 1
    return 0


# keyword families whose data cards are all 10-char fixed-width fields
# (excludes NODE/ELEMENT_* [8/16-char], DEFINE_CURVE points [20-char],
#  PART/TITLE/INCLUDE [free text lines])
ALIGN10_PREFIXES = (
    "CONTROL_", "DATABASE_", "SECTION_", "MAT_", "EOS_", "HOURGLASS",
    "CONTACT_", "BOUNDARY_", "INITIAL_", "LOAD_", "SET_",
)


def _piece_is_complete_number(piece):
    """A column-slice piece is a self-contained value: starts with sign/digit
    (a leading '.' or 'E' means a value was cut mid-mantissa/exponent by the
    field boundary) and parses as a number."""
    if not re.match(r"^[+-]?\d", piece):
        return False
    try:
        float(piece.replace("d", "e").replace("D", "E"))
        return True
    except ValueError:
        return False


def check_fixed_alignment(deck, errors):
    """Detect fixed-width misalignment on 10-column cards. The solver reads by
    columns, so a whitespace token crossing a field boundary is fine when the
    boundary happens to butt two complete values together (e.g. field 4 ending
    '...0.0' followed by a full-width '1.000000E8' in field 5). It is an error
    when slicing at the boundaries cuts a value apart (e.g. a 9-char ENDTIM
    shifting the card left so field 5 becomes '.000000E8') - then the solver
    silently reads different values than intended."""
    for kw, data, f, ln in deck.blocks:
        bk = base_kw(kw)
        if not any(bk.startswith(p) for p in ALIGN10_PREFIXES):
            continue
        loc = f"{Path(f).name}:{ln}"
        off = title_or_id_offset(kw, data)
        hits = 0
        for i, dline in enumerate(data[off:]):
            if "," in dline:          # free (comma) format line
                continue
            for m in re.finditer(r"\S+", dline):
                s, e = m.start(), m.end()
                if s // 10 == (e - 1) // 10:
                    continue          # token stays inside one 10-char field
                # slice the token at every 10-column boundary it crosses
                pieces, p = [], s
                while p < e:
                    q = min(e, (p // 10 + 1) * 10)
                    pieces.append(m.group()[p - s:q - s])
                    p = q
                if all(_piece_is_complete_number(pc) for pc in pieces):
                    continue          # fully packed adjacent values: legal
                errors.append(
                    f"{kw} ({loc}) data card {i + 1}: token '{m.group()[:24]}'"
                    f" spans a 10-column field boundary (cols {s + 1}-{e}) and"
                    f" splits into {pieces} - fixed-width misalignment, solver"
                    f" will misread fields")
                hits += 1
                break
            if hits >= 3:
                break


def crosscheck(deck, errors, warnings):
    if not deck.has_keyword_card:
        errors.append("missing *KEYWORD as first card")
    if not deck.has_end:
        warnings.append("missing *END terminator (solver tolerates it, but add one)")
    if deck.endtim is None:
        errors.append("no *CONTROL_TERMINATION card")
    elif deck.endtim <= 0:
        errors.append(f"*CONTROL_TERMINATION ENDTIM={deck.endtim:g} must be > 0")

    # energy-quality prerequisites: without these, L2 gates G3-G5 have no data
    # and parse_results can only report WARN
    present = {base_kw(kw) for kw, _, _, _ in deck.blocks}
    if "CONTROL_ENERGY" not in present:
        warnings.append("missing *CONTROL_ENERGY (HGEN=2 RWEN=2 SLNTEN=2 RYLEN=2) - "
                        "energy quality gates will have no data")
    if "DATABASE_GLSTAT" not in present:
        warnings.append("missing *DATABASE_GLSTAT - L2 energy/mass checks impossible")

    if deck.dup_nodes:
        warnings.append(f"{len(deck.dup_nodes)} duplicate node ids (first: {deck.dup_nodes[:5]})")
    if deck.dup_elems:
        warnings.append(f"{len(deck.dup_elems)} duplicate element ids (first: {deck.dup_elems[:5]})")

    # parts -> section / material
    used_pids = set()
    for pid, pt in deck.parts.items():
        if pt["secid"] not in deck.sections:
            errors.append(f"PART {pid} ('{pt['title']}') references missing SECTION {pt['secid']}")
        if pt["mid"] not in deck.mats:
            errors.append(f"PART {pid} ('{pt['title']}') references missing MAT {pt['mid']}")
        if pt["eosid"] and pt["eosid"] not in deck.eos:
            errors.append(f"PART {pid} references missing EOS {pt['eosid']}")
        if pt["hgid"] and pt["hgid"] not in deck.hourglass:
            errors.append(f"PART {pid} references missing HOURGLASS {pt['hgid']}")

    # elements -> part, nodes
    bad_pid, bad_nid = 0, 0
    for eid, (etype, pid, nids) in deck.elements.items():
        if etype not in ("ELEMENT_MASS",) and pid not in deck.parts:
            bad_pid += 1
            if bad_pid <= 3:
                errors.append(f"{etype} {eid} references missing PART {pid}")
        used_pids.add(pid)
        for n in nids:
            if n not in deck.nodes:
                bad_nid += 1
                if bad_nid <= 3:
                    errors.append(f"{etype} {eid} references missing NODE {n}")
    if bad_pid > 3:
        errors.append(f"... {bad_pid} elements total with missing parts")
    if bad_nid > 3:
        errors.append(f"... {bad_nid} element-node references missing in total")

    for pid in deck.parts:
        if pid not in used_pids:
            warnings.append(f"PART {pid} has no elements")

    # node sets -> nodes
    for sid, nids, loc in deck.set_node_refs:
        missing = [n for n in nids if n not in deck.nodes]
        if missing:
            errors.append(f"SET_NODE {sid} ({loc}): {len(missing)} member nodes missing (first: {missing[:5]})")

    # density sanity
    for mid, rho in deck.mat_rho.items():
        if rho <= 0:
            errors.append(f"MAT {mid} has non-positive density RO={rho:g}")

    # referenced ids in common cards
    for kw, rows, f, ln in deck.blocks:
        bk = base_kw(kw)
        off = title_or_id_offset(kw, rows)
        loc = f"{Path(f).name}:{ln}"
        rows2 = rows[off:]
        if bk.startswith("BOUNDARY_SPC_SET"):
            if rows2:
                nsid = _int(_fields(rows2[0], [10] * 8)[0])
                if nsid not in deck.nsets:
                    errors.append(f"{kw} ({loc}): missing node set {nsid}")
        elif bk.startswith("BOUNDARY_PRESCRIBED_MOTION_SET"):
            if rows2:
                fl = _fields(rows2[0], [10] * 8)
                nsid, lcid = _int(fl[0]), _int(fl[3] if len(fl) > 3 else "")
                if nsid not in deck.nsets:
                    errors.append(f"{kw} ({loc}): missing node set {nsid}")
                if lcid and lcid not in deck.curves:
                    errors.append(f"{kw} ({loc}): missing curve {lcid}")
        elif bk.startswith("BOUNDARY_PRESCRIBED_MOTION_RIGID"):
            if rows2:
                fl = _fields(rows2[0], [10] * 8)
                pid, lcid = _int(fl[0]), _int(fl[3] if len(fl) > 3 else "")
                if pid not in deck.parts:
                    errors.append(f"{kw} ({loc}): missing part {pid}")
                if lcid and lcid not in deck.curves:
                    errors.append(f"{kw} ({loc}): missing curve {lcid}")
        elif bk == "LOAD_BODY_Z" or bk == "LOAD_BODY_Y" or bk == "LOAD_BODY_X":
            if rows2:
                lcid = _int(_fields(rows2[0], [10] * 8)[0])
                if lcid and lcid not in deck.curves:
                    errors.append(f"{kw} ({loc}): missing curve {lcid}")
        elif bk.startswith("INITIAL_VELOCITY_GENERATION"):
            if rows2:
                fl = _fields(rows2[0], [10] * 8)
                sid, styp = _int(fl[0]), _int(fl[1] if len(fl) > 1 else "")
                ok = ((styp == 1 and sid in deck.psets) or
                      (styp == 2 and sid in deck.parts) or
                      (styp == 3 and sid in deck.nsets) or sid == 0)
                if not ok:
                    errors.append(f"{kw} ({loc}): ID {sid} not found for STYP={styp} "
                                  f"(1=part set, 2=part, 3=node set)")
        elif bk.startswith("CONTACT_") and not bk.startswith("CONTACT_ENTITY"):
            if rows2:
                fl = _fields(rows2[0], [10] * 8)
                pairs = [(_int(fl[0] if len(fl) > 0 else ""), _int(fl[2] if len(fl) > 2 else "")),
                         (_int(fl[1] if len(fl) > 1 else ""), _int(fl[3] if len(fl) > 3 else ""))]
                for sid, styp in pairs:
                    if sid == 0:
                        continue
                    ok = ((styp in (0, 1) and (sid in deck.segsets or sid in deck.shsets)) or
                          (styp == 2 and sid in deck.psets) or
                          (styp == 3 and sid in deck.parts) or
                          (styp == 4 and sid in deck.nsets) or
                          (styp == 5) or (styp == 6 and sid in deck.psets))
                    if not ok:
                        errors.append(f"{kw} ({loc}): surface id {sid} not found for type {styp} "
                                      f"(0/1=seg/shell set, 2=part set, 3=part, 4=node set)")

    # unknown keywords
    for kw, rows, f, ln in deck.blocks:
        if not any(kw.startswith(pfx) for pfx in KNOWN_PREFIXES):
            warnings.append(f"unrecognized keyword *{kw} ({Path(f).name}:{ln}) - verify spelling in the manual")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kfile")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args(argv)

    deck = Deck()
    errors, warnings = [], []
    read_deck(a.kfile, deck, errors)
    harvest(deck, errors, warnings)
    check_fixed_alignment(deck, errors)
    crosscheck(deck, errors, warnings)

    stats = {
        "nodes": len(deck.nodes), "elements": len(deck.elements),
        "parts": sorted(deck.parts), "sections": sorted(deck.sections),
        "materials": sorted(deck.mats), "curves": sorted(deck.curves),
        "node_sets": sorted(deck.nsets), "part_sets": sorted(deck.psets),
        "endtim": deck.endtim,
    }
    report = {"errors": errors, "warnings": warnings, "stats": stats,
              "verdict": "FAIL" if errors else "PASS"}
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"== check_kfile: {a.kfile} ==")
    print(f"nodes={stats['nodes']} elements={stats['elements']} parts={stats['parts']} "
          f"mats={stats['materials']} endtim={stats['endtim']}")
    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"warn : {w}")
    print(f"VERDICT: {report['verdict']} ({len(errors)} errors, {len(warnings)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
