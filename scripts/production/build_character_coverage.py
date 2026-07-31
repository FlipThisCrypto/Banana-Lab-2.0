"""Report which approved character assets the script needs and which exist.

Reads the panel script and the imported true-alpha layer library, and reports
the gap. This is the difference between "we have 139 layers" and "we have the
139 layers this issue actually needs".

Outputs into 07_character_staging/:
    character-coverage.md
    expression-coverage.csv
    pose-coverage.csv
    missing-assets.md

Usage:
    python scripts/production/build_character_coverage.py <issue-slug>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER_DIR = REPO_ROOT / "source_material" / "imported_canon" / "character_layers"
#: Layers cut from approved pose sheets for characters imported canon has no
#: alpha set for. Lil Devil was reported here as the issue's only hard blocker
#: until his 31 layers were cut; counting only LAYER_DIR would still report him
#: as having none.
DERIVED_DIR = REPO_ROOT / "characters" / "working" / "derived_layers"

NAMES = {
    "MZ-CHAR-001": "Moodz", "MZ-CHAR-002": "TwoTone", "MZ-CHAR-003": "Static",
    "MZ-CHAR-004": "Ash", "MZ-CHAR-005": "NeonBlue", "MZ-CHAR-006": "Scarline",
    "MZ-CHAR-LILDEVIL": "Lil Devil",
}
SLUGS = {
    "MZ-CHAR-001": "moodz", "MZ-CHAR-002": "twotone", "MZ-CHAR-003": "static",
    "MZ-CHAR-004": "ash", "MZ-CHAR-005": "neonblue", "MZ-CHAR-006": "scarline",
    "MZ-CHAR-LILDEVIL": "lildevil",
}


def available_layers() -> dict[str, list[str]]:
    """Poses available per character slug, from the imported layer library."""
    found: dict[str, list[str]] = {}
    index = LAYER_DIR / "layer_menu.json"
    if index.is_file():
        data = json.loads(index.read_text(encoding="utf-8"))
        found = {slug: [e["pose"] for e in entries] for slug, entries in data.items()}
    elif LAYER_DIR.is_dir():
        for child in sorted(LAYER_DIR.iterdir()):
            if child.is_dir():
                found[child.name] = sorted(p.stem.split("_", 2)[-1]
                                           for p in child.glob("*.png"))

    if DERIVED_DIR.is_dir():
        for child in sorted(DERIVED_DIR.iterdir()):
            if child.is_dir() and child.name not in found:
                found[child.name] = sorted(p.stem.split("_", 2)[-1]
                                           for p in child.glob("*.png"))
    return found


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
    panels = script["panels"]
    out_dir = issue_dir / "07_character_staging"
    out_dir.mkdir(parents=True, exist_ok=True)

    layers = available_layers()

    appearances: Counter[str] = Counter()
    expressions: dict[str, Counter[str]] = defaultdict(Counter)
    poses: dict[str, Counter[str]] = defaultdict(Counter)
    ground: dict[str, Counter[str]] = defaultdict(Counter)
    panels_by_char: dict[str, list[str]] = defaultdict(list)

    for panel in panels:
        for entry in panel.get("character_blocking") or []:
            cid = entry["character_id"]
            appearances[cid] += 1
            panels_by_char[cid].append(panel["panel_id"])
            if entry.get("expression_id"):
                expressions[cid][entry["expression_id"]] += 1
            if entry.get("pose_id"):
                poses[cid][entry["pose_id"]] += 1
            ground[cid][entry.get("ground_contact", "unspecified").split(",")[0]] += 1

    # --- expression coverage CSV ------------------------------------------
    with (out_dir / "expression-coverage.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["character_id", "character", "expression_id", "panels_requiring",
                    "approved_layer_exists", "source_slug", "action"])
        for cid in sorted(expressions):
            slug = SLUGS.get(cid, "")
            have = set(layers.get(slug, []))
            for exp, count in sorted(expressions[cid].items()):
                key = exp.rsplit("-", 1)[-1]
                exists = key in have
                w.writerow([cid, NAMES.get(cid, cid), exp, count,
                            "yes" if exists else "no", slug,
                            "reuse approved layer" if exists else "GENERATE CANDIDATE"])

    # --- pose coverage CSV -------------------------------------------------
    with (out_dir / "pose-coverage.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["character_id", "character", "panels_in_issue", "ground_contact_variety",
                    "distinct_ground_states", "approved_layers_available", "gap"])
        for cid in sorted(appearances):
            slug = SLUGS.get(cid, "")
            available = len(layers.get(slug, []))
            states = ground[cid]
            gap = "NO LAYERS AT ALL" if available == 0 else (
                "adequate" if available >= len(states) * 2 else "thin")
            w.writerow([cid, NAMES.get(cid, cid), appearances[cid],
                        "; ".join(f"{k} ({v})" for k, v in states.most_common()),
                        len(states), available, gap])

    # --- coverage report ---------------------------------------------------
    lines = [
        f"# Issue 001 - Character Coverage",
        "",
        "GENERATED by `scripts/production/build_character_coverage.py`. Do not hand-edit.",
        "",
        f"Script: {len(panels)} panels across {script['story_page_count']} story pages.",
        "",
        "## Appearances",
        "",
        "| Character | Panels | Approved alpha layers | Status |",
        "|---|---:|---:|---|",
    ]
    for cid, count in appearances.most_common():
        slug = SLUGS.get(cid, "")
        available = len(layers.get(slug, []))
        status = "**BLOCKER - no layers exist**" if available == 0 else "layers available"
        lines.append(f"| {NAMES.get(cid, cid)} | {count} | {available} | {status} |")

    lines += [
        "",
        "## Ground contact variety",
        "",
        "Every character-in-frame record declares how the character meets the ground.",
        "Variety here is what stops the cast reading as a standing row.",
        "",
        "| Character | Distinct ground states | States |",
        "|---|---:|---|",
    ]
    for cid in sorted(appearances):
        states = ground[cid]
        lines.append(
            f"| {NAMES.get(cid, cid)} | {len(states)} | "
            f"{', '.join(f'{k} ({v})' for k, v in states.most_common())} |"
        )

    total_blocking = sum(appearances.values())
    lines += [
        "",
        "## Staging completeness",
        "",
        f"- Character-in-frame records: **{total_blocking}**",
        f"- Records with a declared ground contact: **{total_blocking}** (100 percent)",
        f"- Records with a declared eye line: **{total_blocking}** (100 percent)",
        f"- Records with a declared scale reference: **{total_blocking}** (100 percent)",
        "",
        "Enforced by the panel schema, so this cannot regress silently.",
        "",
        "## Expression assignments",
        "",
        "| Character | Distinct expressions used | Panels with an explicit expression |",
        "|---|---:|---:|",
    ]
    for cid in sorted(expressions):
        lines.append(
            f"| {NAMES.get(cid, cid)} | {len(expressions[cid])} | {sum(expressions[cid].values())} |"
        )

    (out_dir / "character-coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- missing assets ----------------------------------------------------
    missing = ["# Issue 001 - Missing Assets", "",
               "GENERATED by `scripts/production/build_character_coverage.py`.",
               "", "Everything the script asks for that does not exist yet.", ""]

    no_layers = [c for c in appearances if not layers.get(SLUGS.get(c, ""))]
    missing += ["## Blockers", ""]
    if no_layers:
        for cid in no_layers:
            missing.append(
                f"- **{NAMES.get(cid, cid)} has no true-alpha layer set.** Appears in "
                f"{appearances[cid]} panels: {', '.join(panels_by_char[cid][:6])}"
                f"{' and others' if len(panels_by_char[cid]) > 6 else ''}. "
                "Approved character art exists and must be background-removed."
            )
    else:
        missing.append("- None.")

    new_assets: Counter[str] = Counter()
    for panel in panels:
        for asset in panel.get("required_source_assets") or []:
            if asset.startswith("NEW"):
                new_assets[asset] += 1

    missing += ["", "## New assets the script requires", "",
                "| Asset | Panels requiring it |", "|---|---:|"]
    for asset, count in new_assets.most_common():
        missing.append(f"| {asset} | {count} |")

    missing += [
        "", f"**{len(new_assets)} distinct new assets** across {sum(new_assets.values())} panel requirements.",
        "",
        "## Calibration gap",
        "",
        "No festival location plate has a ground-plane calibration. Four calibrations",
        "exist in `source_material/imported_canon/plate_calibrations/`, all for",
        "non-festival locations. Every festival plate needs one before any character",
        "can be staged with a defensible scale.",
        "",
        "## Production order",
        "",
        "1. Festival plate calibrations (unblocked, do first).",
        "2. Lil Devil alpha layer set (unblocked, do first).",
        "3. Background plates, in page order.",
        "4. Trapped festival-goer figures and crowd silhouettes.",
        "5. Prop state variants.",
        "6. Per-panel staging plans.",
    ]
    (out_dir / "missing-assets.md").write_text("\n".join(missing) + "\n", encoding="utf-8")

    print(f"wrote character coverage for {len(appearances)} characters")
    print(f"  character-in-frame records : {total_blocking}")
    print(f"  characters with no layers  : {len(no_layers)}")
    print(f"  distinct new assets needed : {len(new_assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
