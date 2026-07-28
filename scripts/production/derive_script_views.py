"""Generate the dialogue-only and visual-only views from the panel script.

Both are derived, never hand-edited. `panel-script.yaml` is the single source of
truth; a lettering pass and an art pass need different slices of it, and slices
that drift from their source are worse than no slices at all.

Usage:
    python scripts/production/derive_script_views.py <issue-slug>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

SPEAKER_NAMES = {
    "MZ-CHAR-001": "MOODZ",
    "MZ-CHAR-002": "TWOTONE",
    "MZ-CHAR-003": "STATIC",
    "MZ-CHAR-004": "ASH",
    "MZ-CHAR-005": "NEONBLUE",
    "MZ-CHAR-006": "SCARLINE",
    "MZ-CHAR-LILDEVIL": "LIL DEVIL",
}


def name_of(character_id: str) -> str:
    return SPEAKER_NAMES.get(character_id, character_id)


def build_dialogue_view(data: dict) -> str:
    lines = [
        f"# {data['title']} - Dialogue Only",
        "",
        "Lettering script. Generated from `panel-script.yaml` by",
        "`scripts/production/derive_script_views.py`. Do not hand-edit.",
        "",
        "Word counts are per balloon. House limit is 15.",
        "",
    ]
    page = None
    total_words = 0
    balloon_count = 0
    over_limit = []

    for panel in data["panels"]:
        if panel["page_number"] != page:
            page = panel["page_number"]
            lines += ["", f"## Page {page}", ""]

        pid = panel["panel_id"]
        bits: list[str] = []

        if panel.get("caption"):
            bits.append(f"  CAPTION: {panel['caption']}")
        for balloon in panel.get("dialogue") or []:
            words = len(balloon["text"].split())
            total_words += words
            balloon_count += 1
            if words > 15:
                over_limit.append((pid, words))
            marker = f" [{balloon['bubble_type']}, {words}w]"
            bits.append(f"  {name_of(balloon['speaker'])}: {balloon['text']}{marker}")
        for sfx in panel.get("sound_effects") or []:
            bits.append(f"  SFX: {sfx}")

        if bits:
            lines.append(f"**{pid}**")
            lines += bits
            lines.append("")
        else:
            lines.append(f"**{pid}** - silent")
            lines.append("")

    average = total_words / balloon_count if balloon_count else 0
    lines += [
        "---",
        "",
        "## Lettering summary",
        "",
        f"- Balloons: {balloon_count}",
        f"- Total words in balloons: {total_words}",
        f"- Average balloon length: {average:.1f} words",
        f"- Balloons over the 15-word limit: {len(over_limit)}",
    ]
    for pid, words in over_limit:
        lines.append(f"  - {pid}: {words} words")
    return "\n".join(lines) + "\n"


def build_visual_view(data: dict) -> str:
    lines = [
        f"# {data['title']} - Visual Only",
        "",
        "Art direction script, dialogue stripped. Generated from",
        "`panel-script.yaml` by `scripts/production/derive_script_views.py`.",
        "Do not hand-edit.",
        "",
        "Panel art is **frameless and textless**. Shape and size describe the box",
        "the art is placed into at page assembly.",
        "",
    ]
    page = None
    for panel in data["panels"]:
        if panel["page_number"] != page:
            page = panel["page_number"]
            lines += ["", f"## Page {page}", ""]

        light = panel.get("lighting", {})
        lines += [
            f"### {panel['panel_id']}",
            "",
            f"- **Beat**: {panel['visual_beat']}",
            f"- **Location**: {panel['location']} | **Time**: {panel['time']}",
            f"- **Camera**: {panel['camera_shot']} / {panel['camera_angle']} / {panel['lens_feeling']}",
            f"- **Panel**: {panel['panel_shape']}, {panel['relative_panel_size']}",
            f"- **Background**: {panel['background_description']}",
            f"- **Depth**: {panel['depth_plan']}",
            f"- **Key light**: {light.get('key_direction', '?')} ({light.get('key_color', '?')})",
            f"- **Contact shadow**: {light.get('contact_shadow', '?')}",
            f"- **Colour mood**: {panel['color_mood']}",
            f"- **Scale**: {panel['character_scale']}",
        ]
        blocking = panel.get("character_blocking") or []
        if blocking:
            lines.append("- **Staging**:")
            for entry in blocking:
                lines.append(
                    f"  - {name_of(entry['character_id'])}: {entry['position']} "
                    f"({entry['depth_plane']}) | ground: {entry['ground_contact']} "
                    f"| eyes: {entry['eye_line']} | hands: {entry['hand_activity']}"
                )
        lines.append(f"- **Assets**: {'; '.join(panel['required_source_assets'])}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue", help="issue directory name under issues/")
    args = parser.parse_args()

    issue_dir = REPO_ROOT / "issues" / args.issue
    script_path = issue_dir / "03_script" / "panel-script.yaml"
    if not script_path.is_file():
        print(f"no panel script at {script_path}", file=sys.stderr)
        return 1

    data = yaml.safe_load(script_path.read_text(encoding="utf-8"))

    for name, builder in (
        ("dialogue-only.md", build_dialogue_view),
        ("visual-only.md", build_visual_view),
    ):
        target = issue_dir / "03_script" / name
        target.write_text(builder(data), encoding="utf-8")
        print(f"wrote {target.relative_to(REPO_ROOT).as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
