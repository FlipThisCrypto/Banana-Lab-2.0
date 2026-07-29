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


def delta_e_chroma(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distance in the a*b* plane only, ignoring lightness.

    This, not full dE, is the right measure for character identity under scene
    light. Identity is carried by HUE and CHROMA - Scarline's scarlet is scarlet
    in daylight and in a red corridor. LIGHTNESS is what a light is supposed to
    change, and penalising it makes a correctly-lit character look like a
    likeness failure.

    Measured: full dE scored the library at 66% across three scene lights while
    the cool-lit scene alone scored 96%. The gap was almost entirely lightness
    response to the warm and red keys, not identity drift.
    """
    a = np.asarray(a)
    b = np.asarray(b)
    return np.sqrt(((a[..., 1:] - b[..., 1:]) ** 2).sum(axis=-1))


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
    image_path: Path | Image.Image, *, max_swatches: int = 10, min_share: float = 0.012
) -> list[Swatch]:
    """The canon palette of an approved layer, measured rather than declared.

    Cel art is made of flat fills, so quantising and counting recovers the real
    palette. Declared hex values in a bible drift from the art; the art does not.
    """
    if isinstance(image_path, Image.Image):
        arr = np.asarray(image_path.convert("RGBA"))
    else:
        with Image.open(image_path) as image:
            arr = np.asarray(image.convert("RGBA"))
    rgb, alpha = arr[..., :3], arr[..., 3]
    solid = alpha == 255
    if solid.sum() == 0:
        return []

    pixels = rgb[solid].astype(float)

    # Cluster in Lab, not in RGB bins. Binning RGB finely fragments a colour
    # that has any gradient or anti-aliasing across dozens of bins, so it never
    # reaches the share threshold and drops out of the palette entirely.
    #
    # Measured on neonblue_16_worried: the cyan crown is 3.98% of the character
    # but spread over 1087 RGB bins, largest 0.12%. It was not a tracked swatch,
    # so recolouring the whole crown orange scored 100 and passed. Eight of the
    # ten tracked swatches had zero chroma - the metric was barely measuring
    # colour at all.
    lab = srgb_to_lab(pixels)
    keys = np.stack([
        np.round(lab[:, 0] / 14.0),
        np.round(lab[:, 1] / 11.0),
        np.round(lab[:, 2] / 11.0),
    ], axis=1)
    values, inverse, counts = np.unique(keys, axis=0, return_inverse=True,
                                        return_counts=True)
    order = np.argsort(-counts)

    swatches: list[Swatch] = []
    for index in order:
        share = float(counts[index] / len(pixels))
        if share < min_share or len(swatches) >= max_swatches:
            break
        # Represent the cluster by the mean of its actual pixels, so the swatch
        # is a colour that exists in the art rather than a bin centre.
        member = pixels[inverse == index].mean(axis=0)
        rgb_value = tuple(int(v) for v in member.round())
        swatches.append(
            Swatch(
                hex="#%02X%02X%02X" % rgb_value,
                rgb=rgb_value,
                share=round(share, 4),
            )
        )
    return swatches


def _palette_from_pixels(pixels: np.ndarray, count: int = 10) -> list[tuple[int, int, int]]:
    """Dominant colours of a pixel array, most-common first."""
    quantised = (pixels.astype(int) // 6) * 6
    values, counts = np.unique(quantised, axis=0, return_counts=True)
    order = np.argsort(-counts)[:count]
    out = [tuple(int(v) for v in values[i]) for i in order]
    while len(out) < count and out:
        out.append(out[-1])
    return out


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
    #: Mean L* change between the approved layer and the render. Expected to be
    #: non-zero: this is the light doing its job.
    lightness_shift: float = 0.0
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
            "lightness_shift": round(self.lightness_shift, 1),
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


#: Chroma-plane dE at which a canon swatch is considered preserved.
SWATCH_TOLERANCE = 12.0

#: How far mean lightness may move under scene light before identity is at risk.
#: Light is SUPPOSED to change lightness, so this is a wide band, not a tight
#: one - it exists to catch a character rendered near-black or blown out, not to
#: penalise correct lighting response.
MAX_LIGHTNESS_SHIFT = 34.0

#: Minimum rendered height, in pixels, at which a chibi character's small
#: identifying features (eye rings, under-eye bags) can still be read at print
#: size. Derived from the P16-02 finding that a 245 px Moodz lost a third of the
#: contrast on his eye rings.
MIN_LEGIBLE_HEIGHT = 320


def measure(
    rendered: Image.Image,
    canon_layer: Path | Image.Image,
    character_id: str,
    *,
    contamination_px: int = 0,
    layer_name: str = "",
) -> LikenessResult:
    """Compare a rendered character crop against its approved layer.

    `rendered` should be the character region only, RGBA with the character's
    alpha, so background pixels do not pollute the palette comparison.
    """
    canon = extract_palette(canon_layer)
    result = LikenessResult(
        character_id=character_id,
        layer=layer_name or (Path(canon_layer).name
                             if isinstance(canon_layer, (str, Path)) else "<image>"),
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

    # Where the render is pixel-aligned with the approved layer - which it is
    # for every composite this pipeline produces, since the render IS the
    # transformed layer - compare the pixels that WERE each canon swatch with
    # what they BECAME. That correspondence is exact.
    #
    # The earlier "nearest rendered colour to each canon swatch" approach was
    # far too permissive and made the metric worthless: across tens of thousands
    # of pixels something always lands near any given swatch, so a hue-swapped
    # character, a fully desaturated one, and the free-tint failure mode this
    # module exists to catch ALL scored above 98 and passed. Negative controls
    # caught it; see docs/audits/LIKENESS_TUNING_REPORT.md.
    if isinstance(canon_layer, Image.Image):
        canon_arr_full = np.asarray(canon_layer.convert("RGBA"))
    else:
        with Image.open(canon_layer) as image:
            canon_arr_full = np.asarray(image.convert("RGBA"))

    aligned = canon_arr_full.shape[:2] == arr.shape[:2]

    weighted = 0.0
    total_share = 0.0

    if aligned:
        canon_rgb = canon_arr_full[..., :3].astype(float)
        canon_pixels = canon_rgb[solid]
        canon_pixel_lab = srgb_to_lab(canon_pixels)

        for swatch in canon:
            # The pixels that were this swatch in the approved art. Matched in
            # Lab within the cluster radius the palette was built with, so a
            # swatch with a gradient is captured whole.
            belongs = delta_e(canon_pixel_lab, swatch.lab) < 14.0
            if belongs.sum() < 20:
                continue
            d = float(delta_e_chroma(rendered_lab[belongs],
                                     canon_pixel_lab[belongs]).mean())
            became = rendered_pixels[belongs].mean(axis=0)
            result.swatches.append(
                SwatchResult(
                    canon_hex=swatch.hex,
                    rendered_hex="#%02X%02X%02X" % tuple(int(v) for v in became.round()),
                    share=swatch.share,
                    delta_e=d,
                    passed=d <= SWATCH_TOLERANCE,
                )
            )
            weighted += d * swatch.share
            total_share += swatch.share
    else:
        # Not aligned - fall back to comparing the two palettes as area-ordered
        # distributions. Weaker, but it still cannot be satisfied by a stray
        # pixel, because it matches swatches of comparable area.
        result.notes.append(
            "UNMEASURABLE: render is not pixel-aligned with the approved layer. "
            "Falling back to an area-matched palette comparison, which cannot "
            "reliably detect identity drift. Pass the same prepared image as "
            "canon_layer so the comparison is exact."
        )
        rendered_palette = _palette_from_pixels(rendered_pixels)
        for swatch, rendered_swatch in zip(canon, rendered_palette):
            d = float(delta_e_chroma(
                srgb_to_lab(np.array(rendered_swatch, dtype=float)), swatch.lab
            ))
            result.swatches.append(
                SwatchResult(
                    canon_hex=swatch.hex,
                    rendered_hex="#%02X%02X%02X" % tuple(int(v) for v in rendered_swatch),
                    share=swatch.share,
                    delta_e=d,
                    passed=d <= SWATCH_TOLERANCE,
                )
            )
            weighted += d * swatch.share
            total_share += swatch.share

    mean_de = weighted / total_share if total_share else 0.0
    worst_de = max((s.delta_e for s in result.swatches), default=0.0)

    # Area weighting alone buries the swatches that carry identity. NeonBlue is
    # mostly neutral fur and black clothing, so his cyan crown - a REQUIRED
    # identifying feature - is a small share and can be destroyed without moving
    # an area-weighted mean. Measured: a hue-swapped and a fully desaturated
    # NeonBlue both scored above 97 and passed on the mean alone.
    #
    # So the score is driven by the WORST swatch as much as the mean, and any
    # single swatch over tolerance fails the component outright.
    result.palette_delta_e = max(mean_de, worst_de * 0.5)
    blended = 0.5 * mean_de + 0.5 * worst_de
    result.palette_score = max(0.0, 100.0 - (blended / SWATCH_TOLERANCE) * 100.0 / 3.0)

    if any(not s.passed for s in result.swatches):
        # A canon colour has been changed, not merely lit differently.
        result.palette_score = min(result.palette_score, 80.0)

    # Both sides must be area-weighted or the comparison is meaningless: the
    # render mean is over every pixel, so the canon mean must be weighted by
    # each swatch's share rather than treating ten swatches as equals.
    canon_arr = np.array([s.rgb for s in canon], dtype=float)
    shares = np.array([s.share for s in canon], dtype=float)
    shares = shares / shares.sum() if shares.sum() else shares
    canon_l = float((srgb_to_lab(canon_arr)[..., 0] * shares).sum())
    render_l = float(rendered_lab[..., 0].mean())
    result.lightness_shift = render_l - canon_l
    if abs(result.lightness_shift) > MAX_LIGHTNESS_SHIFT:
        over = abs(result.lightness_shift) - MAX_LIGHTNESS_SHIFT
        result.palette_score = max(0.0, result.palette_score - over * 2.0)
        result.notes.append(
            f"mean lightness moved {result.lightness_shift:+.0f} L*, beyond the "
            f"{MAX_LIGHTNESS_SHIFT:.0f} band; the character is over- or under-lit"
        )

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
