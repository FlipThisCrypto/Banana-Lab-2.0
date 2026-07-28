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
import math
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Aspect of the live area (inside the margins) on an A4 page at 300 dpi.
#: 2149 x 3177 px -> 0.6765. Used to convert fractional boxes into real aspects.
LIVE_ASPECT = 2149 / 3177

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


#: The aspect each declared panel_shape is asking for. Row grouping is chosen to
#: get as close to these as possible.
#:
#: Without this, row packing honoured only relative_panel_size and 52 of 103
#: panels ended up with a box that contradicted their declared shape - a panel
#: written as a wide establishing shot got a portrait box. Since plate
#: generation takes its dimensions from the box, that would have produced the
#: wrong image for half the issue.
TARGET_ASPECT = {
    "wide": 2.40,
    "tall": 0.52,
    "square": 1.00,
    "rectangle": 1.35,
    "inset": 1.15,
    "borderless": 1.50,
    "bleed": 1.50,
    "irregular": 1.30,
    "splash": 0.68,
}

#: Never put more than this many panels in one row - beyond it, reading order
#: gets ambiguous regardless of how well the aspects fit.
MAX_PER_ROW = 3


def _row_partitions(count: int, max_per_row: int = MAX_PER_ROW) -> list[list[list[int]]]:
    """Every contiguous, order-preserving way to split panels into rows.

    Order preserving is not negotiable: reading order is the story order.
    """
    if count == 0:
        return [[]]
    results: list[list[list[int]]] = []

    def walk(start: int, acc: list[list[int]]) -> None:
        if start == count:
            results.append([row[:] for row in acc])
            return
        for size in range(1, min(max_per_row, count - start) + 1):
            acc.append(list(range(start, start + size)))
            walk(start + size, acc)
            acc.pop()

    walk(0, [])
    return results


def _score_partition(
    plan: list[list[int]], panels: list[dict], weights: list[float], gap: float
) -> float:
    """Total squared log-aspect error against each panel's declared shape.

    Log space so that being 2x too wide and 2x too tall cost the same.
    """
    row_weights = [sum(weights[i] for i in row) for row in plan]
    total = sum(row_weights) or 1.0
    usable_h = 1.0 - gap * (len(plan) - 1)

    error = 0.0
    for row, row_weight in zip(plan, row_weights):
        h = usable_h * (row_weight / total)
        if h <= 0:
            return float("inf")
        row_total = sum(weights[i] for i in row) or 1.0
        usable_w = 1.0 - gap * (len(row) - 1)
        for i in row:
            w = usable_w * (weights[i] / row_total)
            # Aspect in page terms; the live area is taller than it is wide.
            aspect = (w * LIVE_ASPECT) / h
            target = TARGET_ASPECT.get(panels[i].get("panel_shape", "rectangle"), 1.35)
            error += (math.log(aspect / target)) ** 2
    return error


def layout_page(page_number: int, panels: list[dict], template: str) -> list[dict]:
    """Divide the live area into boxes that honour both size AND declared shape.

    Row height still follows relative_panel_size, so narrative weight drives
    area. Row *grouping* is chosen by search to best satisfy each panel's
    declared shape.
    """
    weights = [SIZE_WEIGHT.get(p.get("relative_panel_size", "medium"), 1.6) for p in panels]
    count = len(panels)

    # Row grouping is chosen by SEARCH, not from a fixed table. Enumerate every
    # contiguous, order-preserving partition (at most 2^(n-1), n <= 9) and take
    # the one whose resulting boxes best match each panel's declared shape.
    #
    # Order preserving is not negotiable: reading order is story order. Variety
    # comes from how rows are grouped, never from resequencing panels.
    gap = 0.012
    scored = sorted(
        ((_score_partition(p, panels, weights, gap), p) for p in _row_partitions(count)),
        key=lambda pair: pair[0],
    )
    plan = scored[0][1] if scored else [[i] for i in range(count)]

    # Neighbouring pages with the same panel count would otherwise get the same
    # grouping. When a variant is requested, take the runner-up - but only if it
    # is not appreciably worse at honouring the declared shapes.
    use_alternate = template.endswith("-b") or template in {
        "quad-asymmetric", "wide-over-quad", "six-irregular", "stacked-wides",
        "tall-left-stacked-right", "triple-stack", "two-by-two-offset",
        "tall-left-quad-right", "large-over-five",
    }
    if use_alternate and len(scored) > 1 and scored[1][0] <= scored[0][0] * 2.0 + 0.25:
        plan = scored[1][1]

    row_weights = [sum(weights[i] for i in row) for row in plan]
    total = sum(row_weights) or 1.0

    boxes: list[dict] = []
    y = 0.0
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
    shape_mismatches: list[dict] = []
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
        boxes = layout_page(page_number, panels, template)

        # A page must tile completely, so a set of declared shapes can be
        # collectively unsatisfiable. Where the box a panel actually gets
        # contradicts its declared shape, say so in the spec rather than let
        # the disagreement sit there silently - plate generation reads its
        # dimensions from the BOX, so a hidden mismatch produces the wrong image.
        for panel, box in zip(panels, boxes):
            _, _, w, h = box["box"]
            aspect = (w * LIVE_ASPECT) / h if h else 0.0
            declared = panel.get("panel_shape", "rectangle")
            target = TARGET_ASPECT.get(declared, 1.35)
            box["actual_aspect"] = round(aspect, 3)
            if aspect and not (0.62 <= aspect / target <= 1.62):
                box["shape_mismatch"] = (
                    f"script declares '{declared}' (target aspect {target}) but the "
                    f"page can only give this panel {aspect:.2f}. Generate the plate "
                    f"at the ACTUAL aspect, and consider revising the declared shape."
                )
                shape_mismatches.append(
                    {"panel_id": panel["panel_id"], "declared": declared,
                     "target_aspect": target, "actual_aspect": round(aspect, 3),
                     "page": page_number}
                )

        pages.append(
            {
                "page_number": page_number,
                "purpose": panels[0].get("narrative_purpose", "")[:70],
                "grid_name": f"p{page_number:02d}-{template}",
                "frame_color": color,
                "frame_note": note,
                "panel_count": len(panels),
                "panels": boxes,
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
        "shape_mismatches": shape_mismatches,
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
    if shape_mismatches:
        print(f"  shape mismatches: {len(shape_mismatches)} of {spec['panel_count']} panels")
        print("    the page cannot give these panels the aspect the script declares;")
        print("    generate plates at the ACTUAL aspect and consider revising the script")
        for m in shape_mismatches[:8]:
            print(f"      p{m['page']:02d} {m['panel_id']}: declared {m['declared']} "
                  f"(target {m['target_aspect']}) -> actual {m['actual_aspect']}")
        if len(shape_mismatches) > 8:
            print(f"      ... and {len(shape_mismatches) - 8} more; see layout-spec.yaml")
    else:
        print("  shape mismatches: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
