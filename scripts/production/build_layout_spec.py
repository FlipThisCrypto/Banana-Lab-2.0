"""Generate the layout spec from the panel script.

Panel geometry is derived from the script rather than authored separately, so
the two cannot drift. The generator picks a grid template per page from the
panel count and the panels' declared shapes, then applies the anti-monotony
rules: no template repeats on consecutive pages, and panel area follows the
declared relative_panel_size.

Regenerate after any script change:
    python scripts/production/build_layout_spec.py <issue-slug>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# Relative weight each declared size contributes when dividing a page.
SIZE_WEIGHT = {"xs": 0.6, "small": 1.0, "medium": 1.6, "large": 2.6, "xl": 3.4, "full_page": 8.0}

# Page frame colours, tracking the light progression in the issue bible.
FRAME_COLORS = {
    1: ("#E8A24A", "Warm amber. The good version of the evening."),
    2: ("#E0A257", "Warm amber, holding."),
    3: ("#D89A5C", "Warm gold. Peak festival."),
    4: ("#C08A64", "Cooling gold. Something is off."),
    5: ("#B4527E", "Magenta. The first failure."),
    6: ("#A34C7E", "Magenta, deepening."),
    7: ("#8A4C86", "Cool magenta. It is spreading."),
    8: ("#6E4C8F", "Violet. The pattern."),
    9: ("#5E4A93", "Violet, cooling toward cyan."),
    10: ("#4E4890", "Deep violet. The crack."),
    11: ("#2E5F8C", "Violet-cyan. The splash."),
    12: ("#1E6E82", "Cyan. The gate."),
    13: ("#166374", "Deep cyan. The answer."),
    14: ("#155566", "Deep cyan, darkening."),
    15: ("#141B26", "Near-black. The wound."),
    16: ("#141B26", "Near-black. Permission."),
    17: ("#10151E", "Darkest page ground in the issue."),
    18: ("#4A1A20", "Red-black. The countdown and the three."),
    19: ("#7A1E22", "Deep red. The decision."),
    20: ("#A8622C", "Working amber. Torchlight."),
    21: ("#C8792E", "Working amber, brighter."),
    22: ("#3E5B7A", "Warm and cold together. Neither wins."),
}


def template_name(count: int, index: int) -> str:
    """A grid family name per panel count, varied so neighbours differ."""
    families = {
        1: ["full-page-splash"],
        2: ["tall-pair", "stacked-wides"],
        3: ["large-over-twin", "tall-left-stacked-right", "triple-stack"],
        4: ["wide-anchor-over-trio", "quad-asymmetric", "two-by-two-offset"],
        5: ["four-small-over-wide", "wide-over-quad", "tall-left-quad-right"],
        6: ["twin-wides-over-quad", "six-irregular", "large-over-five"],
        7: ["dense-seven-a", "dense-seven-b"],
    }
    options = families.get(count, [f"grid-{count}"])
    return options[index % len(options)]


def layout_page(page_number: int, panels: list[dict], template: str) -> list[dict]:
    """Divide the live area into boxes whose areas follow declared panel size.

    Rows are packed top to bottom. Panels are grouped into rows so that each row
    holds between one and three panels, and row height is proportional to the
    combined weight of the panels in it.
    """
    weights = [SIZE_WEIGHT.get(p.get("relative_panel_size", "medium"), 1.6) for p in panels]
    count = len(panels)

    # Row plans per panel count. Every plan consumes panel indices in ASCENDING
    # order - reading order is left-to-right, top-to-bottom and must never be
    # rearranged for visual variety. Two plans per count give neighbouring pages
    # of equal panel count different shapes without touching sequence.
    row_plans = {
        1: ([[0]], [[0]]),
        2: ([[0], [1]], [[0], [1]]),
        3: ([[0], [1, 2]], [[0, 1], [2]]),
        4: ([[0], [1, 2], [3]], [[0, 1], [2], [3]]),
        5: ([[0, 1], [2, 3], [4]], [[0], [1, 2], [3, 4]]),
        6: ([[0], [1, 2], [3, 4], [5]], [[0, 1], [2], [3, 4, 5]]),
        7: ([[0, 1], [2, 3, 4], [5], [6]], [[0], [1, 2], [3, 4, 5], [6]]),
    }
    primary, alternate = row_plans.get(
        count, ([[i] for i in range(count)], [[i] for i in range(count)])
    )
    use_alternate = template.endswith("-b") or template in {
        "quad-asymmetric", "wide-over-quad", "six-irregular", "stacked-wides",
        "tall-left-stacked-right", "triple-stack", "two-by-two-offset",
        "tall-left-quad-right", "large-over-five",
    }
    plan = alternate if use_alternate else primary

    row_weights = [sum(weights[i] for i in row) for row in plan]
    total = sum(row_weights) or 1.0

    boxes: list[dict] = []
    y = 0.0
    gap = 0.012
    usable_h = 1.0 - gap * (len(plan) - 1)

    for row, row_weight in zip(plan, row_weights):
        h = usable_h * (row_weight / total)
        x = 0.0
        row_total = sum(weights[i] for i in row) or 1.0
        usable_w = 1.0 - gap * (len(row) - 1)
        for i in row:
            w = usable_w * (weights[i] / row_total)
            panel = panels[i]
            boxes.append(
                {
                    "panel_id": panel["panel_id"],
                    "box": [round(x, 4), round(y, 4), round(w, 4), round(h, 4)],
                    "area_share": round(w * h, 4),
                    "shape": panel.get("panel_shape", "rectangle"),
                    "silent": not panel.get("dialogue"),
                    "anchor": panel.get("relative_panel_size") in ("large", "xl", "full_page"),
                    "bubble_zones": _bubble_zones(panel),
                }
            )
            x += w + gap
        y += h + gap
    return boxes


def _bubble_zones(panel: dict) -> list[dict]:
    """Reserve lettering space in the zone the script names."""
    zone_text = (panel.get("bubble_placement_zone") or "").lower()
    if "none" in zone_text:
        return []
    presets = {
        "upper left": [0.04, 0.05, 0.42, 0.20],
        "upper right": [0.54, 0.05, 0.42, 0.20],
        "upper centre": [0.28, 0.05, 0.44, 0.20],
        "upper band": [0.04, 0.05, 0.92, 0.18],
        "upper third": [0.10, 0.04, 0.80, 0.26],
        "lower left": [0.04, 0.74, 0.42, 0.20],
        "lower right": [0.54, 0.74, 0.42, 0.20],
    }
    for key, box in presets.items():
        if key in zone_text:
            return [{"zone": box, "for": panel.get("speaker") or "caption"}]
    return [{"zone": [0.04, 0.05, 0.44, 0.20], "for": panel.get("speaker") or "caption"}]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue")
    args = parser.parse_args()

    issue_dir = REPO_ROOT / "issues" / args.issue
    script_path = issue_dir / "03_script" / "panel-script.yaml"
    if not script_path.is_file():
        print(f"no panel script at {script_path}", file=sys.stderr)
        return 1

    script = yaml.safe_load(script_path.read_text(encoding="utf-8"))
    by_page: dict[int, list[dict]] = {}
    for panel in script["panels"]:
        by_page.setdefault(panel["page_number"], []).append(panel)

    pages = []
    previous_template = ""
    variant = 0
    for page_number in sorted(by_page):
        panels = by_page[page_number]
        template = template_name(len(panels), variant)
        if template == previous_template:
            variant += 1
            template = template_name(len(panels), variant)
        previous_template = template
        variant += 1

        color, note = FRAME_COLORS.get(page_number, ("#556677", ""))
        pages.append(
            {
                "page_number": page_number,
                "purpose": panels[0].get("narrative_purpose", "")[:70],
                "grid_name": f"p{page_number:02d}-{template}",
                "frame_color": color,
                "frame_note": note,
                "panel_count": len(panels),
                "panels": layout_page(page_number, panels, template),
            }
        )

    spec = {
        "issue_id": script["issue_id"],
        "generated_from": "03_script/panel-script.yaml",
        "generator": "scripts/production/build_layout_spec.py",
        "format": "single_issue",
        "page_count": script["page_count"],
        "story_page_count": script["story_page_count"],
        "panel_count": script["panel_count"],
        "page": {
            "trim_width_mm": 210,
            "trim_height_mm": 297,
            "bleed_mm": 3,
            "safe_margin_mm": 10,
            "live_margin_mm": 14,
            "gutter_mm": 4,
            "print_dpi": 300,
            "print_pixels": [2480, 3508],
            "web_pixels": [1240, 1754],
        },
        "page_ground": {
            "style": "coloured_board_with_frame",
            "reference": (
                "source_material/visual_references/published_editions/"
                "edition-02-the-defusion-tapes"
            ),
            "panel_border_mm": 1.2,
            "panel_border_color": "#101014",
        },
        "rules": [
            "No two consecutive pages may use the same grid.",
            "No page may divide into equal rows of equal panels.",
            "Panel area tracks narrative weight via relative_panel_size.",
            "Reading order must be unambiguous without arrows or numbers.",
            "Balloon zones never overlap a face or a hand.",
            "Panel art is frameless and textless.",
        ],
        "pages": pages,
        "cover": {
            "required_elements": [
                "Stylised title logo, house style, heavy comic lettering",
                "Tagline",
                "NeonBlue central, reaching toward a small light while the festival blacks out",
                "Lil Devil secondary, raising a fist toward a control box",
                "Other five Emo Monkeys as supporting silhouettes",
                "Fiend Studios collectible stamp",
                "Vertical spine text along the left edge",
            ],
            "cover_concept_source": "SEASON-BIBLE.md section 19, August",
            "open_question": (
                "Edition number for the stamp. Published editions are One, Two and Three. "
                "Requires an owner decision."
            ),
        },
    }

    out = issue_dir / "05_layouts" / "layout-spec.yaml"
    header = (
        "# Issue 001 - Layout specification\n"
        "# GENERATED FILE - do not hand-edit.\n"
        "# Source: 03_script/panel-script.yaml\n"
        "# Regenerate: python scripts/production/build_layout_spec.py <issue-slug>\n"
        "#\n"
        "# Coordinates are fractions of the LIVE AREA (inside the margins), origin\n"
        "# top-left. Panel art is placed into these boxes; the boxes are never\n"
        "# rendered into the art.\n\n"
    )
    out.write_text(header + yaml.safe_dump(spec, sort_keys=False, width=100), encoding="utf-8")

    print(f"wrote {out.relative_to(REPO_ROOT).as_posix()}")
    print(f"  pages   : {len(pages)}")
    print(f"  grids   : {len({p['grid_name'] for p in pages})} distinct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
