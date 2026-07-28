"""Render published-edition PDFs to page images.

The PDF is the untouched imported source. This produces a normalised derivative
so pages can be browsed, compared and used as art direction without opening a
reader. Both are kept, per the migration policy: source copy plus derivative.

Derivatives land in `_pages/` beside the PDF and are excluded from Git by the
same rule that excludes the imported binaries.

Usage:
    python scripts/utilities/render_edition_pages.py [--dpi 130]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EDITIONS = REPO_ROOT / "source_material" / "visual_references" / "published_editions"


def main() -> int:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF is required: pip install pymupdf", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dpi", type=int, default=130)
    args = parser.parse_args()

    if not EDITIONS.is_dir():
        print(f"no published editions at {EDITIONS}", file=sys.stderr)
        return 1

    total = 0
    for pdf in sorted(EDITIONS.rglob("*.pdf")):
        out_dir = pdf.parent / "_pages"
        out_dir.mkdir(exist_ok=True)
        with fitz.open(pdf) as doc:
            page_count = doc.page_count
            for index, page in enumerate(doc, start=1):
                pixmap = page.get_pixmap(dpi=args.dpi)
                target = out_dir / f"{pdf.stem}_p{index:02d}.png"
                pixmap.save(target)
                total += 1
        print(f"{pdf.relative_to(REPO_ROOT).as_posix()} -> {page_count} pages")

    print(f"\nrendered {total} page image(s) at {args.dpi} dpi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
