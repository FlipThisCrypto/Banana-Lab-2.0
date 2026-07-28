"""Calibrate a background plate's ground plane and light contract.

A plate is not usable until we know where the floor is and how big a character
standing on it should be. Without that, character scale is guesswork - which is
exactly how the previous system produced a row of equally-sized cut-outs.

Calibration is a small YAML file beside the plate:

    horizon_y                 screen y of the horizon / vanishing point
    calib_foot_y              screen y where the reference object meets the floor
    calib_height_px           that object's screen height in pixels
    calib_height_in_characters  how tall it is, in character heights

From those four numbers the compositor can compute the correct height for a
character standing anywhere on the plane.

Usage:
    python scripts/production/calibrate_plate.py <plate.png> --show
    python scripts/production/calibrate_plate.py <plate.png> --horizon 512 \
        --calib-foot 940 --calib-height 300 --calib-characters 1.6 \
        --key-angle 90 --key-color "#C8322A"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]


def hex_to_rgb(value: str) -> list[int]:
    value = value.lstrip("#")
    return [int(value[i : i + 2], 16) for i in (0, 2, 4)]


def preview(plate: Path, calib: dict, out: Path) -> Path:
    """Draw the horizon, the calibration object and a scale ladder.

    Looking at the ladder is how you catch a wrong horizon in five seconds.
    """
    image = Image.open(plate).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size

    horizon = calib["ground_plane"]["horizon_y"]
    foot = calib["ground_plane"]["calib_foot_y"]
    char_px = calib["ground_plane"]["calib_height_px"]
    in_chars = calib["ground_plane"]["calib_height_in_characters"]

    draw.line([(0, horizon), (width, horizon)], fill=(255, 220, 0, 220), width=3)
    draw.text((8, horizon + 6), f"horizon y={horizon}", fill=(255, 220, 0))

    # The calibration object itself.
    cx = calib["ground_plane"].get("calib_x", width // 2)
    draw.rectangle([cx - 6, foot - char_px, cx + 6, foot], outline=(0, 255, 180, 255), width=3)
    draw.text((cx + 12, foot - char_px), f"ref {char_px}px = {in_chars} char", fill=(0, 255, 180))

    # Scale ladder: a character standing at five depths.
    unit = char_px / in_chars
    calib_drop = foot - horizon
    for i in range(1, 6):
        fy = horizon + calib_drop * (i / 5.0) * 1.6
        if fy >= height or fy <= horizon:
            continue
        h = unit * ((fy - horizon) / calib_drop)
        x = int(width * (0.12 + 0.16 * (i - 1)))
        draw.rectangle([x - h * 0.16, fy - h, x + h * 0.16, fy],
                       outline=(255, 90, 200, 230), width=2)
        draw.ellipse([x - h * 0.18, fy - 4, x + h * 0.18, fy + 4], fill=(255, 90, 200, 120))
        draw.text((x - 10, fy + 6), f"{int(h)}px", fill=(255, 130, 210))

    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, quality=92)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plate", type=Path)
    parser.add_argument("--horizon", type=float, required=True)
    parser.add_argument("--calib-foot", type=float, required=True)
    parser.add_argument("--calib-height", type=float, required=True)
    parser.add_argument("--calib-characters", type=float, default=1.0)
    parser.add_argument("--calib-x", type=int, default=None)
    parser.add_argument("--calib-object", default="unspecified reference object")
    parser.add_argument("--key-angle", type=float, default=90.0,
                        help="degrees; 0=from frame right, 90=overhead, 180=from frame left")
    parser.add_argument("--key-color", default="#FFFFFF")
    parser.add_argument("--fill-color", default="#28303C")
    parser.add_argument("--ground-surface", default="unspecified")
    parser.add_argument("--note", default="")
    parser.add_argument("--show", action="store_true", help="write a preview overlay")
    args = parser.parse_args()

    if not args.plate.is_file():
        print(f"no such plate: {args.plate}", file=sys.stderr)
        return 1

    with Image.open(args.plate) as im:
        size = list(im.size)

    calib = {
        "plate": args.plate.relative_to(REPO_ROOT).as_posix()
        if args.plate.is_absolute() else args.plate.as_posix(),
        "plate_size": size,
        "derivation_note": (
            "Ground-plane values are art-directed estimates read off the plate by "
            "eye and checked against the scale-ladder preview. They are not camera "
            "calibration. Treat as a production convention, not a measurement."
        ),
        "ground_plane": {
            "horizon_y": args.horizon,
            "calib_foot_y": args.calib_foot,
            "calib_height_px": args.calib_height,
            "calib_height_in_characters": args.calib_characters,
            "calib_x": args.calib_x if args.calib_x is not None else size[0] // 2,
            "calib_object": args.calib_object,
            "ground_surface": args.ground_surface,
        },
        "light": {
            "key_angle_deg": args.key_angle,
            "key_color": hex_to_rgb(args.key_color),
            "fill_color": hex_to_rgb(args.fill_color),
        },
        "note": args.note,
    }

    out = args.plate.with_suffix(".calibration.yaml")
    out.write_text(yaml.safe_dump(calib, sort_keys=False), encoding="utf-8")
    print(f"wrote {out}")

    if args.show:
        p = preview(args.plate, calib, args.plate.with_name(args.plate.stem + "_calib_preview.jpg"))
        print(f"wrote {p}")

    unit = args.calib_height / args.calib_characters
    print(f"  one character at the calibration depth = {unit:.0f}px tall")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
