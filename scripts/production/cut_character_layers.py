"""Cut true-alpha character layers from approved pose sheets.

    python scripts/production/cut_character_layers.py "lil devil" --id MZ-CHAR-LILDEVIL

`07_character_staging/missing-assets.md` has recorded this as the issue's only
hard blocker since the first audit:

    **Lil Devil has no true-alpha layer set.** Appears in 17 panels ... Approved
    character art exists and must be background-removed.

The art does exist: 31 pose sheets at 880x1184, the same dimensions as every
other character's cut layers, on a uniform grey field.

THE TRAP, and why this is a flood fill rather than a colour key. The cast are
GREY monkeys on a grey background. Keying on colour alone deletes the character.
Background is therefore defined structurally: the region CONNECTED TO THE BORDER
that matches the border colour. A grey area enclosed by the figure - between an
arm and the torso, inside a curled tail - is not reachable from the border and
stays opaque, which is exactly the matte-hole defect that had to be repaired out
of the existing library afterwards.

Writes to `characters/working/derived_layers/`. Nothing is written into
`source_material/`, which is read-only, and nothing here is approved.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

sys.path.insert(0, ".")

from app.core import paths  # noqa: E402

APPROVED = Path("source_material/imported_canon/approved_characters")
OUT_ROOT = Path("characters/working/derived_layers")
REPORT = Path("docs/audits/derived-layer-cut.json")

#: How far a pixel may sit from the sampled border colour and still be treated
#: as background. The sheets measure 189-193 grey with a border 84-100% uniform,
#: so the field is flat and the tolerance only has to absorb JPEG-ish noise and
#: the anti-aliased rim.
BACKGROUND_TOLERANCE = 26.0

#: Pixels this close to the background colour AND touching the cut edge are
#: feathered rather than kept, which removes the pale halo background removal
#: otherwise leaves around every outline.
EDGE_FEATHER_PX = 1

#: An ENCLOSED region - not reachable from the border - is still background if
#: its colour is the background's. This is the closed gap between a raised arm
#: and the body, which a pure flood fill leaves as an opaque grey blob inside
#: the figure. That is precisely the matte-hole defect that had to be repaired
#: out of the existing library after the fact, so it is prevented here instead.
#:
#: Measured on lildevil_28_celebrating: the enclosed regions are 7575 px at
#: distance 2.6 from the field and 761 px at 6.6 - both background - against
#: 26-33 px regions at distance 19-20, which are the character's cream chest and
#: are art. A tolerance of 10 separates them with room to spare, and the size
#: floor keeps single-pixel noise from being punched out of the linework.
ENCLOSED_TOLERANCE = 10.0
ENCLOSED_MIN_PX = 120


def cut(image: Image.Image) -> tuple[Image.Image, dict]:
    """Return the sheet with a true alpha channel, plus what was measured."""
    rgb = np.asarray(image.convert("RGB")).astype(np.float64)
    height, width = rgb.shape[:2]

    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    field = np.median(border, axis=0)

    near = np.linalg.norm(rgb - field, axis=-1) < BACKGROUND_TOLERANCE

    # Connected to the border is what makes this safe on a grey character.
    labels, count = ndimage.label(near)
    edge_labels = set(labels[0].tolist()) | set(labels[-1].tolist()) \
        | set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    edge_labels.discard(0)
    background = np.isin(labels, list(edge_labels))

    # Enclosed regions that ARE the background colour are background too.
    enclosed_removed = 0
    enclosed_kept = 0
    for region in range(1, count + 1):
        mask = (labels == region) & ~background
        size = int(mask.sum())
        if size == 0:
            continue
        distance = float(np.linalg.norm(rgb[mask].mean(axis=0) - field))
        if size >= ENCLOSED_MIN_PX and distance <= ENCLOSED_TOLERANCE:
            background = background | mask
            enclosed_removed += size
        else:
            enclosed_kept += size

    alpha = np.where(background, 0, 255).astype(np.uint8)

    # Feather the cut edge inward by a pixel so no background-coloured rim
    # survives as a halo around the linework.
    if EDGE_FEATHER_PX > 0:
        mask = Image.fromarray(alpha, "L").filter(
            ImageFilter.MinFilter(2 * EDGE_FEATHER_PX + 1))
        alpha = np.asarray(mask)

    out = np.dstack([np.asarray(image.convert("RGB")), alpha])
    return Image.fromarray(out, "RGBA"), {
        "field_rgb": [int(v) for v in field],
        "transparent_share": round(float((alpha == 0).mean()), 4),
        "enclosed_removed_px": enclosed_removed,
        "enclosed_kept_as_art_px": enclosed_kept,
        "regions": int(count),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help='e.g. "lil devil"')
    ap.add_argument("--id", required=True, help="character id, e.g. MZ-CHAR-LILDEVIL")
    ap.add_argument("--slug", default=None,
                    help="output folder name; defaults to the file-name stem")
    args = ap.parse_args()

    source = APPROVED / args.folder
    if not source.is_dir():
        print(f"no such folder: {source}", file=sys.stderr)
        return 2

    sheets = sorted(p for p in source.glob("*.png"))
    if not sheets:
        print(f"no sheets in {source}", file=sys.stderr)
        return 2

    slug = args.slug or sheets[0].stem.split("_")[0]
    out_dir = OUT_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for sheet in sheets:
        with Image.open(sheet) as image:
            cut_image, measured = cut(image)
        target = out_dir / sheet.name
        paths.assert_safe_write_target(target)
        cut_image.save(target)
        measured["sheet"] = sheet.name
        rows.append(measured)
        print(f"  {sheet.name:34s} transparent {measured['transparent_share']:.3f}  "
              f"holes removed {measured['enclosed_removed_px']:6d}  "
              f"art kept {measured['enclosed_kept_as_art_px']:5d}")

    shares = [r["transparent_share"] for r in rows]
    payload = {
        "character_id": args.id, "slug": slug,
        "source": source.as_posix(), "output": out_dir.as_posix(),
        "status": "CANDIDATE - derived, not approved",
        "sheets": len(rows),
        "transparent_share": {
            "min": round(min(shares), 4), "median": round(float(np.median(shares)), 4),
            "max": round(max(shares), 4),
        },
        "rows": rows,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.is_file() else []
    existing = [e for e in existing if e.get("slug") != slug]
    existing.append(payload)
    REPORT.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    print(f"\n{len(rows)} layers -> {out_dir}")
    print(f"transparent share  min {min(shares):.3f}  "
          f"median {np.median(shares):.3f}  max {max(shares):.3f}")
    print(f"report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
