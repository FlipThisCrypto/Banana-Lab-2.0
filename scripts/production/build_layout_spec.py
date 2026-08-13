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

from app.services.layout_geometry import (
    DENSE_PAGES,
    FRONT_MATTER_PAGES,
    PAGE_TURN_LOCKS,
    TOTAL_BOOK_PAGES,
    layout_page,
    page_side,
    physical_page,
)
from app.services.lettering import (
    CAPTION_FONT,
    DIALOGUE_FONT,
    DIALOGUE_PT_FLOOR,
    DIALOGUE_PT_TARGET,
    SFX_FONT,
    zone_for_balloon,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

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


#: The published boards sit at L* 20-66 with a median chroma of 19 (max 45.8),
#: measured across all 20 pages of both editions. The declared arc above was
#: authored for its STORY meaning - amber, magenta, violet, cyan, near-black,
#: red, amber - and the meaning is right; the intensity was not. Measured before
#: this correction: pages 1-3 at L* 68-72, above the published maximum, and
#: every board at roughly twice the published chroma. Pages 15-17 sat at L*
#: 6.7-9.6, below the published minimum, which also made the near-black panel
#: rule invisible against its own board.
#:
#: So the hue of every board is preserved exactly and only its lightness and
#: chroma are brought into the published band.
BOARD_L_MIN, BOARD_L_MAX = 24.0, 62.0
BOARD_CHROMA_SCALE = 0.52
BOARD_CHROMA_MAX = 30.0


def published_board(hex_colour: str) -> str:
    """Same hue, published lightness and chroma."""
    import numpy as np

    from app.services.likeness import lab_to_srgb_in_gamut, srgb_to_lab

    raw = hex_colour.lstrip("#")
    rgb = np.array([int(raw[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)
    lab = srgb_to_lab(rgb)
    chroma = float(np.hypot(lab[1], lab[2]))

    lightness = min(BOARD_L_MAX, max(BOARD_L_MIN, float(lab[0])))
    target = min(BOARD_CHROMA_MAX, chroma * BOARD_CHROMA_SCALE)
    scale = target / chroma if chroma > 1e-6 else 0.0

    out = lab_to_srgb_in_gamut(
        np.array([lightness, lab[1] * scale, lab[2] * scale]))
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in out)


def _corner_preset(zone_text: str) -> str:
    text = (zone_text or "").lower()
    for key in (
        "upper left",
        "upper right",
        "upper centre",
        "upper center",
        "upper band",
        "upper third",
        "lower left",
        "lower right",
    ):
        if key in text:
            return key.replace("center", "centre")
    return "upper left"


def _bubble_zones(panel: dict, panel_box: list[float]) -> list[dict]:
    """Reserve lettering space, sized against the locked font's real metrics."""
    zone_text = (panel.get("bubble_placement_zone") or "").lower()
    dialogue = panel.get("dialogue") or []
    if "none" in zone_text and not dialogue:
        return []

    balloons: list[tuple[str, str, str]] = []
    for entry in dialogue:
        balloons.append((entry.get("text") or "", entry.get("speaker") or "caption", "speech"))
    if not balloons and "caption" in zone_text:
        balloons.append(("", "caption", "caption"))
    if not balloons:
        return []

    stacked = "stack" in zone_text or (
        len(balloons) == 2 and "left" not in zone_text and "right" not in zone_text
    )
    split_lr = len(balloons) == 2 and "left" in zone_text and "right" in zone_text

    zones: list[dict] = []
    for index, (text, speaker, kind) in enumerate(balloons):
        if split_lr:
            corner = "upper left" if index == 0 else "upper right"
        elif stacked:
            corner = _corner_preset(zone_text)
        else:
            corner = _corner_preset(zone_text)
        box = zone_for_balloon(
            text,
            panel_box,
            corner=corner,
            stack_index=index if stacked else 0,
            stack_count=len(balloons) if stacked else 1,
            kind=kind,
        )
        zones.append({"zone": [round(v, 4) for v in box], "for": speaker, "kind": kind})
    return zones


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
    hard_mismatches: list[dict] = []
    soft_mismatches: list[dict] = []
    previous_structure = ""
    for page_number in sorted(by_page):
        panels = by_page[page_number]
        color, note = FRAME_COLORS.get(page_number, ("#556677", ""))
        color = published_board(color)
        result = layout_page(page_number, panels, prefer_different_from=previous_structure)
        previous_structure = result.structure_name

        for panel, box in zip(panels, result.boxes):
            box["bubble_zones"] = _bubble_zones(panel, box["box"])
            if box.get("shape_verdict") == "hard":
                hard_mismatches.append(
                    {
                        "panel_id": panel["panel_id"],
                        "declared": box["shape"],
                        "target_aspect": box.get("actual_aspect"),
                        "actual_aspect": box.get("actual_aspect"),
                        "page": page_number,
                        "severity": "hard",
                        "reason": box.get("shape_mismatch"),
                    }
                )
            elif box.get("shape_verdict") == "soft":
                soft_mismatches.append(
                    {
                        "panel_id": panel["panel_id"],
                        "declared": box["shape"],
                        "actual_aspect": box.get("actual_aspect"),
                        "page": page_number,
                        "severity": "soft",
                        "reason": box.get("shape_mismatch"),
                    }
                )

        pages.append(
            {
                "page_number": page_number,
                "physical_page": physical_page(page_number),
                "page_side": page_side(page_number),
                "purpose": panels[0].get("narrative_purpose", "")[:70],
                "grid_name": f"p{page_number:02d}-{result.structure_name}",
                "structure": result.structure_name,
                "row_gap": result.row_gap,
                "col_gap": result.col_gap,
                "frame_color": color,
                "frame_note": note,
                "panel_count": len(panels),
                "panels": result.boxes,
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
            "A declared wide must stay clearly landscape; a declared tall must stay clearly portrait.",
            "The generator may not flip a panel's orientation to make the grid work.",
        ],
        "shape_policy": {
            "hard_mismatch_is_illegal": True,
            "soft_mismatch_is_recorded": True,
            "bands": "app.services.layout_geometry.SHAPE_BANDS",
        },
        "hard_shape_mismatches": hard_mismatches,
        "soft_shape_mismatches": soft_mismatches,
        "book_assembly": {
            "total_pages": TOTAL_BOOK_PAGES,
            "front_matter_pages": FRONT_MATTER_PAGES,
            "story_start_physical_page": FRONT_MATTER_PAGES + 1,
            "page_1_is": "recto",
            "page_turn_locks": [
                {
                    **lock,
                    "physical_page": physical_page(lock["story_page"]),
                    "actual_side": page_side(lock["story_page"]),
                    "holds": page_side(lock["story_page"]) == lock["must_be"],
                }
                for lock in PAGE_TURN_LOCKS
            ],
        },
        "lettering": {
            "dialogue_font_file": DIALOGUE_FONT,
            "dialogue_font_name": "Comic Sans MS Bold",
            "caption_font_file": CAPTION_FONT,
            "caption_font_name": "Comic Sans MS",
            "sfx_font_file": SFX_FONT,
            "sfx_font_name": "Impact",
            "dialogue_pt_floor": DIALOGUE_PT_FLOOR,
            "dialogue_pt_target": DIALOGUE_PT_TARGET,
            "print_dpi": 300,
            "note": (
                "Locked 2026-08-13. Comic Sans MS Bold is the production dialogue "
                "face until a licensed comic-lettering font is purchased. Safe "
                "zones are sized from this file's real metrics, not an assumed footprint."
            ),
        },
        "dense_page_gutters": {
            "pages": sorted(DENSE_PAGES),
            "row_gap": 0.024,
            "col_gap": 0.012,
            "reason": (
                "Seven-panel pages. Wider between-row gutter than within-row "
                "gutter is the grouping cue so row boundaries stay readable."
            ),
        },
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
            "edition_stamp": "EDITION FOUR",
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
    print(f"  hard shape mismatches: {len(hard_mismatches)}")
    print(f"  soft shape mismatches: {len(soft_mismatches)}")
    for lock in spec["book_assembly"]["page_turn_locks"]:
        flag = "OK" if lock["holds"] else "FAIL"
        print(
            f"  page-turn lock p{lock['story_page']:02d} "
            f"-> physical {lock['physical_page']} {lock['actual_side']} [{flag}]"
        )
    if hard_mismatches:
        print("HARD mismatches (illegal — the script lost):")
        for item in hard_mismatches:
            print(f"    p{item['page']:02d} {item['panel_id']}: {item['reason']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
