"""Render page thumbnails and a contact sheet from the layout spec.

Layout monotony is the defect this issue exists to correct, and monotony is not
visible in a YAML file. Drawing the grids makes it obvious at a glance whether
two pages share a shape.

Also validates the geometry: overlapping panels, panels escaping the live area,
and area shares that do not agree with the boxes.

Outputs:
    04_storyboards/page-thumbnails/page_NN.png
    04_storyboards/storyboard-contact-sheet.png

Usage:
    python scripts/production/render_layout_thumbnails.py <issue-slug>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]

THUMB_W, THUMB_H = 620, 877  # A4 proportion
MARGIN = 34

SIZE_TINT = {
    "wide": (74, 118, 168),
    "tall": (150, 96, 150),
    "rectangle": (86, 128, 110),
    "square": (168, 132, 74),
    "inset": (168, 86, 86),
}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def check_geometry(page: dict) -> list[str]:
    """Report overlaps, escapes and area-share disagreements."""
    problems: list[str] = []
    boxes = []
    for panel in page["panels"]:
        x, y, w, h = panel["box"]
        pid = panel["panel_id"]
        if x < 0 or y < 0 or x + w > 1.0001 or y + h > 1.0001:
            problems.append(f"{pid}: box escapes the live area")
        declared = panel.get("area_share")
        if declared is not None and abs(declared - w * h) > 0.02:
            problems.append(
                f"{pid}: area_share {declared} disagrees with box area {w * h:.3f}"
            )
        boxes.append((pid, x, y, w, h))

    for i, (pid_a, ax, ay, aw, ah) in enumerate(boxes):
        for pid_b, bx, by, bw, bh in boxes[i + 1 :]:
            overlap_w = min(ax + aw, bx + bw) - max(ax, bx)
            overlap_h = min(ay + ah, by + bh) - max(ay, by)
            if overlap_w > 0.002 and overlap_h > 0.002:
                problems.append(f"{pid_a} overlaps {pid_b}")

    problems += check_reading_order(boxes)
    return problems


def check_reading_order(boxes: list[tuple]) -> list[str]:
    """Panels must appear in reading order: top to bottom, then left to right.

    A layout generator that rearranges panels for visual variety silently
    reorders the story. This catches it.
    """
    problems: list[str] = []
    for i in range(1, len(boxes)):
        pid_prev, px, py, _, ph = boxes[i - 1]
        pid_curr, cx, cy, _, _ = boxes[i]
        same_row = abs(cy - py) < 0.02
        if same_row:
            if cx < px - 0.002:
                problems.append(f"reading order: {pid_curr} sits left of {pid_prev} in the same row")
        elif cy < py + ph - 0.02:
            problems.append(f"reading order: {pid_curr} starts above the bottom of {pid_prev}")
    return problems


def render_page(page: dict) -> Image.Image:
    ground = hex_to_rgb(page.get("frame_color", "#8899AA"))
    image = Image.new("RGB", (THUMB_W, THUMB_H), ground)
    draw = ImageDraw.Draw(image)

    live_w = THUMB_W - 2 * MARGIN
    live_h = THUMB_H - 2 * MARGIN

    for panel in page["panels"]:
        x, y, w, h = panel["box"]
        x0 = MARGIN + x * live_w
        y0 = MARGIN + y * live_h
        x1 = x0 + w * live_w
        y1 = y0 + h * live_h

        tint = SIZE_TINT.get(panel.get("shape", "rectangle"), (100, 100, 100))
        if panel.get("anchor"):
            tint = tuple(min(255, c + 55) for c in tint)
        if panel.get("silent"):
            tint = tuple(int(c * 0.72) for c in tint)

        draw.rectangle([x0, y0, x1, y1], fill=tint, outline=(16, 16, 20), width=3)

        label = panel["panel_id"].replace("ISSUE001-", "")
        draw.text((x0 + 8, y0 + 6), label, fill=(245, 245, 245))
        draw.text((x0 + 8, y0 + 20), f"{panel.get('shape', '?')}", fill=(225, 225, 225))
        if panel.get("silent"):
            draw.text((x0 + 8, y0 + 34), "silent", fill=(230, 230, 200))
        if panel.get("anchor"):
            draw.text((x0 + 8, y0 + 48), "ANCHOR", fill=(255, 245, 200))

        # Balloon zones, drawn as outlines so collisions with faces are visible.
        for zone in panel.get("bubble_zones") or []:
            zx, zy, zw, zh = zone["zone"]
            bx0 = x0 + zx * (x1 - x0)
            by0 = y0 + zy * (y1 - y0)
            draw.rectangle(
                [bx0, by0, bx0 + zw * (x1 - x0), by0 + zh * (y1 - y0)],
                outline=(255, 255, 255),
                width=1,
            )

    draw.text((MARGIN, 10), f"PAGE {page['page_number']} - {page['purpose']}", fill=(250, 250, 250))
    draw.text((MARGIN, THUMB_H - 24), page.get("grid_name", ""), fill=(240, 240, 240))
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue")
    args = parser.parse_args()

    issue_dir = REPO_ROOT / "issues" / args.issue
    spec_path = issue_dir / "05_layouts" / "layout-spec.yaml"
    if not spec_path.is_file():
        print(f"no layout spec at {spec_path}", file=sys.stderr)
        return 1

    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    thumb_dir = issue_dir / "04_storyboards" / "page-thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    problems: list[str] = []
    grids: dict[str, int] = {}
    images = []

    for page in spec["pages"]:
        problems += [f"page {page['page_number']}: {p}" for p in check_geometry(page)]

        grid = page.get("grid_name", "unnamed")
        if grid in grids:
            problems.append(
                f"page {page['page_number']}: grid {grid!r} already used on page {grids[grid]}"
            )
        grids[grid] = page["page_number"]

        image = render_page(page)
        image.save(thumb_dir / f"page_{page['page_number']:02d}.png")
        images.append(image)

    # Contact sheet, 4 across.
    cols = 4
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * THUMB_W, rows * THUMB_H), (24, 24, 28))
    for index, image in enumerate(images):
        sheet.paste(image, ((index % cols) * THUMB_W, (index // cols) * THUMB_H))
    sheet_path = issue_dir / "04_storyboards" / "storyboard-contact-sheet.png"
    sheet.save(sheet_path)

    print(f"wrote {len(images)} thumbnails to {thumb_dir.relative_to(REPO_ROOT).as_posix()}")
    print(f"wrote {sheet_path.relative_to(REPO_ROOT).as_posix()}")

    if problems:
        print(f"\n{len(problems)} geometry problem(s):")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print("\ngeometry OK: no overlaps, no escapes, no repeated grids")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
