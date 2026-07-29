"""Measure whether a rendered character still looks like the approved character.

"Consistent likeness" has to be a number or it is an opinion. This module turns
it into one.

The pipeline does not GENERATE character identity - it composites approved art.
So in principle likeness is perfect by construction. In practice three things
erode it between the approved layer and the finished panel:

  1. Contamination in the layer itself (card-background bleed inside the
     silhouette).
  2. Relight drifting the palette, which hits the mid-greys hardest - and the
     mid-greys are what carry under-eye bags, eye rings and stitched chest
     panels, i.e. required identifying features.
  3. Scale: a feature can survive the maths and still be too small to read at
     print size.

Each is measured separately, because each has a different fix.

Colour distance is CIE76 dE in Lab. It is not the best perceptual metric, but it
is stable, cheap and interpretable: dE under ~5 is invisible, ~10 is noticeable
side by side, over ~25 is a different colour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

# --- colour ---------------------------------------------------------------

_SRGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_WHITE = np.array([0.95047, 1.00000, 1.08883])


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """rgb in 0-255, any leading shape. Returns Lab with the same leading shape."""
    arr = np.asarray(rgb, dtype=np.float64) / 255.0
    linear = np.where(arr <= 0.04045, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
    xyz = linear @ _SRGB_TO_XYZ.T / _WHITE

    eps = 216 / 24389
    kappa = 24389 / 27
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16) / 116)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], axis=-1)


def delta_e(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """CIE76 distance between two Lab arrays."""
    return np.sqrt(((np.asarray(a) - np.asarray(b)) ** 2).sum(axis=-1))


# --- palette --------------------------------------------------------------

@dataclass
class Swatch:
    hex: str
    rgb: tuple[int, int, int]
    share: float
    role: str = ""

    @property
    def lab(self) -> np.ndarray:
        return srgb_to_lab(np.array(self.rgb, dtype=float))


def extract_palette(
    image_path: Path, *, max_swatches: int = 10, min_share: float = 0.012
) -> list[Swatch]:
    """The canon palette of an approved layer, measured rather than declared.

    Cel art is made of flat fills, so quantising and counting recovers the real
    palette. Declared hex values in a bible drift from the art; the art does not.
    """
    with Image.open(image_path) as image:
        arr = np.asarray(image.convert("RGBA"))
    rgb, alpha = arr[..., :3], arr[..., 3]
    solid = alpha == 255
    if solid.sum() == 0:
        return []

    pixels = rgb[solid]
    quantised = (pixels // 6) * 6
    values, counts = np.unique(quantised, axis=0, return_counts=True)
    order = np.argsort(-counts)

    swatches: list[Swatch] = []
    for index in order:
        share = float(counts[index] / len(pixels))
        if share < min_share or len(swatches) >= max_swatches:
            break
        value = values[index]
        swatches.append(
            Swatch(
                hex="#%02X%02X%02X" % tuple(int(v) for v in value),
                rgb=tuple(int(v) for v in value),
                share=round(share, 4),
            )
        )
    return swatches


# --- measurement ----------------------------------------------------------

@dataclass
class SwatchResult:
    canon_hex: str
    rendered_hex: str
    share: float
    delta_e: float
    passed: bool


@dataclass
class LikenessResult:
    character_id: str
    layer: str
    #: Worst dE across the character's canon swatches, weighted by area.
    palette_delta_e: float
    palette_score: float
    swatches: list[SwatchResult] = field(default_factory=list)
    contamination_px: int = 0
    contamination_score: float = 100.0
    rendered_height_px: int = 0
    feature_legibility_score: float = 100.0
    notes: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Overall likeness, 0-100."""
        return round(
            0.55 * self.palette_score
            + 0.25 * self.contamination_score
            + 0.20 * self.feature_legibility_score,
            1,
        )

    @property
    def passed(self) -> bool:
        """A pass needs the overall score AND every component to be sound.

        A high average must never hide a failed component - same principle as
        the panel approval standard, where a 99 with an extra hand still fails.
        """
        return (
            self.score >= 95.0
            and self.palette_score >= 92.0
            and self.contamination_score >= 99.0
            and self.feature_legibility_score >= 85.0
        )

    def to_dict(self) -> dict:
        return {
            "character_id": self.character_id,
            "layer": self.layer,
            "score": self.score,
            "passed": self.passed,
            "palette_score": round(self.palette_score, 1),
            "palette_delta_e": round(self.palette_delta_e, 1),
            "contamination_score": round(self.contamination_score, 1),
            "contamination_px": self.contamination_px,
            "feature_legibility_score": round(self.feature_legibility_score, 1),
            "rendered_height_px": self.rendered_height_px,
            "swatches": [
                {
                    "canon": s.canon_hex, "rendered": s.rendered_hex,
                    "share": s.share, "delta_e": round(s.delta_e, 1), "passed": s.passed,
                }
                for s in self.swatches
            ],
            "notes": self.notes,
        }


