"""Build the Issue 001 cover: plate, cast, title treatment, stamp, spine.

    python scripts/production/build_cover.py [--takes 4] [--no-generate]

Follows the cover brief in `05_layouts/layout-spec.yaml`:

    Stylised title logo, house style, heavy comic lettering
    Tagline
    NeonBlue central, reaching toward a small light while the festival blacks out
    Lil Devil secondary, raising a fist toward a control box
    Other five Emo Monkeys as supporting silhouettes
    Fiend Studios collectible stamp
    Vertical spine text along the left edge

Two elements of that brief cannot be met from approved material, and are
reported rather than faked:

  - **Lil Devil has no approved alpha layers.** He is named in the brief as the
    secondary figure. No other character is substituted for him and no art is
    invented; he is simply absent, and the run report says so.
  - **The edition number is an open owner question**, recorded in the layout
    spec. The real stamp asset available reads EDITION TWO. It is placed
    unmodified; nothing paints a different number onto the studio's trademark.

Everything written is a candidate. Nothing is approved.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

sys.path.insert(0, ".")

from app.adapters.comfy_client import ComfyClient, write_job_manifest  # noqa: E402
from app.core import paths  # noqa: E402
from app.services import workflows as wf  # noqa: E402
from app.services.compositor import (  # noqa: E402
    GroundPlane, LightContract, Placement, composite_panel,
)
from app.services.cover import (  # noqa: E402
    CoverText, draw_hanging_light, render_cover,
)
from app.services.plate_finish import finish_plate  # noqa: E402

ISSUE = Path("issues/issue-001-neonblue-the-last-light-of-summer")
LAYERS = Path("source_material/imported_canon/character_layers")
REPAIRED = Path("characters/working/repaired_layers")
DERIVED = Path("characters/working/derived_layers")
OUT_PLATES = ISSUE / "06_backgrounds" / "generated_candidates"
OUT_META = ISSUE / "06_backgrounds" / "metadata"
OUT_PAGES = ISSUE / "09_composites" / "sample_pages"
OUT_EXPORT = ISSUE / "14_exports" / "sample"

#: The hero and the five who can actually be staged. Lil Devil is absent
#: because he has no approved layers - see the module docstring.
HERO = ("MZ-CHAR-005", "neonblue", "26_reaching")
#: The brief puts Lil Devil second, raising a fist. 28_celebrating is the
#: closest approved pose - both fists up - and he is staged larger and nearer
#: than the rest of the supporting cast to read as the secondary figure.
SECONDARY = ("MZ-CHAR-LILDEVIL", "lildevil", "28_celebrating", 0.735)
#: (id, folder, pose, x fraction, DEPTH 0..1 where 1 is nearest camera).
#: Depth varies so the cast is not the flat standing row the compositor exists
#: to prevent - the first cover put all five at one baseline and one size.
SUPPORTING = [
    ("MZ-CHAR-001", "moodz", "19_determined", 0.085, 0.95),
    ("MZ-CHAR-003", "static", "16_worried", 0.235, 0.35),
    ("MZ-CHAR-002", "twotone", "24_thinking", 0.845, 0.80),
    ("MZ-CHAR-006", "scarline", "19_determined", 0.925, 0.20),
    ("MZ-CHAR-004", "ash", "18_sleepy", 0.360, 0.60),
]
#: Lil Devil is now stageable: his 31 layers were cut from the approved pose
#: sheets. The control-box prop the brief pairs him with still does not exist.
MISSING: dict[str, str] = {}

COVER_PROMPT = (
    "(night:1.45), (total blackout at a summer funfair:1.4), "
    "(one ferris wheel silhouette against a deep blue night sky:1.35), "
    "every bulb dead and unlit, dead strings of bulbs overhead, "
    "(one single small warm lamp burning low at the centre:1.45), "
    "a narrow pool of warm light on the open ground beneath it, "
    "wide empty trodden ground leading in toward that one light, "
    "(large simple flat shapes:1.35), (only three colours:1.35), "
    "(hard edged flat colour, no gradients, no airbrush:1.35), "
    "(deep black shadow in all four corners:1.3), "
    "(render crowds and rows of objects as large simple massed silhouette "
    "shapes:1.35), (not individual figures or individual objects:1.3), "
    "cover composition, generous empty centre for a figure to stand in, "
    "(clear empty upper third of night sky for a title:1.4), "
    "seen from standing eye level"
)
COVER_NEGATIVE = (
    "aerial view, bird's eye view, isometric, top-down, crowd of detailed "
    "people, hundreds of small figures, busy, cluttered, wimmelbild, "
    "fine intricate detail, tiny text, signage lettering, evenly lit, "
    "bright daylight, airbrushed, soft gradient, painterly, blurry, "
    "photographic bokeh, no linework, people, characters, monkeys, figures"
)


def layer_for(folder: str, pose: str) -> Path | None:
    for base in (REPAIRED, LAYERS, DERIVED):
        exact = base / folder / f"{folder}_{pose}.png"
        if exact.is_file():
            return exact
    for base in (LAYERS, DERIVED):
        found = sorted((base / folder).glob("*.png"))
        if found:
            return found[0]
    return None


def score(path: Path) -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "asc", "scripts/validation/aesthetic_scorecard.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("asc", module)
    spec.loader.exec_module(module)
    with Image.open(path) as image:
        return module.score_page(np.asarray(image.convert("RGB")))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--takes", type=int, default=4)
    ap.add_argument("--seed", type=int, default=770814)
    ap.add_argument("--no-generate", action="store_true",
                    help="re-dress the existing cover plate without the model")
    args = ap.parse_args()

    layout = yaml.safe_load((ISSUE / "05_layouts/layout-spec.yaml")
                            .read_text(encoding="utf-8"))
    bible = yaml.safe_load((ISSUE / "02_issue_bible/issue-bible.yaml")
                           .read_text(encoding="utf-8"))
    width, height = layout["page"]["print_pixels"]

    chosen = OUT_PLATES / "ISSUE001-COVER_finished.png"
    report: dict = {"run": "cover", "status": "CANDIDATE - not approved",
                    "candidates": [], "missing": MISSING,
                    "edition_number": "OPEN OWNER QUESTION - the stamp asset "
                                      "available reads EDITION TWO and was "
                                      "placed unmodified"}

    if not args.no_generate:
        client = ComfyClient()
        if not client.reachable():
            print("ComfyUI is not reachable", file=sys.stderr)
            return 2

        # The cover is a full trim page; generate at its aspect near 1 MP.
        aspect = width / height
        gen_h = int(round(((1_150_000 / aspect) ** 0.5) / 8) * 8)
        gen_w = int(round((gen_h * aspect) / 8) * 8)

        takes = []
        started = time.time()
        for index in range(args.takes):
            seed = args.seed + index * 7919
            graph = wf.background_plate(
                prompt=COVER_PROMPT, negative_extra=COVER_NEGATIVE,
                width=gen_w, height=gen_h, seed=seed,
                filename_prefix="bananalab/cover/ISSUE001-COVER")
            result = client.run(graph, OUT_PLATES, f"ISSUE001-COVER_take{index + 1}")
            if not result.ok:
                continue
            raw = result.images[0]
            finished = raw.with_name(f"{raw.stem}_finished{raw.suffix}")
            paths.assert_safe_write_target(finished)
            finish_plate(raw).save(finished)
            marks = score(finished)
            takes.append((marks, raw, finished, seed))
            report["candidates"].append({
                "seed": seed, "raw": raw.as_posix(), "finished": finished.as_posix(),
                "share_in_large_shapes": round(marks.get("share_in_large_shapes", 0), 3),
                "hairline_ink_density": round(marks.get("hairline_ink_density", 0), 2),
                "C_p95": round(marks.get("C_p95", 0), 1)})
            print(f"  take {index + 1}: share "
                  f"{marks.get('share_in_large_shapes', 0):.3f}  hairline "
                  f"{marks.get('hairline_ink_density', 0):.2f}  "
                  f"C_p95 {marks.get('C_p95', 0):.1f}")

        if not takes:
            print("no cover plate generated", file=sys.stderr)
            return 1

        # A cover wants a clear centre for the hero and a clear top for the
        # title, so the ranking prefers large flat shapes above all.
        takes.sort(key=lambda t: (
            0 if t[0].get("C_p95", 0) >= 50 else 1,
            -t[0].get("share_in_large_shapes", 0),
            t[0].get("hairline_ink_density", 999)))
        best_marks, best_raw, chosen, best_seed = takes[0]
        for entry in report["candidates"]:
            entry["chosen"] = entry["finished"] == chosen.as_posix()
        print(f"  chose seed {best_seed} ({time.time() - started:.0f}s)")

        write_job_manifest(
            OUT_META / "ISSUE001-COVER.job.json",
            job_id="ISSUE001-COVER", job_class="cover_plate",
            workflow_version="cover-1", graph=graph,
            result=type("R", (), {"prompt_id": "", "ok": True, "error": "",
                                  "seconds": 0.0, "images": [best_raw]})(),
            extra={"prompt": COVER_PROMPT, "negative": COVER_NEGATIVE,
                   "seed": best_seed, "note": "SAMPLE cover candidate."})

    plate = Image.open(chosen).convert("RGBA")
    pw, ph = plate.size

    # Stage the cast. The hero stands centre in the pool of light, reaching;
    # the five who have layers flank him, smaller and further back.
    ground = GroundPlane(horizon_y=0.42 * ph, calib_foot_y=0.99 * ph,
                         calib_height_px=0.60 * ph)
    light = LightContract(
        key_angle_deg=90.0, key_color=(255, 196, 128), fill_color=(38, 44, 70),
        key_strength=0.24, fill_strength=0.12, rim_strength=0.16,
        spill_strength=0.14, protect_neutrals=0.85)

    # 0.52 of plate height with feet at 0.965 put giant heads across the bottom
    # third and cropped the boots off the trim. The published covers give the
    # hero about 40% of page height standing clear of the bottom edge.
    placements = [Placement(
        character_id=HERO[0], layer_path=layer_for(HERO[1], HERO[2]),
        centre_x=int(pw * 0.50), foot_y=int(ph * 0.815),
        scale_multiplier=(0.34 * ph) / ground.character_height_at(0.815 * ph),
        depth_plane="foreground", identity_critical=True)]

    secondary_path = layer_for(SECONDARY[1], SECONDARY[2])
    if secondary_path is not None:
        placements.append(Placement(
            character_id=SECONDARY[0], layer_path=secondary_path,
            centre_x=int(pw * SECONDARY[3]), foot_y=int(ph * 0.800),
            scale_multiplier=(0.24 * ph) / ground.character_height_at(0.800 * ph),
            depth_plane="midground", identity_critical=True))
    else:
        report["missing"][SECONDARY[0]] = "no layer found"

    for cid, folder, pose, x, depth in SUPPORTING:
        path = layer_for(folder, pose)
        if path is None:
            report["missing"][cid] = f"{folder} - no layer found"
            continue
        foot = 0.745 + 0.075 * depth
        share = 0.125 + 0.075 * depth
        placements.append(Placement(
            character_id=cid, layer_path=path,
            centre_x=int(pw * x), foot_y=int(ph * foot),
            scale_multiplier=(share * ph) / ground.character_height_at(foot * ph),
            depth_plane="midground" if depth > 0.55 else "background",
            identity_critical=False))

    staged, composite_report = composite_panel(chosen, ground, light, placements)
    report["placements"] = composite_report.placements
    report["warnings"] = composite_report.warnings

    text = CoverText(
        masthead="MONKEYZOO",
        subtitle_lines=["THE LAST LIGHT", "OF SUMMER"],
        tagline="Season one - The Signal Between Us",
        spine="MONKEYZOO  -  THE LAST LIGHT OF SUMMER  -  ISSUE 1",
        # A cover caption is a hook, not a synopsis. The full logline ran to
        # 140 characters and filled the lower third.
        captions=["When the lights go out, somebody has to choose."],
    )

    dressed = staged.resize((width, height), Image.LANCZOS).convert("RGBA")
    # Above and slightly right of the hero's raised hands, so the reach lands.
    # Above the hero's raised hands, not between them: at 0.505 the bulb sat
    # inside the loop his arms make and read as something he was holding.
    draw_hanging_light(dressed, at=(0.515, 0.425), radius_frac=0.038)
    cover = render_cover(dressed, text)
    OUT_PAGES.mkdir(parents=True, exist_ok=True)
    out = OUT_PAGES / "page_00_cover.png"
    paths.assert_safe_write_target(out)
    cover.save(out)

    OUT_EXPORT.mkdir(parents=True, exist_ok=True)
    (OUT_EXPORT / "cover-run-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print(f"\ncover: {out}")
    for record in composite_report.placements:
        print(f"  {record['character_id']:14s} h{record['rendered_height_px']:5d} "
              f"likeness {record['likeness_score']:5.1f} "
              f"{'PASS' if record['likeness_passed'] else 'FAIL'}")
    for cid, why in report["missing"].items():
        print(f"  ABSENT {cid}: {why}")
    print(f"  EDITION NUMBER: {report['edition_number']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
