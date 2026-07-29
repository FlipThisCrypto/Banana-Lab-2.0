"""Re-sweep protect_neutrals against the CORRECTED relight.

0.85 was chosen when relight preserved hue by scaling RGB ratios, which did not
actually preserve hue (see LIKENESS_TUNING_REPORT.md, Fix 4). relight() now
recombines in Lab, so the parameter means something different and its old value
carries no evidence.

The sweep reports two numbers per level, and BOTH matter:

  library pass   - how much legitimate art survives
  control escape - how much deliberately broken art also survives

A protection level that maximises the first while letting the second rise above
zero is a worse setting, not a better one. A level that passes everything is a
failed experiment.

Usage:  python scripts/validation/protection_sweep.py [--per-character N]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, ".")

from app.services.compositor import (  # noqa: E402
    LightContract, erode_alpha, relight, trim_alpha,
)
from app.services.likeness import measure  # noqa: E402

sys.path.insert(0, "scripts/validation")
from control_sweep import (  # noqa: E402
    CONTROLS, MIN_APPLICABLE_SHIFT, SCENES, applied_chroma_shift,
)

LAYERS = Path("source_material/imported_canon/character_layers")
REPAIRED = Path("characters/working/repaired_layers")

LEVELS = [0.70, 0.80, 0.85, 0.90, 0.95, 1.00]


def stratified(per_character: int) -> list[Path]:
    """Even coverage across the cast, not the first N files alphabetically.

    Sampling the head of the list gave a run that probed only Ash.
    """
    by_character: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(LAYERS.glob("*/*.png")):
        by_character[path.parent.name].append(path)
    picked: list[Path] = []
    for character, paths in sorted(by_character.items()):
        step = max(1, len(paths) // per_character)
        picked.extend(paths[::step][:per_character])
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-character", type=int, default=3)
    args = ap.parse_args()

    paths = stratified(args.per_character)
    prepared = []
    for path in paths:
        rel = path.relative_to(LAYERS).as_posix()
        use = REPAIRED / rel if (REPAIRED / rel).is_file() else path
        prepared.append(
            (rel, erode_alpha(trim_alpha(Image.open(use).convert("RGBA")), 1))
        )
    print(f"layers: {len(prepared)} across "
          f"{len({r.split('/')[0] for r, _ in prepared})} characters\n")

    print(f"{'protect':>8s}{'library pass':>15s}{'min':>7s}{'median':>8s}"
          f"{'control escapes':>17s}{'best broken':>13s}")
    for level in LEVELS:
        scores: list[float] = []
        broken_scores: list[float] = []
        escapes = 0
        for rel, canon in prepared:
            for scene in SCENES.values():
                light = LightContract(
                    key_angle_deg=scene["a"], key_color=scene["k"],
                    fill_color=scene["f"], key_strength=0.22, fill_strength=0.10,
                    rim_strength=0.10, spill_strength=0.14,
                    protect_neutrals=level,
                )
                lit = relight(canon, light, spill_color=scene["s"])
                scores.append(measure(lit, canon, "X", layer_name=rel).score)

                for build in CONTROLS.values():
                    bad = build(canon, scene)
                    if applied_chroma_shift(canon, bad) < MIN_APPLICABLE_SHIFT:
                        continue
                    result = measure(bad, canon, "X", layer_name=rel)
                    broken_scores.append(result.score)
                    escapes += 1 if result.passed else 0

        arr = np.array(scores)
        passed = int((arr >= 95.0).sum())
        best_broken = max(broken_scores) if broken_scores else float("nan")
        flag = "" if escapes == 0 else "   <-- GATE TOO LOOSE"
        print(f"{level:8.2f}{passed:>9d}/{len(arr):<5d}{arr.min():7.1f}"
              f"{np.median(arr):8.1f}{escapes:17d}{best_broken:13.1f}{flag}")

    print("\nPick the level with the widest gap between 'min' and 'best broken' "
          "among those with zero escapes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
