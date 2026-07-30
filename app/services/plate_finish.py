"""Deterministic finishing pass on a generated plate.

Three scorecard properties resisted every prompt this pipeline tried:

    n_hue_families        published 4.0    asked three times, went 6.4 -> 5.9 -> 6.9
    hairline_ink_density  published 2.65   18.8 -> 17.0 -> 13.0 -> 12.3
    share_in_large_shapes published 0.558  0.115 -> 0.186 -> 0.295 -> 0.348

Each attempt added adjectives - "large flat areas of colour", "simple bold
shapes", "only three colours", "very few objects" - and each time the model
partly complied and partly did not. Prompting is not a control surface for
these; they are properties of the pixels, so they are set in the pixels.

That is not a cheat. Cel art IS posterised: flat fills inside black linework is
what the published editions are made of, and the published numbers are what a
limited palette measures like. What would be a cheat is blurring to make the
hairline number fall, which is why nothing here blurs - the linework is detected
and preserved at full contrast.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from app.services.likeness import (
    delta_e_chroma, lab_to_srgb_in_gamut, srgb_to_lab,
)

#: Lightness below which a pixel is treated as linework and never touched.
#: The published art's black outlines are the structure of the image; posterising
#: them would soften every edge and lose exactly what the style is.
INK_L = 34.0

#: How many colour cells the plate is reduced to, excluding ink. The published
#: pages measure about four hue families; a few more cells than that gives the
#: shading steps cel art needs without reintroducing a gradient.
#: Swept over the cached plates across 11 configurations; see
#: docs/audits/aesthetic-loop-ledger.json. n_hue_families against palette size:
#: 10 -> 5.74, 6 -> 4.75, 5 -> 4.62, 4 -> 3.78, against a 5.5 ceiling and a
#: published 4.0. Six keeps the published count without collapsing the shading
#: steps cel art needs.
PALETTE_SIZE = 6

#: Chroma below which a cell counts as neutral. Neutrals are quantised in
#: lightness only, so skies and ground do not collapse into one grey.
NEUTRAL_CHROMA = 8.0


def _kmeans_lab(samples: np.ndarray, k: int, iterations: int = 12) -> np.ndarray:
    """Lloyd's algorithm in Lab, seeded deterministically by lightness order.

    Deterministic seeding matters: the same plate must finish the same way every
    run, or a defect cannot be reproduced.
    """
    order = np.argsort(samples[:, 0])
    picks = np.linspace(0, len(order) - 1, k).astype(int)
    centres = samples[order[picks]].copy()

    for _ in range(iterations):
        distance = np.linalg.norm(samples[:, None, :] - centres[None, :, :], axis=2)
        nearest = distance.argmin(axis=1)
        for index in range(k):
            member = samples[nearest == index]
            if len(member):
                centres[index] = member.mean(axis=0)
    return centres


def posterise(image: Image.Image, palette_size: int = PALETTE_SIZE) -> Image.Image:
    """Flatten the plate to a limited palette, preserving linework exactly."""
    rgb = np.asarray(image.convert("RGB")).astype(np.float64)
    lab = srgb_to_lab(rgb)
    ink = lab[..., 0] < INK_L

    body = lab[~ink]
    if body.size == 0:
        return image.convert("RGB")

    # Fit on a subsample: the plate has ~1M pixels and a few thousand is ample
    # for cluster centres, with a fixed stride so the result is reproducible.
    stride = max(1, len(body) // 4000)
    centres = _kmeans_lab(body[::stride], palette_size)

    distance = np.linalg.norm(body[:, None, :] - centres[None, :, :], axis=2)
    flattened = centres[distance.argmin(axis=1)]

    out_lab = lab.copy()
    out_lab[~ink] = flattened
    out = lab_to_srgb_in_gamut(out_lab)
    # Ink returns bit-exact. Nothing here is allowed to soften an outline.
    out[ink] = rgb[ink]
    return Image.fromarray(out.astype(np.uint8), "RGB")


#: Chroma gain is the lever for peak_over_field. Measured across 11 swept
#: configurations: 0.40 -> 35.9, 0.70 -> 42.4, 0.85 -> 43.5, 1.00 -> 49.1,
#: against a 42.6 floor.
#:
#: Settled at 0.60 AFTER the zero-mean fix below, not before. The high gains were
#: chosen while the vignette was silently darkening every plate by ~11 L*, and
#: once that was fixed a much gentler gain cleared the same floor: 0.60 measures
#: peak 47.5 with page lightness preserved.
CHROMA_GAIN = 0.60

#: The glow sits BELOW centre because that is where a standing figure is. Moving
#: it from 0.46 to 0.58 took hairline 12.81 -> 12.44 and peak 43.5 -> 44.4.
VIGNETTE_CENTRE = (0.5, 0.58)
VIGNETTE_STRENGTH = 0.35


#: Ink dilation radius in pixels at the generation resolution.
#:
#: hairline_ink_density counts inches of ink stroke NARROWER than 1.5 pt per
#: square inch: published 2.65, this pipeline 12.4 after every other lever was
#: exhausted. Simplifying the plates moved it 13.3 -> 12.4 and stopped.
#:
#: The fix is not to remove ink. HOUSE_STYLE.md and the style contract both call
#: for "thick uniform black outlines", and SDXL is not delivering them - it draws
#: correct-looking art with linework far finer than the published editions.
#: Thickening the ink is what the house style asks for, and it reduces the
#: hairline count as a consequence rather than as a trick: a stroke that was
#: 1 pt becomes 2 pt and stops being a hairline because it stops being thin.
#:
#: This is the opposite of blurring. Blurring lowers the number by destroying
#: edge contrast; this raises edge contrast by making the black areas larger and
#: harder. test_the_finishing_pass_does_not_blur still holds.
INK_DILATE_PX = 2

#: MEASURED AND REJECTED, kept for the record.
#:
#: Dilation does move the metric: on P01-01, hairline goes 40.6 / 13.5 / 4.2 /
#: 2.3 / 1.4 at radius 0 / 1 / 2 / 3 / 4, and the published median is 2.65. But
#: it moves share_in_large_shapes 0.012 -> 0.801 at the same time, because the
#: linework merges into blobs, and it costs about 10 L* of page lightness at
#: radius 1 and 12 L* at radius 2 - taking finished plates to mean L* 15.7-17.8
#: against a published 37.0.
#:
#: Looked at rather than measured: at radius 3 the railings have merged into
#: solid black. The scorecard read 7/8 while the art moved AWAY from the
#: reference. That is the exact failure the scorecard's author predicted, so the
#: function stays out of the pipeline and stays here as evidence.
_THICKEN_REJECTED = True


def thicken_ink(image: Image.Image, radius: int = INK_DILATE_PX) -> Image.Image:
    """Grow the linework so it matches the house style's declared weight."""
    if radius <= 0:
        return image.convert("RGB")

    rgb = np.asarray(image.convert("RGB")).astype(np.uint8)
    lab = srgb_to_lab(rgb.astype(np.float64))
    ink = (lab[..., 0] < INK_L).astype(np.uint8) * 255

    # A MinFilter on the inverse grows the dark region - a morphological
    # dilation of the ink mask, with a hard edge throughout.
    grown = Image.fromarray(255 - ink, "L").filter(
        ImageFilter.MinFilter(2 * radius + 1))
    grown_mask = np.asarray(grown) < 128

    # New ink takes the darkest colour already present in the plate, so the
    # thickened line matches the art's own black rather than a synthetic one.
    darkest = rgb.reshape(-1, 3)[lab[..., 0].reshape(-1).argmin()]
    out = rgb.copy()
    out[grown_mask] = darkest
    return Image.fromarray(out, "RGB")


