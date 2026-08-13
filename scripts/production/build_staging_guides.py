"""Build per-panel staging guides from the script and the layout spec.

A plate is not scenery. It is a place the cast will stand, with empty space
the lettering already reserved. These guides are what background production
and compositing read. They are generated so they cannot drift from the script.

Regenerate after any script or layout change:
    python scripts/production/build_staging_guides.py <issue-slug>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def build(issue_slug: str) -> int:
    issue_dir = REPO_ROOT / "issues" / issue_slug
    script_path = issue_dir / "03_script" / "panel-script.yaml"
    layout_path = issue_dir / "05_layouts" / "layout-spec.yaml"
    if not script_path.is_file():
        print(f"no panel script at {script_path}", file=sys.stderr)
        return 1
    if not layout_path.is_file():
        print(f"no layout spec at {layout_path}", file=sys.stderr)
        return 1

    script = yaml.safe_load(script_path.read_text(encoding="utf-8"))
    layout = yaml.safe_load(layout_path.read_text(encoding="utf-8"))
    by_id = {}
    for page in layout.get("pages") or []:
        for panel in page.get("panels") or []:
            by_id[panel["panel_id"]] = (page, panel)

    out_dir = issue_dir / "06_backgrounds" / "staging-guides"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for panel in script.get("panels") or []:
        pid = panel["panel_id"]
        page, box = by_id.get(pid, ({}, {}))
        guide = {
            "panel_id": pid,
            "page_number": panel.get("page_number"),
            "generated_from": [
                "03_script/panel-script.yaml",
                "05_layouts/layout-spec.yaml",
            ],
            "narrative_purpose": panel.get("narrative_purpose"),
            "visual_beat": panel.get("visual_beat"),
            "location": panel.get("location"),
            "time": panel.get("time"),
            "camera_shot": panel.get("camera_shot"),
            "camera_angle": panel.get("camera_angle"),
            "background_description": panel.get("background_description"),
            "depth_plan": panel.get("depth_plan"),
            "lighting": panel.get("lighting") or {},
            "color_mood": panel.get("color_mood"),
            "box": box.get("box"),
            "shape": box.get("shape") or panel.get("panel_shape"),
            "actual_aspect": box.get("actual_aspect"),
            "keep_empty": {
                "bubble_zones": box.get("bubble_zones") or [],
                "reason": (
                    "Lettering is placed in space the artwork reserves. "
                    "Do not put faces, hands, or story objects here."
                ),
            },
            "characters": panel.get("character_blocking") or [],
            "required_source_assets": panel.get("required_source_assets") or [],
            "qa_checklist": panel.get("qa_checklist") or [],
            "visual_review_must_answer": [
                "eye goes where the story wants",
                "characters belong in this space",
                "readable without dialogue",
                "connected to neighbours",
                "nothing accidentally generated",
            ],
        }
        dest = out_dir / f"{pid}.yaml"
        header = (
            f"# Staging guide for {pid}\n"
            "# GENERATED - do not hand-edit.\n"
            "# python scripts/production/build_staging_guides.py <issue-slug>\n\n"
        )
        dest.write_text(header + yaml.safe_dump(guide, sort_keys=False, width=100), encoding="utf-8")
        written += 1

    print(f"wrote {written} staging guides to {out_dir.relative_to(REPO_ROOT).as_posix()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue")
    return build(parser.parse_args().issue)


if __name__ == "__main__":
    raise SystemExit(main())
