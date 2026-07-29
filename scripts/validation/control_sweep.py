"""Run the negative controls across the WHOLE library, not one lucky layer.

The library scored 417/417 once before and the number was worthless - the
metric was broken in three separate ways and the controls that would have shown
it were only run on a single layer.

So: for every layer and every scene light, build deliberately broken versions
and confirm the metric rejects them. A single control that passes anywhere in
the library means the gate is too loose and the 100% is not real.

Usage:  python scripts/validation/control_sweep.py [--limit N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, ".")

from app.services.compositor import (  # noqa: E402
    LightContract, erode_alpha, relight, trim_alpha,
)
from app.services.likeness import (  # noqa: E402
    delta_e_chroma, measure, srgb_to_lab,
)

LAYERS = Path("source_material/imported_canon/character_layers")
REPAIRED = Path("characters/working/repaired_layers")

SCENES = {
    "cool-corridor": dict(a=90.0, k=(150, 225, 235), f=(30, 70, 80), s=(40, 90, 100)),
    "warm-festival": dict(a=20.0, k=(255, 190, 120), f=(70, 55, 40), s=(120, 80, 45)),
    "red-emergency": dict(a=90.0, k=(230, 90, 70), f=(60, 25, 25), s=(110, 40, 35)),
}


def light_for(scene: dict, protect: float) -> LightContract:
    return LightContract(
        key_angle_deg=scene["a"], key_color=scene["k"], fill_color=scene["f"],
        key_strength=0.22, fill_strength=0.10, rim_strength=0.10,
        spill_strength=0.14, protect_neutrals=protect,
    )


def free_tint(canon: Image.Image, scene: dict) -> Image.Image:
    """The scene light applied with NO hue protection - the failure mode the
    whole relight design exists to prevent."""
    return relight(canon, light_for(scene, 0.0), spill_color=scene["s"])


def desaturated(canon: Image.Image, _scene: dict) -> Image.Image:
    arr = np.asarray(canon).astype(float)
    lum = (arr[..., :3] * [0.2126, 0.7152, 0.0722]).sum(axis=2, keepdims=True)
    arr[..., :3] = np.repeat(lum, 3, axis=2)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def hue_swapped(canon: Image.Image, _scene: dict) -> Image.Image:
    arr = np.asarray(canon).copy()
    arr[..., [0, 1]] = arr[..., [1, 0]]
    return Image.fromarray(arr, "RGBA")


def accent_recoloured(canon: Image.Image, _scene: dict) -> Image.Image:
    """Rotate the most saturated region of THIS character to a foreign hue.

    Generic rather than NeonBlue-specific, so every character is probed on
    whatever carries its own identity colour.
    """
    arr = np.asarray(canon).copy()
    rgb = arr[..., :3].astype(int)
    opaque = arr[..., 3] == 255
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    if not opaque.any():
        return Image.fromarray(arr, "RGBA")
    cutoff = np.percentile(chroma[opaque], 97)
    target = opaque & (chroma >= max(cutoff, 30))
    if target.sum() < 50:
        return Image.fromarray(arr, "RGBA")
    arr[..., :3][target] = rgb[target][:, [2, 0, 1]]      # rotate channels
    return Image.fromarray(arr, "RGBA")


#: How far a control must actually move the art, in mean chroma-plane dE over
#: the opaque figure, before its verdict means anything. Measured directly on
#: pixels - deliberately NOT using the metric under test, or the check would be
#: circular. Set at the metric's own aggregate tolerance.
MIN_APPLICABLE_SHIFT = 3.0


def applied_chroma_shift(canon: Image.Image, broken: Image.Image) -> float:
    """Mean a*b* distance the control actually applied, over the opaque figure.

    Independent of the metric being tested. If this is near zero the control is
    a no-op for this character and proves nothing either way.
    """
    a = np.asarray(canon)
    b = np.asarray(broken)
    opaque = a[..., 3] == 255
    if not opaque.any():
        return 0.0
    lab_a = srgb_to_lab(a[..., :3][opaque].astype(float))
    lab_b = srgb_to_lab(b[..., :3][opaque].astype(float))
    return float(delta_e_chroma(lab_a, lab_b).mean())


CONTROLS = {
    "free-tint": free_tint,
    "desaturated": desaturated,
    "hue-swapped": hue_swapped,
    "accent-recoloured": accent_recoloured,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="only probe the first N layers (0 = all)")
    args = ap.parse_args()

    layers = sorted(LAYERS.glob("*/*.png"))
    if args.limit:
        layers = layers[:args.limit]

    escapes: list[tuple[str, str, str, float, float]] = []
    inapplicable: list[tuple[str, str, float]] = []
    checked = 0
    margins: list[float] = []

    for path in layers:
        rel = path.relative_to(LAYERS).as_posix()
        use = REPAIRED / rel if (REPAIRED / rel).is_file() else path
        canon = erode_alpha(trim_alpha(Image.open(use).convert("RGBA")), 1)

        for scene_name, scene in SCENES.items():
            for control_name, build in CONTROLS.items():
                broken = build(canon, scene)
                applied = applied_chroma_shift(canon, broken)
                if applied < MIN_APPLICABLE_SHIFT:
                    # The control did not actually damage this character, so it
                    # tests nothing. Desaturating an already-grey character is
                    # the obvious case: Ash averages chroma 2.3, so "fully
                    # desaturated" moves him by less than the tolerance and the
                    # metric is RIGHT to pass him. Counting that as an escape
                    # would be measuring the control, not the metric.
                    inapplicable.append((rel, control_name, applied))
                    continue

                result = measure(broken, canon, "X", layer_name=rel)
                checked += 1
                margins.append(result.score)
                if result.passed:
                    escapes.append(
                        (rel, scene_name, control_name, result.score, applied)
                    )

    print(f"layers               : {len(layers)}")
    print(f"applicable measures  : {checked}  "
          f"(of {len(layers) * len(SCENES) * len(CONTROLS)} attempted)")
    print(f"skipped, no real damage: {len(inapplicable)}  "
          f"(control moved the art by < dE {MIN_APPLICABLE_SHIFT})")
    print(f"controls REJECTED    : {checked - len(escapes)} / {checked}")
    print(f"controls ESCAPED     : {len(escapes)}")
    if margins:
        arr = np.array(margins)
        print(f"broken-input scores  : max {arr.max():.1f}  "
              f"median {np.median(arr):.1f}  (gate is 95.0)")

    if inapplicable:
        by_control: dict[str, int] = {}
        for _, control, _ in inapplicable:
            by_control[control] = by_control.get(control, 0) + 1
        print("\nSkipped as inapplicable (character has too little colour for "
              "this control to damage):")
        for control, count in sorted(by_control.items(), key=lambda kv: -kv[1]):
            print(f"  {count:5d}  {control}")

    if escapes:
        print("\nESCAPES - the metric accepted art that WAS materially damaged:")
        for rel, scene, control, score, applied in escapes[:40]:
            print(f"  {score:5.1f}  applied dE {applied:5.1f}  "
                  f"{control:18s} {scene:15s} {rel}")
        if len(escapes) > 40:
            print(f"  ... and {len(escapes) - 40} more")
        print("\nVERDICT: the gate is too loose. The library pass rate is not real.")
        return 1

    print("\nVERDICT: every control that actually damaged the art was rejected, "
          "across every layer and every scene.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
