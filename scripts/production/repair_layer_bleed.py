"""Repair card-background bleed in the alpha character layers.

The bleed is background that background-removal missed: an enclosed region -
the gap between an arm and a torso, inside a curled tail - where the card colour
survives at full opacity inside the silhouette. The correct repair is to make
those pixels transparent, because that is what they always should have been.

IMMUTABILITY
------------
This never writes to `source_material/`. Repaired layers are a DERIVED asset and
go to `characters/working/repaired_layers/`, leaving the imported originals
untouched (ADR-002: approved art is never overwritten; a revision is a new file).

HOW THE BLEED IS IDENTIFIED
---------------------------
Definitionally, not by guessing at colour families.

For each layer, the card colours are recovered by looking at what its own opaque
source sheet shows WHERE THE LAYER IS TRANSPARENT. Background removal made those
pixels transparent, so whatever is under them is by definition background. Any
colour holding a meaningful share of that region, and saturated enough not to be
cel-art black/white/grey, is a card colour for that sheet.

Opaque pixels in the layer matching a card colour are bleed.

A pink tongue is not the card colour. A hole is, exactly. Two earlier heuristics
- colour families, and "holes lack an enclosing black outline" - both produced
false positives and false negatives confirmed by eye; this does not.

Layers whose source is missing or a different size cannot be measured this way
and are reported UNDETERMINED rather than guessed at.

Usage:
    python scripts/production/repair_layer_bleed.py --dry-run
    python scripts/production/repair_layer_bleed.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYERS = REPO_ROOT / "source_material" / "imported_canon" / "character_layers"
SOURCES = REPO_ROOT / "source_material" / "imported_canon" / "approved_characters"
OUTPUT = REPO_ROOT / "characters" / "working" / "repaired_layers"

#: Minimum share of the transparent region for a colour to count as background.
MIN_BG_SHARE = 0.04
#: Minimum saturation for a background colour. Black, white and grey are cel-art
#: colours; treating them as background would erase the artwork.
MIN_BG_SATURATION = 45
#: Manhattan RGB distance within which a pixel matches a card colour.
MATCH_TOLERANCE = 40
#: Blobs smaller than this are anti-aliasing speckle, not a hole worth reporting.
MIN_BLOB = 40
#: How far beyond a confirmed hole to sweep for anti-aliased blend pixels.
EDGE_SWEEP_PX = 3
#: Looser match used only in that ring, where pixels are card/art blends.
EDGE_TOLERANCE = 150


def background_colours(layer_path: Path, source_path: Path) -> list[np.ndarray] | None:
    """Card colours for this sheet, from source pixels where the layer is clear."""
    with Image.open(layer_path) as image:
        layer = np.asarray(image.convert("RGBA"))
    with Image.open(source_path) as image:
        source = np.asarray(image.convert("RGB")).astype(int)

    if layer.shape[:2] != source.shape[:2]:
        return None

    transparent = layer[..., 3] == 0
    if transparent.sum() < 500:
        return []

    pixels = source[transparent]
    quantised = (pixels // 8) * 8
    values, counts = np.unique(quantised, axis=0, return_counts=True)

    colours = []
    for value, count in zip(values, counts):
        share = count / len(pixels)
        saturation = int(value.max() - value.min())
        if share >= MIN_BG_SHARE and saturation >= MIN_BG_SATURATION:
            colours.append(value)
    return colours


def find_bleed(layer_path: Path, colours: list[np.ndarray]) -> tuple[np.ndarray, list[dict]]:
    """Mask of opaque pixels matching any card colour, plus per-blob detail."""
    from scipy import ndimage

    with Image.open(layer_path) as image:
        arr = np.asarray(image.convert("RGBA")).astype(int)
    rgb, alpha = arr[..., :3], arr[..., 3]

    mask = np.zeros(alpha.shape, dtype=bool)
    for colour in colours:
        mask |= np.abs(rgb - colour).sum(axis=2) < MATCH_TOLERANCE
    mask &= alpha == 255

    labelled, count = ndimage.label(mask)
    keep = np.zeros_like(mask)
    blobs = []
    for index in range(1, count + 1):
        blob = labelled == index
        size = int(blob.sum())
        if size < MIN_BLOB:
            continue
        keep |= blob
        ys, xs = np.where(blob)
        blobs.append({"px": size, "x0": int(xs.min()), "y0": int(ys.min()),
                      "x1": int(xs.max()), "y1": int(ys.max())})

    if keep.any():
        # The core blob is flat card colour, but the pixels ringing it are
        # anti-aliased blends between card and the adjacent art. At the tight
        # match tolerance they survive and leave a coloured hairline along the
        # repaired edge. Sweep the ring with a looser threshold - safe, because
        # it only applies immediately beside a confirmed hole.
        ring = ndimage.binary_dilation(keep, iterations=EDGE_SWEEP_PX) & ~keep
        blend = np.zeros_like(mask)
        for colour in colours:
            blend |= np.abs(rgb - colour).sum(axis=2) < EDGE_TOLERANCE
        keep |= ring & blend & (alpha == 255)

    return keep, blobs


def repair(layer_path: Path, mask: np.ndarray, out_path: Path) -> None:
    """Write a copy of the layer with the bleed made transparent.

    The mask is feathered by one pixel so the new edge does not alias against
    the cel outline it sits beside.
    """
    from scipy import ndimage

    with Image.open(layer_path) as image:
        arr = np.asarray(image.convert("RGBA")).copy()

    alpha = arr[..., 3].astype(np.float32)
    hole = mask.astype(np.float32)
    # Soften by one pixel so the cut edge is not a hard jag.
    soft = ndimage.gaussian_filter(hole, sigma=0.8)
    alpha = alpha * (1.0 - np.clip(soft, 0.0, 1.0))
    arr[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path,
                        default=REPO_ROOT / "docs" / "audits" / "layer-bleed-repair.csv")
    args = parser.parse_args()

    if not LAYERS.is_dir():
        print(f"no layer library at {LAYERS}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    repaired = undetermined = clean = 0
    total_px = 0

    for layer in sorted(LAYERS.glob("*/*.png")):
        rel = layer.relative_to(LAYERS).as_posix()
        source = SOURCES / layer.parent.name / layer.name

        if not source.is_file():
            rows.append({"layer": rel, "status": "UNDETERMINED", "bleed_px": 0,
                         "blobs": 0, "note": "no opaque source sheet"})
            undetermined += 1
            continue

        colours = background_colours(layer, source)
        if colours is None:
            rows.append({"layer": rel, "status": "UNDETERMINED", "bleed_px": 0, "blobs": 0,
                         "note": "layer and source differ in size; cannot align"})
            undetermined += 1
            continue
        if not colours:
            rows.append({"layer": rel, "status": "UNDETERMINED", "bleed_px": 0, "blobs": 0,
                         "note": "no saturated background colour recoverable"})
            undetermined += 1
            continue

        mask, blobs = find_bleed(layer, colours)
        if not blobs:
            rows.append({"layer": rel, "status": "CLEAN", "bleed_px": 0, "blobs": 0,
                         "note": ""})
            clean += 1
            continue

        bleed_px = int(mask.sum())
        total_px += bleed_px
        out = OUTPUT / rel
        if not args.dry_run:
            repair(layer, mask, out)
        rows.append({
            "layer": rel, "status": "REPAIRED", "bleed_px": bleed_px,
            "blobs": len(blobs),
            "note": "; ".join(f"{b['px']}px@{b['x0']},{b['y0']}" for b in blobs[:3]),
        })
        repaired += 1

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["layer", "status", "bleed_px",
                                                    "blobs", "note"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'DRY RUN - ' if args.dry_run else ''}scanned {len(rows)} layers")
    print(f"  CLEAN        {clean}")
    print(f"  REPAIRED     {repaired}   ({total_px} px made transparent)")
    print(f"  UNDETERMINED {undetermined}")
    if not args.dry_run and repaired:
        print(f"\nrepaired layers -> {OUTPUT.relative_to(REPO_ROOT).as_posix()}")
        print("imported originals untouched")
    print(f"report: {args.report.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
