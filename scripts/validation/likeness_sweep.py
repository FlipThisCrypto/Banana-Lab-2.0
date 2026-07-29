"""Measure likeness across the whole approved layer library, under real relight.

"100% consistent likeness" is a claim that has to be tested against every layer
the pipeline can use, not against the two that were convenient. This runs the
likeness metric over all of them and reports the distribution.

Each layer is relit with a representative scene light and scored. A layer that
fails here will fail in any panel that uses it, so this is the gate that decides
whether the library is production-ready.

Usage:
    python scripts/validation/likeness_sweep.py
    python scripts/validation/likeness_sweep.py --protect 0.0   # show the regression
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.services.compositor import (  # noqa: E402
    LightContract, erode_alpha, relight, trim_alpha,
)
from app.services.likeness import measure  # noqa: E402

LAYERS = REPO_ROOT / "source_material" / "imported_canon" / "character_layers"
#: Repaired derivatives take precedence: they are the same art with card bleed
#: removed, and they are what production actually composites.
REPAIRED = REPO_ROOT / "characters" / "working" / "repaired_layers"

CHARACTER_IDS = {
    "neonblue": "MZ-CHAR-005", "moodz": "MZ-CHAR-001", "twotone": "MZ-CHAR-002",
    "static": "MZ-CHAR-003", "ash": "MZ-CHAR-004", "scarline": "MZ-CHAR-006",
    "clever": "MZ-CHAR-CLEVER", "zombie": "MZ-CHAR-ZOMBIE",
}

#: Three representative scene lights. A layer must hold up under all of them,
#: not just under the one it was tuned on.
SCENES = {
    "cool-corridor": dict(key_angle_deg=90.0, key_color=(150, 225, 235),
                          fill_color=(30, 70, 80), spill=(40, 90, 100)),
    "warm-festival": dict(key_angle_deg=20.0, key_color=(255, 190, 120),
                          fill_color=(70, 55, 40), spill=(120, 80, 45)),
    "red-emergency": dict(key_angle_deg=90.0, key_color=(230, 90, 70),
                          fill_color=(60, 25, 25), spill=(110, 40, 35)),
}


def load_contamination() -> dict[str, int | None]:
    """Card-bleed pixel counts per layer, or None where the status is unknown.

    None is not zero. The detector reports UNDETERMINED for layers it cannot
    align against their source sheet, and this used to fall through as "no
    bleed recorded" - 49 of 139 layers were scored contamination_px=0 and
    passed on an assumption nobody had checked. The repair pass resolves some
    of them, so its verdict is read too, and only layers still undetermined
    after BOTH passes are reported as unknown.
    """
    detected = REPO_ROOT / "docs" / "audits" / "layer-card-bleed.csv"
    repaired = REPO_ROOT / "docs" / "audits" / "layer-bleed-repair.csv"
    if not detected.is_file():
        return {}

    out: dict[str, int | None] = {}
    with detected.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            status = row.get("status")
            if status == "BLEED":
                out[row["layer"]] = int(row.get("bleed_px") or 0)
            elif status == "CLEAN":
                out[row["layer"]] = 0
            else:
                out[row["layer"]] = None

    if repaired.is_file():
        with repaired.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("status") in {"REPAIRED", "CLEAN"}:
                    # The repair pass aligned it and dealt with it, so the
                    # layer's status is known whatever the detector thought.
                    out[row["layer"]] = 0
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--protect", type=float, default=0.85,
                        help="protect_neutrals value to test (0.0 reproduces the regression)")
    parser.add_argument("--csv", type=Path,
                        default=REPO_ROOT / "docs" / "audits" / "likeness-sweep.csv")
    args = parser.parse_args()

    if not LAYERS.is_dir():
        print(f"no layer library at {LAYERS}", file=sys.stderr)
        return 1

    contamination = load_contamination()
    rows: list[dict] = []

    for layer in sorted(LAYERS.glob("*/*.png")):
        character = layer.parent.name
        cid = CHARACTER_IDS.get(character, character)
        rel = layer.relative_to(LAYERS).as_posix()

        use = REPAIRED / rel if (REPAIRED / rel).is_file() else layer
        try:
            image = erode_alpha(trim_alpha(Image.open(use).convert("RGBA")), 1)
        except Exception as exc:  # pragma: no cover
            rows.append({"layer": rel, "character": character, "scene": "-",
                         "score": 0.0, "passed": False, "note": f"unreadable: {exc}"})
            continue

        for scene_name, scene in SCENES.items():
            light = LightContract(
                key_angle_deg=scene["key_angle_deg"], key_color=scene["key_color"],
                fill_color=scene["fill_color"], key_strength=0.22, fill_strength=0.10,
                rim_strength=0.10, spill_strength=0.14,
                protect_neutrals=args.protect,
            )
            # Contamination only counts against a layer that has NOT been
            # repaired; a repaired layer no longer carries it.
            # `use` is the repaired layer when one exists; its bleed is fixed.
            bleed = 0 if use != layer else contamination.get(rel, None)
            # Compare the prepared layer against its own relit self, so the
            # comparison stays on the exact pixel-aligned path. Passing the
            # on-disk file here would be a size mismatch, because `image` has
            # been trimmed and eroded.
            result = measure(
                relight(image, light, spill_color=scene["spill"]),
                image, cid, contamination_px=bleed, layer_name=rel,
            )
            rows.append({
                "layer": rel, "character": character, "scene": scene_name,
                "source": "repaired" if use != layer else "original",
                "score": result.score, "passed": result.passed,
                "palette_score": round(result.palette_score, 1),
                "palette_delta_e": round(result.palette_delta_e, 2),
                "contamination_score": round(result.contamination_score, 1),
                "contamination_px": result.contamination_px,
                "legibility_score": round(result.feature_legibility_score, 1),
                "note": "; ".join(result.notes)[:200],
            })

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    scores = sorted(r["score"] for r in rows)
    layers = {r["layer"] for r in rows}
    failing_layers = {r["layer"] for r in rows if not r["passed"]}

    print(f"protect_neutrals = {args.protect}")
    print(f"measurements     : {total}  ({len(layers)} layers x {len(SCENES)} scenes)")
    print(f"PASS             : {passed} / {total}  ({passed / total:.1%})")
    print(f"layers all-scene clean : {len(layers) - len(failing_layers)} / {len(layers)}")
    print(f"score  min {scores[0]:.1f}   median {scores[len(scores)//2]:.1f}   max {scores[-1]:.1f}")

    by_reason: dict[str, int] = {}
    for row in rows:
        if row["passed"]:
            continue
        if row.get("contamination_px"):
            key = "card-bleed contamination"
        elif row.get("palette_score", 100) < 92:
            key = "palette drift"
        elif row.get("legibility_score", 100) < 85:
            key = "too small to prove legibility"
        else:
            key = "other"
        by_reason[key] = by_reason.get(key, 0) + 1
    if by_reason:
        print("\nfailure reasons:")
        for reason, count in sorted(by_reason.items(), key=lambda kv: -kv[1]):
            print(f"  {count:4d}  {reason}")

    worst = sorted(rows, key=lambda r: r["score"])[:10]
    print("\nlowest scoring:")
    for row in worst:
        print(f"  {row['score']:5.1f}  {row['layer']:36s} {row['scene']:14s} {row['note'][:60]}")

    print(f"\ncsv: {args.csv.relative_to(REPO_ROOT).as_posix()}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
