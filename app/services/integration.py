"""Lit-surface agreement (LSA): scene integration for a relit character layer.

Three multiplied terms, each answering a different way of being a cut-out:

    chroma  did the figure's colour move, along the axis the PLATE's own light
            defines, by as much as a real surface under the declared contract
            would - with an absolute perceptual floor under the denominator so a
            light too weak to see cannot score well by being consistent.
    light   did a LIGHTING operation actually happen - is the figure's lightness
            field the one this light produces, or did someone paint a colour
            filter over an untouched cut-out.
    plate   is there a recoverable illuminant in the plate at all.

The chroma term is the only one that varies with protect_neutrals. The light
term is ~1.000 for every honest relight at every protect level (measured) and
~0 for objects that were tinted rather than lit; it is a validity gate, not a
dial.

WHY THIS EXISTS
---------------
The likeness metric has a degenerate optimum. Identity preservation is trivially
maximised by not lighting the character at all, so likeness alone drives
protect_neutrals to 1.00 - where the character's mean chroma response to a
strong key is 0.26, i.e. a cut-out pasted onto a plate. That is the exact
failure the compositor was built to prevent. Read the two together or neither
means anything.

STATUS - NOT A GATE
-------------------
Likeness has 1089 adversarial controls behind it. This has ~400. It is reported,
not gated, and likeness remains the hard constraint. Do not promote this to a
gate without giving it the same treatment.

HISTORY
-------
Four independent designs were proposed for this and all four were broken by
adversarial review, in the same way each time: they measured chroma and only
chroma, so an object with a colour filter and no light scored as well as a
correctly lit one. This is the composite that survived, plus one further fix
found when its own claims were re-verified rather than taken on trust:

`light_shape` was a RAW correlation between the candidate's dL* field and the
declared light's. That cannot tell lighting from filtering. relight() and a flat
colour multiply are BOTH multiplicative, so both produce a dL* field
proportional to the figure's own albedo, and that shared component dominates -
measured r = 0.8398 between an honest relight and a flat decal matched to its
mean colour. The decal scored 46.6 against the honest relight's 47.2, a dead
heat. It is now a PARTIAL correlation controlling for the figure's luminance, so
only the part a light's direction contributes is compared. Measured effect:

    flat decal, 9 character x protect cells    not rejected -> rejected in all 9
    honest relight (0.00 / 0.50 / 0.85)        98.2 / 87.5 / 47.2, unchanged
    lit from 270 deg against a 90 deg contract 5.3 -> 0.0

Costing the honest signal nothing while closing the hole is the shape a real fix
has; see the same pattern in LIKENESS_TUNING_REPORT.md Fix 6.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from app.services.compositor import LightContract, relight
from app.services.likeness import srgb_to_lab

_LUMA = np.array([0.2126, 0.7152, 0.0722])
NEUTRAL = np.array([1 / 3, 1 / 3, 1 / 3])

#: Saturation rate of the chroma term. r = 1 means the figure moved along the
#: plate's illuminant axis by exactly as much as a Lambertian surface under the
#: declared contract would; that pays 0.918 rather than 1.0 on purpose, because
#: relight()'s own free tint measures r = 1.2-1.8 and the scale must not be
#: saturated at the physical prediction.
RESPONSE_GAIN = 2.5

#: Response beyond this multiple of the prediction starts to cost and pays
#: nothing at OVERSHOOT_ZERO.
OVERSHOOT_FREE, OVERSHOOT_ZERO = 2.5, 5.0

#: Perceptual floor on the DENOMINATOR of the response ratio, in dE(a*b*).
#:
#: This is the term that stops the measure being scale-free. Without it,
#: dividing by the contract's own prediction makes key_strength cancel: turn the
#: key down by 10x and a character that visibly does not change scores 100.
#: With it, a contract that cannot move this artwork at least MIN_DEMAND_DE is
#: judged against MIN_DEMAND_DE anyway and scores in proportion to how little it
#: actually did. Measured predicted swings on the real scene lights at
#: key_strength 0.22: 1.5-5.9 dE. Measured effect: key_strength 0.005 / 0.02 /
#: 0.05 / 0.22 scores 8.2 / 24.9 / 51.5 / 92.8 instead of 100 / 100 / 100 / 100.
MIN_DEMAND_DE = 3.0

#: Plate chromaticity offset below which no illuminant can be recovered.
MIN_PLATE_CAST = 0.010

#: The light term's ramps. Measured over 6 characters x 3 scene lights x 6
#: protect levels: honest relights give response 1.000-1.004 and shape
#: 0.9998-1.0000 at EVERY protect level. Everything that was tinted rather than
#: lit sits far below both floors (decal 0.011-0.013 / 0.22-0.55, flat-cast
#: sticker 0.010-0.021 / -0.07-0.87).
LIGHT_RESPONSE_FLOOR, LIGHT_RESPONSE_FULL = 0.25, 0.60
LIGHT_SHAPE_FLOOR, LIGHT_SHAPE_FULL = 0.50, 0.90
#: A lightness response several times the declared light's is not this light.
#: Measured: a flat patch of plate colour reads 2.6-4.3.
LIGHT_RESPONSE_FREE, LIGHT_RESPONSE_ZERO = 2.5, 5.0


def _lin(x):
    a = np.asarray(x, dtype=np.float64) / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def _srgb(x):
    a = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055) * 255.0


def _ramp(x, lo, hi):
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def _decay(x, free, zero):
    return 1.0 if x <= free else float(max(0.0, 1.0 - (x - free) / (zero - free)))


def plate_illuminant_axis(plate: Image.Image, box, dilate: float = 0.5):
    """The a*b* direction the PLATE's own light pushes a surface, from pixels.

    Linear grey-world over the placement box dilated by `dilate` on each side,
    then a mid-grey card pushed through the recovered chromaticity and read in
    a*b*. Grey-world confounds albedo with illuminant - unresolvable from one
    image - but only the DIRECTION is used, and the direction is what separates
    "lit for this panel" from "lit for a different one".

    Measured: cool plate (exp002_seed760201) u = (-0.749, -0.663) cast 0.2232;
    warm plate (exp007_B_bucket_crop) u = (+0.560, +0.828) cast 0.1981.

    This is where the plate becomes load-bearing. Because it is the axis the
    score is measured ALONG, rather than a multiplier bolted on beside it, a
    contract that disagrees with the plate produces a negative response and
    there is nothing left to divide: measured 0.0 on all six off-diagonal cells
    of a 3-light x 2-plate matrix, against 84.8-98.5 on the diagonal.
    """
    left, top, right, bottom = box
    w, h = right - left, bottom - top
    l = max(0, int(left - w * dilate)); t = max(0, int(top - h * dilate))
    r = min(plate.width, int(right + w * dilate))
    b = min(plate.height, int(bottom + h * dilate))
    region = np.asarray(plate.convert("RGB").crop((l, t, r, b)), dtype=np.float64)
    e = _lin(region).reshape(-1, 3).mean(axis=0)
    chrom = e / max(e.sum(), 1e-12)
    cast = float(np.linalg.norm(chrom - NEUTRAL))
    if cast < MIN_PLATE_CAST:
        return np.zeros(2), cast
    gain = chrom / NEUTRAL
    grey = _lin(np.array([128.0, 128.0, 128.0]))
    lit = _srgb(grey * gain / gain.mean())
    ab = srgb_to_lab(lit)[1:] - srgb_to_lab(np.array([128.0, 128.0, 128.0]))[1:]
    n = float(np.linalg.norm(ab))
    return (ab / n if n > 1e-9 else np.zeros(2)), cast


def scene_illuminant(light: LightContract, spill_color=None) -> np.ndarray:
    """Unit-luminance LINEAR illuminant the contract declares.

    Built from the contract's own numbers, NOT from relight()'s internal
    arithmetic (its 1.6 / 1.4 / 2.0 multipliers and its `lit` gradient are not
    copied), so the measure can disagree with the renderer rather than merely
    confirm it ran. Unit luminance because this describes the light's COLOUR;
    exposure is handled by the light term, not here.
    """
    ks, fs = float(light.key_strength), float(light.fill_strength)
    ss = float(light.spill_strength) if spill_color is not None else 0.0
    e = (ks * _lin(np.array(light.key_color, dtype=np.float64))
         + fs * _lin(np.array(light.fill_color, dtype=np.float64))
         + (ss * _lin(np.array(spill_color, dtype=np.float64))
            if spill_color is not None else 0.0)
         + max(0.0, 1.0 - ks - fs - ss) * np.ones(3))
    return e / float(e @ _LUMA)


def _free_tint(light: LightContract) -> LightContract:
    return LightContract(
        key_angle_deg=light.key_angle_deg, key_color=light.key_color,
        key_strength=light.key_strength, fill_color=light.fill_color,
        fill_strength=light.fill_strength, rim_strength=light.rim_strength,
        protect_neutrals=0.0, cast_length=light.cast_length,
        cast_opacity=light.cast_opacity, contact_opacity=light.contact_opacity,
        spill_strength=light.spill_strength, ambient_lift=light.ambient_lift)


@dataclass
class IntegrationResult:
    score: float = 0.0
    #: Chroma the figure actually moved along the plate's illuminant axis, dE.
    achieved_de: float = 0.0
    #: Chroma a Lambertian surface of this artwork would move, same axis, dE.
    predicted_de: float = 0.0
    #: achieved / max(predicted, MIN_DEMAND_DE). The monotone driver.
    response_ratio: float = 0.0
    chroma_factor: float = 0.0
    #: Figure's lightness response as a fraction of the declared light's.
    light_response: float = 0.0
    #: Correlation of the figure's lightness change with the declared light's.
    light_shape: float = 0.0
    light_factor: float = 0.0
    plate_cast: float = 0.0
    #: cos between the plate's recovered axis and the contract's declared one.
    #: Reported, not multiplied in: the plate axis is already the axis the score
    #: is measured along, so disagreement shows up as a negative response.
    contract_plate_cos: float = 0.0
    demand_floored: bool = False
    opaque_px: int = 0
    notes: list = field(default_factory=list)

    def to_dict(self):
        return {k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


def measure_integration(
    relit: Image.Image,
    original: Image.Image,
    plate: Image.Image,
    box,
    light: LightContract,
    *,
    spill_color=None,
    post: callable | None = None,
    reference_cache: dict | None = None,
) -> IntegrationResult:
    """Scene integration, 0-100. Read together with likeness, never alone.

    `relit`     the character layer as it will be pasted (after relight and any
                post-relight step such as depth haze)
    `original`  the same layer before relight - composite_panel already keeps
                this as `canon_reference`
    `plate`     the panel plate
    `box`       the character's placement rectangle in plate coordinates
    `spill_color` the colour composite_panel's _sample_environment returned
    `post`      any deterministic post-relight transform composite_panel applies
                (depth haze). REQUIRED for any placement that is not foreground:
                it is applied to the baseline and to the internal reference, so
                the veil's own contribution cancels instead of being credited to
                the relight. Attach a hashable `.cache_key` attribute to it if
                you pass `reference_cache`.
    """
    res = IntegrationResult()
    # Post-relight steps that are not the relight - depth haze - must be applied
    # to the BASELINE as well as to the candidate, or the measure credits the
    # relight with work the veil did. Measured without this: a value-only
    # cut-out (protect_neutrals = 1.00, no chroma response at all) under the
    # background veil scored 47.4-92.5 purely on the veil's own plate-coloured
    # chroma. With it, 0.0-12.2, against 40.0-69.5 for an honestly lit and
    # hazed figure at protect 0.70.
    base_img = post(original) if post is not None else original
    rel = np.asarray(relit.convert("RGBA")).astype(np.float64)
    org = np.asarray(base_img.convert("RGBA")).astype(np.float64)
    if rel.shape[:2] != org.shape[:2]:
        res.notes.append("relit and approved layer are not pixel aligned")
        return res
    mask = (rel[..., 3] > 200) & (org[..., 3] > 200)
    res.opaque_px = int(mask.sum())
    if res.opaque_px < 200:
        res.notes.append("too few opaque pixels to measure")
        return res

    u, cast = plate_illuminant_axis(plate, box)
    res.plate_cast = round(cast, 4)
    if cast < MIN_PLATE_CAST:
        res.notes.append(
            f"plate carries no recoverable colour cast (|e|={cast:.4f}); there "
            f"is no scene illuminant to integrate with and this measure has no "
            f"signal here")
        return res

    lab_rel = srgb_to_lab(rel[..., :3][mask])
    lab_org = srgb_to_lab(org[..., :3][mask])

    # --- chroma term ------------------------------------------------------
    illum = scene_illuminant(light, spill_color)
    pred_lab = srgb_to_lab(_srgb(_lin(org[..., :3][mask]) * illum))
    achieved = float(((lab_rel[:, 1:] - lab_org[:, 1:]) @ u).mean())
    predicted = float(((pred_lab[:, 1:] - lab_org[:, 1:]) @ u).mean())
    res.achieved_de, res.predicted_de = round(achieved, 3), round(predicted, 3)

    demand = max(predicted, MIN_DEMAND_DE)
    res.demand_floored = predicted < MIN_DEMAND_DE
    r = achieved / demand
    res.response_ratio = round(r, 3)
    res.chroma_factor = round(
        0.0 if r <= 0 else (1.0 - float(np.exp(-RESPONSE_GAIN * r)))
        * _decay(r, OVERSHOOT_FREE, OVERSHOOT_ZERO), 4)

    # --- light term -------------------------------------------------------
    # The lightness field the DECLARED light produces on this artwork. Every
    # honest relight matches it at every protect_neutrals setting (measured
    # response 1.000-1.004, shape 0.9998-1.0000), because relight() takes L*
    # from the tinted result on both sides of the protect blend. An object that
    # was given a colour filter instead of a light has no such field.
    #
    # Key the cache on the layer's CONTENT. Keying on id() is wrong: PIL images
    # are freed and their addresses reused, so two different characters alias to
    # one reference. That bug bit during development; it surfaced as a shape
    # mismatch but would otherwise be a silent few-point error.
    key = (hash(original.tobytes()), original.size,
           light.key_angle_deg, light.key_color, light.key_strength,
           light.fill_color, light.fill_strength, light.rim_strength,
           light.spill_strength, light.ambient_lift, spill_color,
           None if post is None else getattr(post, "cache_key", id(post)))
    if reference_cache is not None and key in reference_cache:
        d_ref = reference_cache[key]
    else:
        ref = relight(original, _free_tint(light), spill_color=spill_color)
        if post is not None:
            ref = post(ref)
        d_ref = (srgb_to_lab(
            np.asarray(ref.convert("RGBA")).astype(np.float64)[..., :3][mask])[:, 0]
            - lab_org[:, 0])
        if reference_cache is not None:
            reference_cache[key] = d_ref

    d_cand = lab_rel[:, 0] - lab_org[:, 0]
    base_luma = lab_org[:, 0]
    energy = float(d_ref @ d_ref)
    if energy < 1e-6:
        res.light_response, res.light_shape, res.light_factor = 0.0, 0.0, 0.0
        res.notes.append(
            "this contract changes the artwork's lightness not at all, so "
            "whether a lighting operation happened cannot be verified")
    else:
        res.light_response = round(float(d_cand @ d_ref) / energy, 4)
        sc, sr = float(d_cand.std()), float(d_ref.std())
        # PARTIAL correlation, controlling for the figure's own luminance.
        #
        # A raw correlation here cannot tell lighting from filtering. relight()
        # and a flat colour multiply are BOTH multiplicative, so both produce a
        # dL* field proportional to the figure's own albedo, and that shared
        # component dominates: measured r = 0.8398 between an honest relight and
        # a flat decal built to match its mean colour. The decal then scored
        # 46.6 against the honest 47.2 - not rejected.
        #
        # Removing the albedo-explained part of BOTH fields leaves the part a
        # light's DIRECTION actually contributes, which is the thing being
        # asked about.
        def _resid(v):
            basis = np.stack([np.ones_like(base_luma), base_luma], axis=1)
            coef, *_ = np.linalg.lstsq(basis, v, rcond=None)
            return v - basis @ coef

        rc, rr = _resid(d_cand), _resid(d_ref)
        src, srr = float(rc.std()), float(rr.std())
        res.light_shape = round(
            0.0 if sc < 1e-9 or sr < 1e-9 or src < 1e-9 or srr < 1e-9
            else float(np.corrcoef(rc, rr)[0, 1]), 4)
        res.light_factor = round(
            _ramp(res.light_response, LIGHT_RESPONSE_FLOOR, LIGHT_RESPONSE_FULL)
            * _decay(res.light_response, LIGHT_RESPONSE_FREE, LIGHT_RESPONSE_ZERO)
            * _ramp(res.light_shape, LIGHT_SHAPE_FLOOR, LIGHT_SHAPE_FULL), 4)

    res.score = round(100.0 * res.chroma_factor * res.light_factor, 1)

    # --- diagnostics ------------------------------------------------------
    uc = pred_lab[:, 1:].mean(axis=0) - lab_org[:, 1:].mean(axis=0)
    n = float(np.linalg.norm(uc))
    res.contract_plate_cos = round(float(uc @ u / n) if n > 1e-9 else 0.0, 3)
    if res.contract_plate_cos < 0.0:
        res.notes.append(
            f"the declared light pushes colour AWAY from the plate's own "
            f"illuminant (cos {res.contract_plate_cos:+.2f}); no value of "
            f"protect_neutrals integrates this figure - the contract and the "
            f"plate disagree, and the contract is the thing to fix")
    if res.demand_floored:
        res.notes.append(
            f"this contract can only move a real surface {predicted:.2f} dE "
            f"along the plate's illuminant axis, under the {MIN_DEMAND_DE} dE "
            f"visibility floor; the light is too weak to integrate this figure "
            f"whatever protect_neutrals does, so it is scored against the floor")
    if 0 < res.light_factor < 1.0:
        res.notes.append(
            f"the figure's lightness does not match what this light does to it "
            f"(response {res.light_response:.2f}, shape {res.light_shape:.2f}); "
            f"this object was tinted rather than lit")
    if r > OVERSHOOT_FREE:
        res.notes.append(f"over-lit: {r:.1f}x the response the contract implies")
    return res
