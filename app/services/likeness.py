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


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """Inverse of srgb_to_lab. Returns 0-255 floats, unclamped."""
    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[..., 0] + 16.0) / 116.0
    fx = fy + lab[..., 1] / 500.0
    fz = fy - lab[..., 2] / 200.0

    eps = 216 / 24389
    kappa = 24389 / 27
    def finv(f):
        cubed = f ** 3
        return np.where(cubed > eps, cubed, (116.0 * f - 16.0) / kappa)

    xyz = np.stack([finv(fx), finv(fy), finv(fz)], axis=-1) * _WHITE
    linear = xyz @ np.linalg.inv(_SRGB_TO_XYZ).T
    # Signed gamma, deliberately NOT clipped. Out-of-gamut Lab must come back
    # as an out-of-range number, or lab_to_srgb_in_gamut() cannot detect the
    # condition it exists to correct - clipping here made every colour look
    # in-gamut and the mapping became a no-op.
    mag = np.abs(linear)
    srgb = np.sign(linear) * np.where(mag <= 0.0031308, mag * 12.92,
                                      1.055 * np.power(mag, 1 / 2.4) - 0.055)
    return srgb * 255.0


def lab_to_srgb_in_gamut(lab: np.ndarray) -> np.ndarray:
    """Lab -> sRGB, mapped into gamut by reducing chroma, never by clipping.

    Darkening a saturated colour in Lab routinely leaves sRGB. Clipping the
    channels there bends the hue: cyan (52,229,232) taken to 60% lightness
    clips red to 0 and swings a* from -40.9 to -28.9. Scaling a*/b* toward
    the neutral axis instead holds the hue angle exactly and gives up only
    the chroma the display genuinely cannot show.

    Returns 0-255 floats guaranteed inside the cube.
    """
    lab = np.asarray(lab, dtype=np.float64)
    out = lab_to_srgb(lab)

    # Most pixels already fit. Searching all of them costs 24 full colour
    # conversions per image; searching only the offenders costs 24 conversions
    # of a small subset. On the layer library that is the difference between
    # ~14s and well under a second per megapixel.
    offenders = (out.min(axis=-1) < 0.0) | (out.max(axis=-1) > 255.0)
    if not offenders.any():
        return np.clip(out, 0.0, 255.0)

    work = lab[offenders]                  # (n, 3)

    # Flat comic art repeats colours: one layer gave 3397 distinct offending
    # Lab values across 704258 offending pixels. Solve each distinct value
    # once. Quantising to 0.1 only decides which scale factor to use - the
    # factor is then applied to the full-precision Lab, so the output keeps
    # its precision.
    _, index, inverse = np.unique(np.round(work, 1), axis=0,
                                  return_index=True, return_inverse=True)
    uniq = work[index]
    lo = np.zeros(uniq.shape[0])           # always in gamut: the neutral axis
    hi = np.ones(uniq.shape[0])
    for _ in range(24):
        mid = (lo + hi) / 2.0
        trial = uniq * np.stack([np.ones_like(mid), mid, mid], axis=-1)
        rgb = lab_to_srgb(trial)
        # Strict: a tolerance here is not slack, it is hue error. Accepting
        # R = -0.4 and then clipping to 0 shifts the hue by exactly as much as
        # clipping would have, which defeats the mapping.
        ok = (rgb.min(axis=-1) >= 0.0) & (rgb.max(axis=-1) <= 255.0)
        lo = np.where(ok, mid, lo)
        hi = np.where(ok, hi, mid)

    scale = lo[inverse]
    fixed = lab_to_srgb(work * np.stack([np.ones_like(scale), scale, scale],
                                        axis=-1))
    out = out.copy()
    out[offenders] = fixed
    return np.clip(out, 0.0, 255.0)


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
    #: The two rules behind palette_score, reported separately so a failure
    #: says which one bit. See MEAN_DRIFT_TOLERANCE.
    palette_mean_de: float = 0.0
    palette_worst_de: float = 0.0
    #: Mean chroma dE over every opaque pixel. Only meaningful on the aligned
    #: path; stays 0.0 when the render cannot be compared pixel for pixel.
    pixel_drift_de: float = 0.0
    #: Mean L* change between the approved layer and the render. Expected to be
    #: non-zero: this is the light doing its job.
    lightness_shift: float = 0.0
    swatches: list[SwatchResult] = field(default_factory=list)
    contamination_px: int = 0
    contamination_score: float = 100.0
    #: False when the caller could not determine the layer's card-bleed status.
    #: An unmeasured component must never read as a passed one - see `passed`.
    contamination_measured: bool = True
    rendered_height_px: int = 0
    feature_legibility_score: float = 100.0
    #: True when the render was below the legibility floor but was staged as
    #: non-identity-bearing, so the floor was waived. Recorded, never silent.
    legibility_exempt: bool = False
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
            # Equivalent to: worst swatch within SWATCH_TOLERANCE AND mean
            # within MEAN_DRIFT_TOLERANCE. See the palette_score derivation.
            and self.palette_score >= 92.0
            # An UNMEASURED component cannot pass. The bleed detector returns
            # UNDETERMINED for layers it cannot align against their source
            # sheet, and 49 of 139 library layers were in that state - scored
            # contamination_px=0, i.e. silently assumed clean, and passing. A
            # machine gate may only reject; "not known to be dirty" is not
            # "known to be clean". Same rule as the unaligned-render path.
            and self.contamination_measured
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
            "palette_mean_de": round(self.palette_mean_de, 2),
            "palette_worst_de": round(self.palette_worst_de, 2),
            "pixel_drift_de": round(self.pixel_drift_de, 2),
            "palette_delta_e": round(self.palette_delta_e, 1),
            "lightness_shift": round(self.lightness_shift, 1),
            "contamination_score": round(self.contamination_score, 1),
            "contamination_px": self.contamination_px,
            "contamination_measured": self.contamination_measured,
            "feature_legibility_score": round(self.feature_legibility_score, 1),
            "rendered_height_px": self.rendered_height_px,
            "legibility_exempt": self.legibility_exempt,
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

