"""Adversarial controls for the scene-integration measure, across the library.

The likeness metric was found broken seven times, and every single time the
pass rate looked fine on its own. So this measure does not get adopted on the
strength of a few hand-picked examples either.

For every layer and every scene light, build things that are NOT correctly lit
and confirm the measure scores them below an honest relight of the same layer:

  flat-decal        uniform colour multiply matched to the honest relight's mean
                    colour. Tinted, never lit. This is the adversary that killed
                    the measure's own first draft: raw correlation of the dL*
                    fields cannot tell it from a relight, because relight and a
                    multiply are BOTH multiplicative and both produce a dL*
                    field proportional to the figure's albedo (measured r=0.84).
  cut-out           the untouched layer. Ignores the scene entirely.
  wrong-direction   correctly lit, but from the opposite side to the contract.
  wrong-scene       correctly lit, by a different scene's light.

Usage:  python scripts/validation/integration_control_sweep.py [--limit N]
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
from app.services.integration import measure_integration  # noqa: E402

LAYERS = Path("source_material/imported_canon/character_layers")
REPAIRED = Path("characters/working/repaired_layers")
PLATE = Path("workflows/comfyui/experiments/exp002-p16-02-plate/"
             "exp002_seed760201.png")

#: Only the cool corridor. The one real calibrated plate available is cool-lit,
#: and the measure correctly refuses to score a contract that opposes the
#: plate's own illuminant - so warm and red keys against this plate are
#: off-diagonal cells that return 0.0 by design, and would prove nothing here.
#: That is a COVERAGE LIMIT of this sweep, not a property of the measure.
SCENE = dict(a=90.0, k=(150, 225, 235), f=(30, 70, 80), s=(40, 90, 100))
OTHER = dict(a=20.0, k=(255, 190, 120), f=(70, 55, 40), s=(120, 80, 45))

PROTECTS = (0.0, 0.5, 0.85)

#: How far below the honest relight a broken input must score to count as
#: rejected. Not a tolerance - a separation requirement.
#:
#: It can only be demanded when the honest relight has that much room. Some
#: layer/contract pairs genuinely barely integrate: moodz_30_backview is 56%
#: black and 21% saturated blue, so the cool contract can only move it 0.98 dE
#: along the plate's illuminant axis - under the measure's own 3.0 dE visibility
#: floor - and the honest relight scores 12.7 at protect 0.85. Its four broken
#: variants all scored 0.0, correctly ranked below, but there is no room for a
#: 20-point gap. Where that happens the requirement is strict ordering instead,
#: and the pair is reported separately as barely-integrating - which is a
#: finding about the panel, not a failure of the measure.
MIN_SEPARATION = 20.0


def light(scene, protect, angle=None):
    return LightContract(
        key_angle_deg=scene["a"] if angle is None else angle,
        key_color=scene["k"], fill_color=scene["f"],
        key_strength=0.22, fill_strength=0.10, rim_strength=0.10,
        spill_strength=0.14, protect_neutrals=protect,
    )


def flat_decal(canon: Image.Image, honest: Image.Image) -> Image.Image:
    """Same mean colour as the honest relight, applied as a uniform multiply."""
    a = np.asarray(canon).astype(float)
    h = np.asarray(honest).astype(float)
    opaque = a[..., 3] == 255
    if not opaque.any():
        return canon
    ratio = ((h[..., :3][opaque].mean(axis=0) + 1e-6)
             / (a[..., :3][opaque].mean(axis=0) + 1e-6))
    out = a.copy()
    out[..., :3] = np.clip(a[..., :3] * ratio, 0, 255)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    plate = Image.open(PLATE).convert("RGBA")
    layers = sorted(LAYERS.glob("*/*.png"))
    if args.limit:
        by_character: dict[str, list[Path]] = defaultdict(list)
        for path in layers:
            by_character[path.parent.name].append(path)
        per = max(1, args.limit // max(1, len(by_character)))
        layers = [p for paths in by_character.values() for p in paths[::max(1, len(paths) // per)][:per]]

    escapes: list[tuple[str, str, float, float, float]] = []
    barely: list[tuple[str, float, float]] = []
    checked = 0
    honest_scores: list[float] = []
    # One reference relight per (layer, contract) instead of one per
    # measurement. The key excludes protect_neutrals, because the reference IS
    # the free-tint version. Cuts 15 reference relights per layer to 1.
    reference_cache: dict = {}

    for path in layers:
        rel = path.relative_to(LAYERS).as_posix()
        use = REPAIRED / rel if (REPAIRED / rel).is_file() else path
        canon = erode_alpha(trim_alpha(Image.open(use).convert("RGBA")), 1)
        box = (300, 300, 300 + canon.width, 300 + canon.height)

        for protect in PROTECTS:
            contract = light(SCENE, protect)
            honest = relight(canon, contract, spill_color=SCENE["s"])
            good = measure_integration(honest, canon, plate, box, contract,
                                       spill_color=SCENE["s"],
                                       reference_cache=reference_cache).score
            honest_scores.append(good)
            if good < MIN_SEPARATION:
                barely.append((rel, protect, good))

            broken = {
                "flat-decal": flat_decal(canon, honest),
                "cut-out": canon,
                "wrong-direction": relight(canon, light(SCENE, protect, angle=270),
                                           spill_color=SCENE["s"]),
                "wrong-scene": relight(canon, light(OTHER, protect),
                                       spill_color=OTHER["s"]),
            }
            for name, image in broken.items():
                bad = measure_integration(image, canon, plate, box, contract,
                                          spill_color=SCENE["s"],
                                          reference_cache=reference_cache).score
                checked += 1
                rejected = (bad <= good - MIN_SEPARATION if good >= MIN_SEPARATION
                            else bad < good)
                if not rejected:
                    escapes.append((rel, name, protect, good, bad))

    print(f"layers            : {len(layers)}")
    print(f"control measures  : {checked}")
    print(f"controls REJECTED : {checked - len(escapes)} / {checked}")
    print(f"controls ESCAPED  : {len(escapes)}")
    if honest_scores:
        arr = np.array(honest_scores)
        print(f"honest relight    : min {arr.min():.1f}  median "
              f"{np.median(arr):.1f}  max {arr.max():.1f}")

    if barely:
        print(f"\nBarely-integrating pairs ({len(barely)}): the honest relight "
              f"itself scored under {MIN_SEPARATION:.0f}, so its broken "
              f"variants only had to rank below it rather than clear a gap.")
        print("This is a finding about those panels, not about the measure - "
              "the light genuinely does little to that artwork.")
        for rel, protect, good in barely[:10]:
            print(f"  protect {protect:4.2f}  honest {good:5.1f}   {rel}")
        if len(barely) > 10:
            print(f"  ... and {len(barely) - 10} more")

    if escapes:
        print("\nESCAPES - not scored below an honest relight of the same layer:")
        for rel, name, protect, good, bad in escapes[:40]:
            print(f"  {name:16s} protect {protect:4.2f}  honest {good:5.1f}  "
                  f"broken {bad:5.1f}   {rel}")
        if len(escapes) > 40:
            print(f"  ... and {len(escapes) - 40} more")
        return 1

    print(f"\nVERDICT: every incorrectly-lit control scored below an honest "
          f"relight of the same layer - by at least {MIN_SEPARATION:.0f} points "
          f"wherever the honest relight had that much room, and strictly below "
          f"it otherwise. {len(barely)} of {len(honest_scores)} pairs were in "
          f"the latter case.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
