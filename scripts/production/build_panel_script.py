"""Build `panel-script.yaml` for Issue 001 from structured panel data.

Why a generator rather than hand-authored YAML: at 103 panels the script is
large enough that quoting mistakes become likely and expensive, and every panel
carries the same ~20 required fields. Authoring the data as Python and emitting
YAML makes the required-field contract impossible to forget and the quoting
impossible to get wrong.

`PANELS` below is the authoring source. `panel-script.yaml` is generated and
should not be hand-edited - regenerate instead.

Usage:
    python scripts/production/build_panel_script.py
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ISSUE_DIR = REPO_ROOT / "issues" / "issue-001-neonblue-the-last-light-of-summer"
OUT = ISSUE_DIR / "03_script" / "panel-script.yaml"

# Character shorthands used in the authoring data below.
NB, MZ, TT, ST, ASH, SC, LD = (
    "MZ-CHAR-005", "MZ-CHAR-001", "MZ-CHAR-002",
    "MZ-CHAR-003", "MZ-CHAR-004", "MZ-CHAR-006", "MZ-CHAR-LILDEVIL",
)

GROUNDS = "LOC-festival-grounds"
STAGE = "LOC-festival-main-stage"
CORRIDOR = "LOC-festival-service-corridor"
NODE = "LOC-festival-control-node"

DUSK = "Dusk, sun low"
NIGHT = "Night"
LATE = "Late night, after the countdown"


def block(
    character_id: str,
    position: str,
    depth: str,
    scale: str,
    ground: str,
    eyes: str,
    hands: str,
    **extra: str,
) -> dict:
    """One character staging record. Every field the panel schema requires."""
    entry = {
        "character_id": character_id,
        "position": position,
        "depth_plane": depth,
        "scale_note": scale,
        "ground_contact": ground,
        "eye_line": eyes,
        "hand_activity": hands,
    }
    entry.update(extra)
    return entry


def light(key_dir: str, key_col: str, fill: str, contact: str, **extra: str) -> dict:
    entry = {
        "key_direction": key_dir,
        "key_color": key_col,
        "fill": fill,
        "contact_shadow": contact,
    }
    entry.update(extra)
    return entry


def say(speaker: str, text: str, bubble: str = "speech") -> dict:
    return {"speaker": speaker, "text": text, "bubble_type": bubble}


def panel(
    page: int,
    number: int,
    purpose: str,
    beat: str,
    location: str,
    time: str,
    shot: str,
    angle: str,
    lens: str,
    scale: str,
    background: str,
    depth: str,
    lighting: dict,
    mood: str,
    bubble_zone: str,
    shape: str,
    size: str,
    transition: str,
    assets: list[str],
    qa: list[str],
    blocking: list[dict] | None = None,
    dialogue: list[dict] | None = None,
    caption: str | None = None,
    sfx: list[str] | None = None,
    approach: str = "background_plus_layers",
    **extra,
) -> dict:
    """Assemble one panel record in the order the schema documents it."""
    present = [b["character_id"] for b in (blocking or [])]
    record: dict = {
        "issue_id": "issue-001",
        "page_number": page,
        "panel_number": number,
        "panel_id": f"ISSUE001-P{page:02d}-{number:02d}",
        "narrative_purpose": purpose,
        "visual_beat": beat,
    }
    if dialogue:
        record["dialogue"] = dialogue
    if caption:
        record["caption"] = caption
    if sfx:
        record["sound_effects"] = sfx
    record["characters_present"] = present
    if dialogue:
        record["speaker"] = dialogue[0]["speaker"]
    record.update(
        {
            "location": location,
            "time": time,
            "camera_shot": shot,
            "camera_angle": angle,
            "lens_feeling": lens,
        }
    )
    if blocking:
        record["character_blocking"] = blocking
    record.update(
        {
            "character_scale": scale,
            "background_description": background,
            "depth_plan": depth,
            "lighting": lighting,
            "color_mood": mood,
            "bubble_placement_zone": bubble_zone,
            "panel_shape": shape,
            "relative_panel_size": size,
            "transition_type": transition,
            "generation_approach": approach,
            "required_source_assets": assets,
            "qa_checklist": qa,
            "approval_status": "draft",
        }
    )
    record.update(extra)
    return record


def load_panels() -> list[dict]:
    """Import the panel data. Kept in a separate module for readability."""
    from scripts.production import issue001_panels

    return issue001_panels.build()


HEADER = """# Issue 001 - The Last Light of Summer
# GENERATED FILE - do not hand-edit.
# Source: scripts/production/issue001_panels.py
# Regenerate: python scripts/production/build_panel_script.py
#
# Validates against config/schemas/panel.schema.yaml and
# config/defaults/format-standards.yaml.
#
# Format: single issue. 28 total pages, 22 story pages.
# Standard: canon/rules/FORMAT_STANDARD.md
# Intent and prose direction: full-script.md. Page structure: page-plan.md
#
# Panel art is FRAMELESS and TEXTLESS. panel_shape and relative_panel_size
# describe the box the art is placed into at page assembly; they are never
# rendered into the artwork.
"""


def main() -> int:
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    panels = load_panels()

    pages = sorted({p["page_number"] for p in panels})
    document = {
        "issue_id": "issue-001",
        "title": "The Last Light of Summer",
        "format": "single_issue",
        "page_count": 28,
        "story_page_count": len(pages),
        "panel_count": len(panels),
        "style_standard": "canon/style/HOUSE_STYLE.md",
        "primary_style_reference": (
            "source_material/visual_references/published_editions/"
            "edition-02-the-defusion-tapes"
        ),
        "panels": panels,
    }

    body = yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=100)
    OUT.write_text(HEADER + "\n" + body, encoding="utf-8")

    per_page: dict[int, int] = {}
    for p in panels:
        per_page[p["page_number"]] = per_page.get(p["page_number"], 0) + 1
    counts = [per_page[k] for k in sorted(per_page)]

    print(f"wrote {OUT.relative_to(REPO_ROOT).as_posix()}")
    print(f"  story pages : {len(pages)}")
    print(f"  panels      : {len(panels)}")
    print(f"  per page    : {counts}")
    print(f"  average     : {len(panels) / len(pages):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