#: Area-weighted mean chroma dE across all canon swatches.
#:
#: SWATCH_TOLERANCE alone cannot catch a free tint: tinting the whole character
#: moves every swatch a little, and "a little" is under 12 for each one taken
#: separately. This rule catches the aggregate. The two are complementary, and
#: neither does the other's job - measured:
#:
#:                            worst dE   mean dE
#:   legitimate relights       1.6-9.2   0.7-1.5   (9 cases, 3 chars x 3 scenes)
#:   free tint, cool key          10.3       5.9
#:   free tint, red key           17.6       9.7
#:   fully desaturated            40.3       2.7   <- only worst catches this
#:   crown recoloured orange      86.9       2.4   <- only worst catches this
#:
#: 3.0 sits at 2x the worst legitimate mean and half the mildest free tint.
MEAN_DRIFT_TOLERANCE = 3.0

#: Mean chroma dE over EVERY opaque pixel, tracked by the palette or not.
#:
#: The swatch rules are blind to colours the palette never captured, and small
#: fragmented identity colours are exactly the ones that fall through. This rule
#: measures the whole figure, so it has no coverage hole. Measured over 8
#: characters x 3 scenes:
#:
#:   legitimate relights   max 1.64   (mean 1.13, p95 1.54)
#:   damaging controls     min 3.02   (median 6.37)
#:
#: 2.5 gives 52% headroom over the worst legitimate case while catching every
#: control that materially damaged the art. It CANNOT catch damage that moves
#: the whole-figure mean by less than 2.5 dE - that is a real and stated limit.
PIXEL_DRIFT_TOLERANCE = 2.5

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
    contamination_px: int | None = 0,
    layer_name: str = "",
    identity_critical: bool = True,
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
        contamination_px=contamination_px or 0,
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

        # Every opaque pixel, whether or not the palette tracks its colour.
        #
        # The swatch rules can only see colours that made it into the palette,
        # and the palette has a coverage hole: a cluster under min_share is not
        # tracked at all. neonblue_21_running is the proof - 11201 high-chroma
        # pixels, 3.60% of the figure, and 100% of them more than dE 14 from any
        # tracked swatch, because his cyan crown fragments into clusters that
        # each fall below the threshold. Recolouring it scored exactly 100.0.
        # The metric saw nothing, because there was nothing there to see.
        #
        # This rule cannot have that hole. It is the safety net under the
        # palette, not a replacement for it - the palette is what makes a
        # failure explainable ("your cyan moved"), this is what makes it certain.
        result.pixel_drift_de = float(
            delta_e_chroma(rendered_lab, canon_pixel_lab).mean()
        )

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
    result.palette_mean_de = mean_de
    result.palette_worst_de = worst_de

    # Score each rule against its OWN tolerance and report the worse. This used
    # to blend the two dE values and divide by SWATCH_TOLERANCE alone, which
    # made the score gate disagree with the per-swatch rule: a layer whose every
    # swatch was inside tolerance still failed, and the note said "palette
    # drift" when nothing had drifted past tolerance. Clever under the red key
    # was the case that exposed it - worst 9.2, mean 1.4, every swatch ok,
    # scored 85.2 and failed.
    #
    # usage is 1.0 exactly at either tolerance, so palette_score >= 92 is now
    # equivalent to "mean within MEAN_DRIFT_TOLERANCE and worst within
    # SWATCH_TOLERANCE" - the gate and the rule cannot drift apart again.
    usage = max(
        mean_de / MEAN_DRIFT_TOLERANCE,
        worst_de / SWATCH_TOLERANCE,
        result.pixel_drift_de / PIXEL_DRIFT_TOLERANCE,
    )
    result.palette_score = max(0.0, 100.0 - 8.0 * usage)

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
    elif result.pixel_drift_de > PIXEL_DRIFT_TOLERANCE:
        result.notes.append(
            f"no tracked swatch moved past tolerance, but the whole figure "
            f"drifted dE {result.pixel_drift_de:.1f} over the "
            f"{PIXEL_DRIFT_TOLERANCE:.1f} pixel limit; a colour the palette "
            f"does not track has been changed"
        )
    elif mean_de > MEAN_DRIFT_TOLERANCE:
        # Say which rule failed. No individual swatch has moved past tolerance;
        # the character has been tinted as a whole. Reporting this as "swatches
        # exceed tolerance" sent me hunting for a swatch that did not exist.
        result.notes.append(
            f"every swatch is individually within dE {SWATCH_TOLERANCE:.0f}, but "
            f"the area-weighted mean is dE {mean_de:.1f}, over the "
            f"{MEAN_DRIFT_TOLERANCE:.1f} aggregate limit; the whole character "
            f"has been tinted"
        )

    # Contamination: any card bleed inside the silhouette is a hard identity fault.
    if contamination_px is None:
        result.contamination_measured = False
        result.notes.append(
            "UNMEASURABLE: this layer's card-bleed status could not be "
            "determined, so contamination is unknown rather than zero. Align "
            "the layer with its source sheet, or re-cut it, before treating "
            "this as a pass."
        )
    elif contamination_px > 0:
        share = contamination_px / max(1, int(solid.sum()))
        result.contamination_score = max(0.0, 100.0 - share * 4000.0)
        result.notes.append(
            f"{contamination_px} contaminated px inside the silhouette "
            f"({share:.2%} of the character)"
        )

    # Legibility: small features stop reading below a height threshold.
    if rendered.height < MIN_LEGIBLE_HEIGHT:
        if identity_critical:
            ratio = rendered.height / MIN_LEGIBLE_HEIGHT
            result.feature_legibility_score = max(0.0, 100.0 * ratio)
            result.notes.append(
                f"rendered at {rendered.height}px tall; below "
                f"{MIN_LEGIBLE_HEIGHT}px small identifying features are not "
                f"proven legible at print size"
            )
        else:
            # Exempted, but never silently. The number is still recorded so an
            # approval step can see exactly what was waived and by how much.
            result.legibility_exempt = True
            result.notes.append(
                f"LEGIBILITY EXEMPT: rendered at {rendered.height}px, below the "
                f"{MIN_LEGIBLE_HEIGHT}px floor, and staged as non-identity-"
                f"bearing background presence. Colour identity was still gated."
            )

    return result
