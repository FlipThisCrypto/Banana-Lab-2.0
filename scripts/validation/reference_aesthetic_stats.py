"""Measure the published editions, so "the right aesthetic" becomes numbers.

The owner supplied two published Fiend Studios editions as the target look.
Eyeballing them produces adjectives; adjectives cannot be checked. This reads
every page of both PDFs and reports the properties that actually differ from
what this pipeline currently produces:

  page ground        Is the page white, or a gradient? Sampled in the margin
                     outside every panel, top band vs bottom band.
  panel inset        Do panels bleed to trim, or float inset on the page?
  panel count        How many panels per page.
  panel saturation   Mean chroma inside panels. The published books put muted
                     environments behind saturated characters; this pipeline
                     currently saturates everything equally.
  value spread       Standard deviation of L* inside panels - how much
                     figure-vs-ground separation there is.
  border weight      Thickness of the panel rule, in page-height percent.

Nothing here judges. It reports, so the comparison can be made against
measured facts rather than impressions.

Usage:  python scripts/validation/reference_aesthetic_stats.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")

from app.services.likeness import srgb_to_lab  # noqa: E402

REFERENCES = {
    "edition-one-fusion-squad":
        r"I:\MonkeyZoo Comic Strip\Fusion Squad\1\TheFusionSquad.pdf",
    "edition-two-defusion-tapes":
        r"I:\MonkeyZoo Comic Strip\Fusion Squad\2\nft\FusionZoo The DeFusion Tapes.pdf",
}
OUT = Path("docs/audits/reference-aesthetic-stats.json")

#: A pixel is "panel ink" if it is dark enough to be a panel rule or outline.
INK_L = 32.0
#: Rows/columns with this share of ink are treated as a panel edge.
EDGE_SHARE = 0.55


def chroma(lab: np.ndarray) -> np.ndarray:
    return np.hypot(lab[..., 1], lab[..., 2])


def page_stats(rgb: np.ndarray) -> dict:
    height, width = rgb.shape[:2]
    lab = srgb_to_lab(rgb.astype(float))
    ink = lab[..., 0] < INK_L

    # Panel extent: the rows and columns that carry a panel rule.
    row_ink = ink.mean(axis=1)
    col_ink = ink.mean(axis=0)
    rows = np.where(row_ink > EDGE_SHARE)[0]
    cols = np.where(col_ink > EDGE_SHARE)[0]

    if rows.size and cols.size:
        top, bottom = int(rows.min()), int(rows.max())
        left, right = int(cols.min()), int(cols.max())
    else:
        top, bottom, left, right = 0, height - 1, 0, width - 1

    # Panel count from horizontal rules: contiguous runs of inked rows.
    runs, run = [], []
    for index, value in enumerate(row_ink > EDGE_SHARE):
        if value:
            run.append(index)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    horizontal_rules = len(runs)

    # Border weight: median thickness of those runs.
    border_px = float(np.median([len(r) for r in runs])) if runs else 0.0

    # The page ground, sampled OUTSIDE the panel block so panel art cannot
    # contaminate it. If there is no margin, the page bleeds and there is no
    # ground to measure.
    margin_top = rgb[: max(1, top - 2)] if top > 6 else None
    margin_bottom = rgb[min(height - 1, bottom + 3):] if bottom < height - 7 else None

    ground = {}
    if margin_top is not None and margin_top.size:
        ground["top_rgb"] = [round(float(v), 1) for v in margin_top.reshape(-1, 3).mean(axis=0)]
    if margin_bottom is not None and margin_bottom.size:
        ground["bottom_rgb"] = [round(float(v), 1)
                                for v in margin_bottom.reshape(-1, 3).mean(axis=0)]
    if "top_rgb" in ground and "bottom_rgb" in ground:
        a = srgb_to_lab(np.array(ground["top_rgb"], dtype=float))
        b = srgb_to_lab(np.array(ground["bottom_rgb"], dtype=float))
        ground["gradient_delta_e"] = round(float(np.linalg.norm(a - b)), 1)

    interior = rgb[top:bottom + 1, left:right + 1]
    interior_lab = srgb_to_lab(interior.astype(float))
    interior_chroma = chroma(interior_lab)

    return {
        "size": [int(width), int(height)],
        "panel_block": {
            "inset_top_pct": round(top / height * 100, 2),
            "inset_bottom_pct": round((height - 1 - bottom) / height * 100, 2),
            "inset_left_pct": round(left / width * 100, 2),
            "inset_right_pct": round((width - 1 - right) / width * 100, 2),
        },
        "horizontal_rules": horizontal_rules,
        "border_weight_pct_of_height": round(border_px / height * 100, 3),
        "page_ground": ground,
        "panel_interior": {
            "mean_chroma": round(float(interior_chroma.mean()), 1),
            "p90_chroma": round(float(np.percentile(interior_chroma, 90)), 1),
            "share_chroma_under_12": round(float((interior_chroma < 12).mean()), 3),
            "share_chroma_over_40": round(float((interior_chroma > 40).mean()), 3),
            "mean_L": round(float(interior_lab[..., 0].mean()), 1),
            "sd_L": round(float(interior_lab[..., 0].std()), 1),
            "ink_share": round(float((interior_lab[..., 0] < INK_L).mean()), 3),
        },
    }


def main() -> int:
    try:
        import fitz
    except ImportError:
        print("PyMuPDF (fitz) is required", file=sys.stderr)
        return 2

    report: dict = {"references": {}}
    for name, path in REFERENCES.items():
        source = Path(path)
        if not source.is_file():
            print(f"missing reference: {source}", file=sys.stderr)
            continue
        document = fitz.open(source)
        pages = []
        for index in range(document.page_count):
            pixmap = document[index].get_pixmap(dpi=100)
            rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n)[..., :3]
            stats = page_stats(rgb)
            stats["page"] = index
            pages.append(stats)
        document.close()
        report["references"][name] = {
            "path": source.as_posix(), "page_count": len(pages), "pages": pages,
        }
        print(f"{name}: {len(pages)} pages")

    every = [p for ref in report["references"].values() for p in ref["pages"]]
    if every:
        def collect(getter):
            values = [getter(p) for p in every if getter(p) is not None]
            return {
                "min": round(float(np.min(values)), 3),
                "median": round(float(np.median(values)), 3),
                "max": round(float(np.max(values)), 3),
            } if values else None

        report["aggregate"] = {
            "aspect": collect(lambda p: p["size"][0] / p["size"][1]),
            "inset_top_pct": collect(lambda p: p["panel_block"]["inset_top_pct"]),
            "inset_left_pct": collect(lambda p: p["panel_block"]["inset_left_pct"]),
            "border_weight_pct": collect(
                lambda p: p["border_weight_pct_of_height"]),
            "gradient_delta_e": collect(
                lambda p: p["page_ground"].get("gradient_delta_e")),
            "mean_chroma": collect(lambda p: p["panel_interior"]["mean_chroma"]),
            "p90_chroma": collect(lambda p: p["panel_interior"]["p90_chroma"]),
            "share_chroma_under_12": collect(
                lambda p: p["panel_interior"]["share_chroma_under_12"]),
            "share_chroma_over_40": collect(
                lambda p: p["panel_interior"]["share_chroma_over_40"]),
            "mean_L": collect(lambda p: p["panel_interior"]["mean_L"]),
            "sd_L": collect(lambda p: p["panel_interior"]["sd_L"]),
            "ink_share": collect(lambda p: p["panel_interior"]["ink_share"]),
        }
        print("\n=== AGGREGATE ACROSS BOTH PUBLISHED EDITIONS ===")
        for key, value in report["aggregate"].items():
            if value:
                print(f"  {key:24s} min {value['min']:8.3f}  "
                      f"median {value['median']:8.3f}  max {value['max']:8.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
