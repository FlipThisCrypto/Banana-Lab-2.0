"""Flag card-background contamination in the approved true-alpha character layers.

The layer library was produced by background-removing reference sheets that had
solid coloured card backgrounds (orange, green, pink, magenta). Where the
removal missed an enclosed region - the gap between an arm and a torso, between
legs, inside a curled tail - a flat wedge of card colour survives at full
opacity, inside the character's silhouette.

It is invisible on the reference sheet and obvious once the layer is composited
over a dark plate. It will recur in every panel built from that layer.

WHAT THIS TOOL DOES AND DOES NOT DO
-----------------------------------
It FLAGS candidates and renders them for human review. It does not classify.

Automated classification was attempted and abandoned: a "matte hole is not
enclosed by a black outline" heuristic gave false negatives (a hole bordered by
the character's own outline on two sides scored as legitimate) AND false
positives (a pink tongue inside a black mouth scored as a hole). Both were
confirmed by eye.

So this follows the project rule - a machine gate may only reject, never approve
(ADR-005). Every flagged blob goes to a contact sheet and a human decides.

Usage:
    python scripts/validation/sweep_layer_mattes.py
    python scripts/validation/sweep_layer_mattes.py --sheet out.jpg --csv out.csv
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

#: Minimum blob size worth a human's attention, in pixels.
MIN_BLOB = 60

#: Card-background families seen in the source reference sheets. Deliberately
#: broad - this is a flagging pass, and a false positive costs a glance.
def _candidate_mask(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    orange = (r > 170) & (g > 90) & (g < 190) & (b < 130) & ((r - b) > 70)
    magenta = (r > 170) & (b > 150) & (g < 140) & ((r - g) > 60) & ((b - g) > 40)
    lime = (g > 170) & (r < 170) & (b < 150) & ((g - r) > 50) & ((g - b) > 60)
    return (alpha == 255) & (orange | magenta | lime) & (saturation > 60)


def _label(mask: np.ndarray) -> tuple[np.ndarray, int]:
    try:
        from scipy import ndimage
    except ImportError:  # pragma: no cover
        print("scipy is required for connected-component labelling", file=sys.stderr)
        raise
    return ndimage.label(mask)


def scan_layer(path: Path) -> list[dict]:
    with Image.open(path) as image:
        arr = np.asarray(image.convert("RGBA"))
    rgb = arr[..., :3].astype(int)
    alpha = arr[..., 3]

    mask = _candidate_mask(rgb, alpha)
    if mask.sum() < MIN_BLOB:
        return []

    labelled, count = _label(mask)
    blobs: list[dict] = []
    for index in range(1, count + 1):
        blob = labelled == index
        size = int(blob.sum())
        if size < MIN_BLOB:
            continue
        ys, xs = np.where(blob)
        blobs.append(
            {
                "layer": path.relative_to(LAYERS).as_posix(),
                "character": path.parent.name,
                "pixels": size,
                "x0": int(xs.min()), "x1": int(xs.max()),
                "y0": int(ys.min()), "y1": int(ys.max()),
                "mean_rgb": "#%02X%02X%02X" % tuple(int(v) for v in rgb[blob].mean(axis=0).round()),
                # Where it sits vertically, as a fraction. Mouth-height blobs are
                # usually tongues; lower-body blobs usually are not.
                "body_fraction": round(float(ys.mean() / arr.shape[0]), 3),
                "verdict": "UNREVIEWED",
            }
        )
    return blobs


def render_sheet(blobs: list[dict], out: Path, tile: int = 240, cols: int = 6) -> Path:
    """Contact sheet of every flagged blob, over a checkerboard so alpha shows."""
    rows = (len(blobs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + 30)), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)

    for index, blob in enumerate(blobs):
        with Image.open(LAYERS / blob["layer"]) as image:
            layer = image.convert("RGBA")
        pad = 60
        box = (
            max(0, blob["x0"] - pad), max(0, blob["y0"] - pad),
            min(layer.width, blob["x1"] + pad), min(layer.height, blob["y1"] + pad),
        )
        crop = layer.crop(box)

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
        draw.text((cx, cy - 22), blob["layer"][:34], fill=(235, 235, 235))
        draw.text((cx, cy - 11),
                  f"{blob['pixels']}px {blob['mean_rgb']} y={blob['body_fraction']}",
                  fill=(180, 200, 180))

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sheet", type=Path,
                        default=REPO_ROOT / "workspace" / "review" / "layer-matte-sweep.jpg")
    parser.add_argument("--csv", type=Path,
                        default=REPO_ROOT / "docs" / "audits" / "layer-matte-sweep.csv")
    args = parser.parse_args()

    if not LAYERS.is_dir():
        print(f"no layer library at {LAYERS}", file=sys.stderr)
        return 1

    files = sorted(LAYERS.glob("*/*.png"))
    blobs: list[dict] = []
    for path in files:
        blobs.extend(scan_layer(path))

    blobs.sort(key=lambda b: -b["pixels"])
    affected = {b["layer"] for b in blobs}

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(blobs[0].keys()) if blobs else
                                ["layer", "character", "pixels", "x0", "x1", "y0", "y1",
                                 "mean_rgb", "body_fraction", "verdict"])
        writer.writeheader()
        writer.writerows(blobs)

    print(f"scanned {len(files)} approved alpha layers")
    print(f"flagged {len(blobs)} blob(s) across {len(affected)} layer(s)")
    print(f"  csv   : {args.csv.relative_to(REPO_ROOT).as_posix()}")

    if blobs:
        sheet = render_sheet(blobs, args.sheet)
        print(f"  sheet : {sheet}")
        print("\nEVERY BLOB IS UNREVIEWED. A human must classify each one as")
        print("MATTE_HOLE (repair the layer) or ART (tongue, accessory, prop).")
        print("Automated classification was tried and is not reliable - see the")
        print("module docstring.")

    by_character: dict[str, int] = {}
    for blob in blobs:
        by_character[blob["character"]] = by_character.get(blob["character"], 0) + 1
    if by_character:
        print("\nflagged blobs by character:")
        for character, count in sorted(by_character.items(), key=lambda kv: -kv[1]):
            print(f"  {character:10s} {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
