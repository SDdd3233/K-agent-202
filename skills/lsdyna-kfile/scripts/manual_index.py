"""Keyword-manual page index: map *KEYWORD names to PDF pages for targeted reading.

The official manuals live in knowledge/manuals/ (run fetch_manuals.py if absent).
Build once:   python manual_index.py build
Look up:      python manual_index.py find MAT_JOHNSON_COOK
              -> prints PDF path + 1-based page range to read with a PDF reader.

Requires: pip install pypdf
"""
import json
import re
import sys
from pathlib import Path

MANUALS_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "manuals"
INDEX_PATH = MANUALS_DIR / "keyword_index.json"


def walk_outline(reader, outline, out, depth=0):
    from pypdf.generic import Destination
    for item in outline:
        if isinstance(item, list):
            walk_outline(reader, item, out, depth + 1)
            continue
        if isinstance(item, Destination):
            title = (item.title or "").strip()
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                continue
            out.append((title, page))


def build():
    from pypdf import PdfReader
    pdfs = sorted(MANUALS_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs in {MANUALS_DIR} - fetch the manuals first:\n"
              f"  python {Path(__file__).parent / 'fetch_manuals.py'}", file=sys.stderr)
        raise SystemExit(1)
    index = {}
    for pdf in pdfs:
        reader = PdfReader(str(pdf))
        entries = []
        try:
            walk_outline(reader, reader.outline, entries)
        except Exception as e:
            print(f"warn: no usable outline in {pdf.name}: {e}", file=sys.stderr)
            continue
        n_pages = len(reader.pages)
        kw_entries = [(t, p) for t, p in entries if t.startswith("*")]
        kw_entries.sort(key=lambda tp: tp[1])
        for i, (title, page) in enumerate(kw_entries):
            name = title.lstrip("*").strip().upper()
            end = kw_entries[i + 1][1] - 1 if i + 1 < len(kw_entries) else min(page + 30, n_pages)
            end = max(end, page)
            index.setdefault(name, []).append(
                {"pdf": pdf.name, "page_start": page, "page_end": end})
        print(f"{pdf.name}: {len(kw_entries)} keyword bookmarks, {n_pages} pages")
    INDEX_PATH.write_text(json.dumps(index, indent=0, sort_keys=True), encoding="utf-8")
    print(f"index written: {INDEX_PATH} ({len(index)} keywords)")


def find(query):
    if not INDEX_PATH.is_file():
        print("index missing - run: python manual_index.py build", file=sys.stderr)
        return 1
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    if not index:
        print("keyword index is empty - manuals were missing when it was built.\n"
              "Run: python fetch_manuals.py   then: python manual_index.py build", file=sys.stderr)
        return 1
    q = query.lstrip("*").strip().upper()
    hits = []
    probe = q
    while probe and not hits:
        if probe in index:
            hits = [(probe, index[probe])]
            break
        pref = [(k, v) for k, v in index.items() if k.startswith(probe)]
        sub = [(k, v) for k, v in index.items() if probe in k and not k.startswith(probe)]
        hits = sorted(pref)[:8] + sorted(sub)[:4]
        if not hits and "_" in probe:
            probe = probe.rsplit("_", 1)[0]   # CONTACT_AUTOMATIC_... -> CONTACT_AUTOMATIC -> CONTACT
        elif not hits:
            break
    if not hits:
        print(f"no match for '{query}'. Try a shorter prefix, e.g. 'MAT_' or 'CONTACT_'")
        return 1
    if probe != q:
        print(f"(no exact entry for '{q}'; the manual groups it under the section below)")
    for name, locs in hits:
        for loc in locs:
            print(f"*{name}  ->  {MANUALS_DIR / loc['pdf']}  pages {loc['page_start']}-{loc['page_end']}")
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == "build":
        build()
        return 0
    if argv[0] == "find":
        return find(" ".join(argv[1:]))
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