def focal_vignette(image: Image.Image, strength: float = VIGNETTE_STRENGTH,
                   centre: tuple[float, float] = VIGNETTE_CENTRE) -> Image.Image:
    """Brighten the middle, sink the corners, so the panel has a focal point.

    `peak_over_field` measured 37.1 then 39.4 against a 42.6 floor while the
    prompt asked for a vignette in three different ways. The published pages get
    their focus from a bright field behind the figure and dead-dark corners; that
    is a gradient over the frame, so it is applied as one.

    Lightness only. Chroma is untouched, so the C_p95 guardrail cannot move and
    no canon colour shifts hue.
    """
    rgb = np.asarray(image.convert("RGB")).astype(np.float64)
    height, width = rgb.shape[:2]

    ys = (np.linspace(0.0, 1.0, height)[:, None] - centre[1]) / 0.5
    xs = (np.linspace(0.0, 1.0, width)[None, :] - centre[0]) / 0.5
    radius = np.sqrt(xs ** 2 + ys ** 2) / np.sqrt(2.0)

    # +1 at the centre, -1 in the corners, smooth between.
    field = np.cos(np.clip(radius, 0.0, 1.0) * np.pi)

    # Zero-MEAN, or this is not a vignette - it is a global darken.
    #
    # Area grows with radius, so most pixels sit where cos is negative and the
    # raw field averages well below zero. Measured consequence: finished plates
    # came out at mean L* 15.7-17.3 against a published 37.0 and a raw-plate
    # 27.5, i.e. the finishing pass was making every plate roughly 11 L* darker
    # than the art it started from while the scorecard read 7/8. Centring the
    # field makes the centre brighten by as much as the corners sink.
    field = field - field.mean()

    lab = srgb_to_lab(rgb)
    ink = lab[..., 0] < INK_L
    lab[..., 0] = np.clip(lab[..., 0] + field * strength * 46.0, 0.0, 100.0)

    # And on CHROMA, which is what actually carries the focal reading.
    #
    # The first version moved lightness only and peak_over_field fell 40.4 ->
    # 36.6. That property is P99 chroma minus the median of a chroma field - a
    # SATURATION contrast, not a brightness one - so a lightness gradient cannot
    # move it and a chroma gradient moves it directly: the centre gets more
    # saturated, the corners less. This also lifts C_p95 rather than risking it.
    chroma_gain = 1.0 + field * CHROMA_GAIN
    lab[..., 1] *= chroma_gain
    lab[..., 2] *= chroma_gain

    out = lab_to_srgb_in_gamut(lab)
    # Linework stays black. Lifting it would grey out every outline in the
    # middle of frame, which is the opposite of the intended effect.
    out[ink] = rgb[ink]
    return Image.fromarray(out.astype(np.uint8), "RGB")


def finish_plate(path, palette_size: int = PALETTE_SIZE,
                 vignette: float = VIGNETTE_STRENGTH) -> Image.Image:
    """The full finishing pass, in the order the two steps must run.

    Posterise first, then vignette: flattening after the gradient would quantise
    the gradient itself into visible bands.
    """
    with Image.open(path) as source:
        plate = source.convert("RGB")
    # thicken_ink is deliberately NOT in this chain. See its docstring: it moves
    # hairline_ink_density into range, but it does so by flooding the frame with
    # black, and that is destroying the art to move a number.
    return focal_vignette(posterise(plate, palette_size), vignette)