#: dE at which a canon swatch is considered preserved.
SWATCH_TOLERANCE = 12.0

#: Minimum rendered height, in pixels, at which a chibi character's small
#: identifying features (eye rings, under-eye bags) can still be read at print
#: size. Derived from the P16-02 finding that a 245 px Moodz lost a third of the
#: contrast on his eye rings.
MIN_LEGIBLE_HEIGHT = 320


def measure(
    rendered: Image.Image,
    canon_layer: Path,
    character_id: str,
    *,
    contamination_px: int = 0,
) -> LikenessResult:
    """Compare a rendered character crop against its approved layer.

    `rendered` should be the character region only, RGBA with the character's
    alpha, so background pixels do not pollute the palette comparison.
    """
    canon = extract_palette(canon_layer)
    result = LikenessResult(
        character_id=character_id,
        layer=Path(canon_layer).name,
        palette_delta_e=0.0,
        palette_score=100.0,
        rendered_height_px=rendered.height,
        contamination_px=contamination_px,
    )
    if not canon:
        result.notes.append("approved layer has no opaque pixels; cannot measure")
        result.palette_score = 0.0
        return result

    arr = np.asarray(rendered.convert("RGBA"))
    solid = arr[..., 3] > 200
    if solid.sum() < 50:
        result.notes.append("rendered crop has too few opaque pixels to measure")
        result.palette_score = 0.0
        return result

    rendered_pixels = arr[..., :3][solid].astype(float)
    rendered_lab = srgb_to_lab(rendered_pixels)

    weighted = 0.0
    total_share = 0.0
    worst = 0.0

    for swatch in canon:
        # Nearest rendered colour to this canon swatch. If the swatch survived
        # the pipeline at all, something in the render sits close to it.
        distances = delta_e(rendered_lab, swatch.lab)
        best = int(np.argmin(distances))
        nearest = rendered_pixels[best]
        d = float(distances[best])

        result.swatches.append(
            SwatchResult(
                canon_hex=swatch.hex,
                rendered_hex="#%02X%02X%02X" % tuple(int(v) for v in nearest.round()),
                share=swatch.share,
                delta_e=d,
                passed=d <= SWATCH_TOLERANCE,
            )
        )
        weighted += d * swatch.share
        total_share += swatch.share
        worst = max(worst, d)

    mean_de = weighted / total_share if total_share else 0.0
    result.palette_delta_e = mean_de
    # 0 dE -> 100, SWATCH_TOLERANCE dE -> 80, 3x tolerance -> 0.
    result.palette_score = max(0.0, 100.0 - (mean_de / SWATCH_TOLERANCE) * 20.0 * (100 / 60))

    failed = [s for s in result.swatches if not s.passed]
    if failed:
        result.notes.append(
            f"{len(failed)} of {len(result.swatches)} canon swatches exceed dE "
            f"{SWATCH_TOLERANCE}: " + ", ".join(f"{s.canon_hex}({s.delta_e:.0f})" for s in failed[:4])
        )

    # Contamination: any card bleed inside the silhouette is a hard identity fault.
    if contamination_px > 0:
        share = contamination_px / max(1, int(solid.sum()))
        result.contamination_score = max(0.0, 100.0 - share * 4000.0)
        result.notes.append(
            f"{contamination_px} contaminated px inside the silhouette "
            f"({share:.2%} of the character)"
        )

    # Legibility: small features stop reading below a height threshold.
    if rendered.height < MIN_LEGIBLE_HEIGHT:
        ratio = rendered.height / MIN_LEGIBLE_HEIGHT
        result.feature_legibility_score = max(0.0, 100.0 * ratio)
        result.notes.append(
            f"rendered at {rendered.height}px tall; below {MIN_LEGIBLE_HEIGHT}px "
            f"small identifying features are not proven legible at print size"
        )

    return result
