"""Detect card-background contamination in alpha layers, rigorously.

The alpha layers were cut from reference sheets that had a solid coloured card
background. Where background removal missed an enclosed region - the gap between
an arm and a torso, inside a curled tail - a wedge of card colour survives at
full opacity, inside the silhouette. It is invisible on the sheet and obvious on
a dark plate, and it recurs in every panel built from that layer.

METHOD
------
Earlier attempts guessed from colour families ("orange-ish pixels are suspect")
and from an outline heuristic ("holes lack an enclosing black outline"). Both
gave false positives AND false negatives, confirmed by eye - a pink tongue was
flagged, a real hole was cleared.

This does not guess. For each layer it recovers the ACTUAL card colour from the
border of that layer's own opaque source sheet in `approved_characters/`, then
flags opaque pixels within a tight distance of that specific colour.

A tongue is not the card colour. A hole is, exactly.

GUARDS
------
A border sample is only accepted as a card colour when it is:
  * saturated  - rules out black, white and grey, which are cel-art colours.
    Without this, a sheet whose border happens to be black causes every outline
    pixel in the layer to be flagged (measured: 106,753 false positives on
    clever_08_shocked).
  * dominant   - a large enough share of the border to be a background rather
    than an object that happens to touch the edge.

Layers whose source cannot be found, or whose card colour fails these guards,
are reported as UNDETERMINED and sent to human review rather than guessed at.

Usage:
    python scripts/validation/detect_card_bleed.py
    python scripts/validation/detect_card_bleed.py --csv out.csv --sheet out.jpg
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYERS = REPO_ROOT / "source_material" / "imported_canon" / "character_layers"
SOURCES = REPO_ROOT / "source_material" / "imported_canon" / "approved_characters"

#: Manhattan RGB distance within which a pixel counts as the card colour.
#: Tight: the card is a flat fill, so real card pixels sit almost exactly on it.
CARD_TOLERANCE = 40

#: Minimum blob size worth reporting, in pixels.
MIN_BLOB = 40

#: A card colour must be at least this saturated (max channel - min channel).
#: Black, white and grey borders are cel-art colours, not card backgrounds.
MIN_CARD_SATURATION = 45

#: ...and must occupy at least this share of the sampled border.
MIN_CARD_BORDER_SHARE = 0.12

BORDER_PX = 8


def recover_card_colour(source: Path) -> tuple[np.ndarray | None, float, str]:
    """Read the card background colour off the border of an opaque source sheet."""
    with Image.open(source) as image:
        arr = np.asarray(image.convert("RGB")).astype(int)

    border = np.concatenate([
        arr[:BORDER_PX].reshape(-1, 3), arr[-BORDER_PX:].reshape(-1, 3),
        arr[:, :BORDER_PX].reshape(-1, 3), arr[:, -BORDER_PX:].reshape(-1, 3),
    ])
    values, counts = np.unique(border, axis=0, return_counts=True)
    best = values[counts.argmax()]
    share = float(counts.max() / len(border))

    saturation = int(best.max() - best.min())
    if saturation < MIN_CARD_SATURATION:
        return None, share, f"border colour #{best[0]:02X}{best[1]:02X}{best[2]:02X} is not saturated (sat {saturation})"
    if share < MIN_CARD_BORDER_SHARE:
        return None, share, f"border colour occupies only {share:.0%} of the border"
    return best, share, ""


def find_source(layer: Path) -> Path | None:
    candidate = SOURCES / layer.parent.name / layer.name
    return candidate if candidate.is_file() else None


def scan(layer: Path) -> dict:
    """Return a per-layer record: blobs found, or why it is undetermined."""
    record: dict = {
        "layer": layer.relative_to(LAYERS).as_posix(),
        "character": layer.parent.name,
        "status": "CLEAN",
        "card_hex": "",
        "bleed_px": 0,
        "blobs": 0,
        "largest_blob_px": 0,
        "note": "",
        "boxes": [],
    }

    source = find_source(layer)
    if source is None:
        record["status"] = "UNDETERMINED"
        record["note"] = "no matching opaque source sheet in approved_characters"
        return record

    card, share, why = recover_card_colour(source)
    if card is None:
        record["status"] = "UNDETERMINED"
        record["note"] = why
        return record

    record["card_hex"] = "#%02X%02X%02X" % tuple(int(v) for v in card)

    with Image.open(layer) as image:
        arr = np.asarray(image.convert("RGBA")).astype(int)
    rgb, alpha = arr[..., :3], arr[..., 3]

    distance = np.abs(rgb - card).sum(axis=2)
    bleed = (alpha == 255) & (distance < CARD_TOLERANCE)
    if not bleed.any():
        return record

    try:
        from scipy import ndimage
    except ImportError:  # pragma: no cover
        print("scipy is required", file=sys.stderr)
        raise

    labelled, count = ndimage.label(bleed)
    boxes = []
    total = 0
    largest = 0
    for index in range(1, count + 1):
        blob = labelled == index
        size = int(blob.sum())
        if size < MIN_BLOB:
            continue
        ys, xs = np.where(blob)
        boxes.append({"px": size, "x0": int(xs.min()), "y0": int(ys.min()),
                      "x1": int(xs.max()), "y1": int(ys.max())})
        total += size
        largest = max(largest, size)

    if boxes:
        record.update(status="BLEED", bleed_px=total, blobs=len(boxes),
                      largest_blob_px=largest, boxes=boxes)
    return record


def render_sheet(records: list[dict], out: Path, tile: int = 230, cols: int = 6) -> Path:
    """Contact sheet of every detected bleed blob, over a checkerboard."""
    items = [(r, b) for r in records if r["status"] == "BLEED" for b in r["boxes"]]
    if not items:
        return out
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + 30)), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)

    for index, (record, box) in enumerate(items):
        with Image.open(LAYERS / record["layer"]) as image:
            layer = image.convert("RGBA")
        pad = 55
        crop = layer.crop((max(0, box["x0"] - pad), max(0, box["y0"] - pad),
                           min(layer.width, box["x1"] + pad),
                           min(layer.height, box["y1"] + pad)))
        board = Image.new("RGBA", crop.size, (255, 255, 255, 255))
        checker = ImageDraw.Draw(board)
        for y in range(0, crop.height, 12):
            for x in range(0, crop.width, 12):
                if (x // 12 + y // 12) % 2:
                    checker.rectangle([x, y, x + 11, y + 11], fill=(200, 200, 212, 255))
        composed = Image.alpha_composite(board, crop).convert("RGB")
        composed.thumbnail((tile - 8, tile - 8))

        cx = (index % cols) * tile + 4
        cy = (index // cols) * (tile + 30) + 26
        sheet.paste(composed, (cx, cy))
        draw.text((cx, cy - 22), record["layer"][:34], fill=(235, 235, 235))
        draw.text((cx, cy - 11), f"{box['px']}px card {record['card_hex']}",
                  fill=(190, 210, 190))

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path,
                        default=REPO_ROOT / "docs" / "audits" / "layer-card-bleed.csv")
    parser.add_argument("--sheet", type=Path,
                        default=REPO_ROOT / "workspace" / "review" / "layer-card-bleed.jpg")
    args = parser.parse_args()

    if not LAYERS.is_dir():
        print(f"no layer library at {LAYERS}", file=sys.stderr)
        return 1

    records = [scan(p) for p in sorted(LAYERS.glob("*/*.png"))]

    bleeding = [r for r in records if r["status"] == "BLEED"]
    undetermined = [r for r in records if r["status"] == "UNDETERMINED"]
    clean = [r for r in records if r["status"] == "CLEAN"]

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["layer", "character", "status", "card_hex", "bleed_px",
                        "blobs", "largest_blob_px", "note"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"scanned {len(records)} alpha layers")
    print(f"  CLEAN        {len(clean)}")
    print(f"  BLEED        {len(bleeding)}")
    print(f"  UNDETERMINED {len(undetermined)}")
    print(f"\ncsv: {args.csv.relative_to(REPO_ROOT).as_posix()}")

    if bleeding:
        sheet = render_sheet(records, args.sheet)
        print(f"sheet: {sheet}")
        print("\nworst affected:")
        for record in sorted(bleeding, key=lambda r: -r["bleed_px"])[:12]:
            print(f"  {record['layer']:38s} {record['bleed_px']:6d} px  "
                  f"{record['blobs']} blob(s)  card {record['card_hex']}")

    if undetermined:
        print("\nundetermined (sent to human review, not guessed at):")
        for record in undetermined[:10]:
            print(f"  {record['layer']:38s} {record['note']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
