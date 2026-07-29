"""Regression protection for the likeness metric and the relight tuning.

Every number asserted here was measured, and every assertion protects a specific
finding recorded in docs/audits/LIKENESS_TUNING_REPORT.md. If one of these
fails, character likeness has regressed.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.services.compositor import LightContract, relight
from app.services.likeness import (
    MEAN_DRIFT_TOLERANCE, PIXEL_DRIFT_TOLERANCE, SWATCH_TOLERANCE, delta_e,
    delta_e_chroma,
    extract_palette, lab_to_srgb,
    lab_to_srgb_in_gamut, measure, srgb_to_lab,
)

pytestmark = pytest.mark.production_validation


# --- colour maths ---------------------------------------------------------

def test_lab_srgb_round_trip_is_exact():
    """relight() recombines in Lab, so the inverse must be a true inverse.

    A lossy inverse would silently shift every canon colour on every panel.
    """
    rgb = np.array([
        [185, 66, 53], [52, 229, 232], [222, 222, 222], [10, 10, 10],
        [0, 0, 0], [255, 255, 255], [168, 192, 156], [144, 144, 144],
    ], dtype=float)
    back = lab_to_srgb(srgb_to_lab(rgb))
    assert np.abs(back - rgb).max() < 1e-6


def test_lab_recombination_holds_hue_when_out_of_gamut():
    """Darkening saturated colours leaves sRGB. The hue must survive anyway.

    Channel clipping does not survive it: cyan taken to 60% L* clips red to
    zero and swings a* by 12. Chroma-scaled gamut mapping keeps the hue angle
    and gives up only unrepresentable chroma.
    """
    rgb = np.array([[185, 66, 53], [52, 229, 232], [168, 192, 156]], dtype=float)
    lab = srgb_to_lab(rgb)
    darker = lab.copy()
    darker[:, 0] *= 0.6

    mapped = srgb_to_lab(lab_to_srgb_in_gamut(darker))
    clipped = srgb_to_lab(np.clip(lab_to_srgb(darker), 0.0, 255.0))

    def hue_deg(v):
        return np.degrees(np.arctan2(v[:, 2], v[:, 1]))

    assert np.abs(hue_deg(mapped) - hue_deg(lab)).max() < 1.0
    assert (np.abs(hue_deg(clipped) - hue_deg(lab)).max()
            > np.abs(hue_deg(mapped) - hue_deg(lab)).max())


def test_lab_conversion_anchors():
    """Known reference values, so a broken conversion cannot silently pass."""
    black = srgb_to_lab(np.array([0.0, 0.0, 0.0]))
    white = srgb_to_lab(np.array([255.0, 255.0, 255.0]))
    assert black[0] == pytest.approx(0.0, abs=0.5)
    assert white[0] == pytest.approx(100.0, abs=0.5)
    assert abs(white[1]) < 0.5 and abs(white[2]) < 0.5


def test_delta_e_is_zero_for_identical_colours():
    a = srgb_to_lab(np.array([120.0, 60.0, 200.0]))
    assert delta_e(a, a) == pytest.approx(0.0)


def test_delta_e_grows_with_visible_difference():
    grey = srgb_to_lab(np.array([128.0, 128.0, 128.0]))
    near = srgb_to_lab(np.array([131.0, 128.0, 127.0]))
    far = srgb_to_lab(np.array([255.0, 0.0, 0.0]))
    assert delta_e(grey, near) < 5
    assert delta_e(grey, far) > 60


# --- palette extraction ---------------------------------------------------

def test_palette_is_measured_from_the_art(tmp_path):
    """Two flat fills should come back as two swatches, largest first."""
    arr = np.zeros((100, 100, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[:70, :, :3] = (200, 40, 40)
    arr[70:, :, :3] = (30, 30, 30)
    path = tmp_path / "flat.png"
    Image.fromarray(arr, "RGBA").save(path)

    palette = extract_palette(path)
    assert len(palette) >= 2
    assert palette[0].share > palette[1].share
    assert palette[0].rgb[0] > 150, "the dominant fill should be the red"


def test_palette_ignores_transparent_pixels(tmp_path):
    arr = np.zeros((60, 60, 4), dtype=np.uint8)
    arr[..., :3] = (255, 0, 255)      # magenta everywhere
    arr[:30, :, 3] = 255              # but only the top half is opaque
    arr[:30, :, :3] = (10, 120, 200)
    path = tmp_path / "half.png"
    Image.fromarray(arr, "RGBA").save(path)

    palette = extract_palette(path)
    assert palette, "should find the opaque colour"
    assert palette[0].rgb[0] < 60, "magenta is transparent and must not be sampled"


# --- the metric itself ----------------------------------------------------

def test_identical_image_scores_near_100(tmp_path):
    """The floor requirement: a layer compared with itself must pass.

    Fixture is 400px tall so it clears MIN_LEGIBLE_HEIGHT; this test is probing
    palette fidelity, not size.
    """
    arr = np.zeros((400, 240, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[:200, :, :3] = (222, 222, 222)
    arr[200:, :, :3] = (0, 0, 0)
    path = tmp_path / "layer.png"
    Image.fromarray(arr, "RGBA").save(path)

    result = measure(Image.open(path).convert("RGBA"), path, "MZ-CHAR-005")
    assert result.score >= 99.0
    assert result.passed
    assert result.palette_delta_e < 1.0


def test_a_recoloured_character_fails(tmp_path):
    """A hue shift large enough to be visible must fail the gate."""
    arr = np.zeros((400, 240, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (220, 60, 60)
    path = tmp_path / "layer.png"
    Image.fromarray(arr, "RGBA").save(path)

    shifted = arr.copy()
    shifted[..., :3] = (60, 220, 60)      # red character rendered green
    result = measure(Image.fromarray(shifted, "RGBA"), path, "MZ-CHAR-005")
    assert not result.passed
    assert result.palette_delta_e > SWATCH_TOLERANCE


def test_contamination_fails_even_with_a_perfect_palette(tmp_path):
    """Card bleed is an identity fault; a good palette must not mask it.

    This is the component-gate rule: a high average never hides a failed
    component.
    """
    arr = np.zeros((400, 240, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (200, 200, 200)
    path = tmp_path / "layer.png"
    Image.fromarray(arr, "RGBA").save(path)

    clean = measure(Image.open(path).convert("RGBA"), path, "MZ-CHAR-001")
    assert clean.passed

    dirty = measure(Image.open(path).convert("RGBA"), path, "MZ-CHAR-001",
                    contamination_px=2000)
    assert not dirty.passed
    assert dirty.contamination_score < 99.0


def test_a_tiny_render_fails_legibility(tmp_path):
    arr = np.zeros((60, 40, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (180, 180, 180)
    path = tmp_path / "layer.png"
    Image.fromarray(arr, "RGBA").save(path)

    result = measure(Image.open(path).convert("RGBA"), path, "MZ-CHAR-003")
    assert result.feature_legibility_score < 85.0
    assert not result.passed


# --- the relight tuning ---------------------------------------------------

def _flat(rgb: tuple[int, int, int], size=(160, 100)) -> Image.Image:
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = rgb
    return Image.fromarray(arr, "RGBA")


def _hue_shift(before: Image.Image, after: Image.Image) -> float:
    """Chroma-plane dE: drift in a*/b*, ignoring the L* the light may change.

    This used to normalise luminance by scaling RGB uniformly and then take a
    full dE. That is not luminance-normalisation - scaling a saturated colour
    up in RGB also raises its chroma. Restoring (180,60,48) after a relight
    needed a x1.52 scale, which pushed a*b* from (47.9, 34.0) to (64.4, 46.4)
    and reported dE 21.6 for a relight whose real chroma drift was 2.3. The
    helper was measuring its own normalisation. Use the same L*-independent
    instrument the metric itself uses.
    """
    a = np.asarray(before.convert("RGB")).astype(float).reshape(-1, 3).mean(axis=0)
    b = np.asarray(after.convert("RGB")).astype(float).reshape(-1, 3).mean(axis=0)
    return float(delta_e_chroma(srgb_to_lab(b), srgb_to_lab(a)))


CYAN_LIGHT = dict(key_angle_deg=90.0, key_color=(150, 225, 235),
                  fill_color=(30, 70, 80), key_strength=0.22,
                  fill_strength=0.10, spill_strength=0.14)


@pytest.mark.parametrize("colour", [
    (240, 240, 240),   # NeonBlue face white
    (252, 252, 252),   # Moodz pale chest
    (180, 60, 48),     # Scarline scarlet family
    (168, 192, 156),   # Zombie pale green
    (144, 144, 144),   # mid grey - eye rings, under-eye bags
])
def test_hue_safe_relight_holds_canon_colours(colour):
    """Light must change value, not hue. Applies to saturated AND neutral fills.

    The first fix only shielded near-neutrals and left saturated canon colours
    drifting by dE 14-20 - Scarline's scarlet and Zombie's green among them.
    """
    layer = _flat(colour)
    free = relight(layer, LightContract(**CYAN_LIGHT, protect_neutrals=0.0),
                   spill_color=(40, 90, 100))
    safe = relight(layer, LightContract(**CYAN_LIGHT, protect_neutrals=0.85),
                   spill_color=(40, 90, 100))

    assert _hue_shift(layer, safe) < _hue_shift(layer, free), (
        f"hue-safe relight should drift {colour} less than a free tint"
    )
    assert _hue_shift(layer, safe) < 8.0, "residual hue drift is too large"


def test_full_protection_preserves_hue_exactly():
    layer = _flat((180, 60, 48))
    safe = relight(layer, LightContract(**CYAN_LIGHT, protect_neutrals=1.0),
                   spill_color=(40, 90, 100))
    assert _hue_shift(layer, safe) < 1.5


def test_relight_still_changes_luminance():
    """A relight that preserves everything is not a relight."""
    layer = _flat((150, 150, 150))
    lit = relight(layer, LightContract(**CYAN_LIGHT, protect_neutrals=0.85),
                  spill_color=(40, 90, 100))
    before = np.asarray(layer.convert("L")).astype(float).mean()
    after = np.asarray(lit.convert("L")).astype(float).mean()
    assert abs(after - before) > 1.0, "the light must still affect value"


def test_colour_under_full_transparency_cannot_reach_the_output():
    """relight() neutralises RGB where alpha == 0, for speed. Prove it is free.

    Cut-out layers carry arbitrary matte colour under alpha=0. It never renders,
    but it dominated the gamut search (67.6% of pixels out of gamut, only 4.1%
    both visible AND out of gamut). Neutralising it took relight from 8.23s to
    1.66s on a 1.04MP layer. Measured bit-identical on 8 layers; this holds it.
    """
    arr = np.zeros((120, 120, 4), dtype=np.uint8)
    arr[..., :3] = (200, 100, 50)
    arr[30:90, 30:90, 3] = 255
    arr[20:40, 20:40, 3] = 128          # semi-transparent edge must be kept
    clean = Image.fromarray(arr, "RGBA")

    polluted = arr.copy()
    polluted[..., :3][polluted[..., 3] == 0] = (37, 211, 102)

    light = LightContract(**CYAN_LIGHT, protect_neutrals=0.85)
    a = np.asarray(relight(clean, light, spill_color=(40, 90, 100))).astype(int)
    b = np.asarray(relight(Image.fromarray(polluted, "RGBA"), light,
                           spill_color=(40, 90, 100))).astype(int)

    visible = arr[..., 3] > 0
    assert np.array_equal(a[..., :3][visible], b[..., :3][visible])


def test_relight_preserves_alpha():
    arr = np.zeros((80, 80, 4), dtype=np.uint8)
    arr[..., :3] = (200, 100, 50)
    arr[20:60, 20:60, 3] = 255
    layer = Image.fromarray(arr, "RGBA")
    lit = relight(layer, LightContract(**CYAN_LIGHT, protect_neutrals=0.85))
    assert np.array_equal(
        np.asarray(layer.getchannel("A")), np.asarray(lit.getchannel("A"))
    )


def test_default_protection_is_the_tuned_value():
    """Guards against someone lowering the default and quietly regressing."""
    assert LightContract(key_angle_deg=0, key_color=(255, 255, 255)).protect_neutrals >= 0.85


# --- negative controls ----------------------------------------------------
#
# These exist because the metric passed three of six deliberately-broken inputs
# on its first two designs, including the exact free-tint failure mode it was
# written to catch. A metric that passes everything is indistinguishable from no
# metric. These are not optional.

@pytest.fixture
def canon_character():
    """A small synthetic character: mostly neutral, with one small hue accent.

    Shaped like the real problem - NeonBlue is mostly white fur and black
    clothing, and his identity lives in a cyan crown that is under 4% of him.
    """
    arr = np.zeros((400, 300, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[:, :, :3] = (222, 222, 222)          # pale fur, dominant
    arr[240:, :, :3] = (10, 10, 10)          # black clothing
    arr[20:60, 110:190, :3] = (52, 229, 232)  # cyan crown, ~2.7% of the figure
    return Image.fromarray(arr, "RGBA")


def _score(rendered, canon):
    return measure(rendered, canon, "MZ-CHAR-005")


def test_control_unmodified_passes(canon_character):
    result = _score(canon_character, canon_character)
    assert result.passed
    assert result.score >= 99.0


def test_damage_to_a_colour_the_palette_never_tracked_is_still_caught():
    """The palette has a coverage hole. The pixel rule is the net under it.

    A cluster below min_share is not tracked at all, so nothing in the swatch
    rules can see it change. Measured on real art: neonblue_21_running has
    11201 high-chroma pixels (3.60% of the figure) and 100% of them sit more
    than dE 14 from any tracked swatch - his palette comes back entirely
    neutral, because the cyan crown fragments into Lab clusters that each fall
    under the threshold. Recolouring it scored exactly 100.0. The metric saw
    nothing, because nothing was there to see.

    Reproduced here by varying the accent across Lab bins, which is what the
    real art does. Note that scattering one FLAT colour spatially does not
    reproduce it - that stays a single cluster and gets tracked normally.
    """
    arr = np.zeros((400, 300, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[:, :, :3] = (222, 222, 222)
    arr[240:, :, :3] = (10, 10, 10)
    # A saturated accent spread across Lab bins: 13 distinct colours, 4.8% of
    # the figure, none of them a large enough single cluster to be tracked.
    accents = []
    for i, row in enumerate(range(20, 220, 16)):
        colour = (min(250, 20 + i * 16), min(250, 190 + i * 10),
                  min(250, 205 + i * 10))
        arr[row:row + 2, 40:260, :3] = colour
        accents.append(colour)
    canon = Image.fromarray(arr, "RGBA")

    chromatic = [s for s in extract_palette(canon) if max(s.rgb) - min(s.rgb) > 40]
    assert not chromatic, (
        "fixture invalid: the accent IS tracked, so it does not test the hole"
    )

    recoloured = arr.copy()
    for colour in set(accents):
        mask = np.all(arr[..., :3] == colour, axis=-1)
        recoloured[..., :3][mask] = (colour[2], colour[0], colour[1])

    result = measure(Image.fromarray(recoloured, "RGBA"), canon, "MZ-CHAR-001")
    assert result.pixel_drift_de > PIXEL_DRIFT_TOLERANCE
    assert not result.passed, (
        "recolouring an untracked identity colour must still fail"
    )


def test_the_two_palette_rules_each_catch_what_the_other_misses(canon_character):
    """The mean rule and the worst rule are not redundant. Measured separation:

                                worst dE   mean dE
      legitimate relights        1.6-9.2   0.7-1.5
      free tint, cool key           10.3       5.9   <- only the mean catches it
      free tint, red key            17.6       9.7
      fully desaturated             40.3       2.7   <- only the worst catches it
      crown recoloured orange       86.9       2.4   <- only the worst catches it

    Drop either rule and a real identity failure passes.
    """
    arr = np.asarray(canon_character).copy()

    # Recolour the small crown: huge worst, tiny mean (it is 2.7% of the figure).
    recoloured = arr.copy()
    recoloured[20:60, 110:190, :3] = (232, 140, 52)
    r = _score(Image.fromarray(recoloured, "RGBA"), canon_character)
    assert not r.passed
    assert r.palette_worst_de > SWATCH_TOLERANCE
    assert r.palette_mean_de < MEAN_DRIFT_TOLERANCE, (
        "the mean must NOT catch this - that is why the worst rule exists"
    )

    # Tint everything gently: every swatch stays inside tolerance, mean does not.
    tinted = arr.astype(float)
    tinted[..., :3] *= np.array([0.92, 1.0, 1.03])
    tinted = np.clip(tinted, 0, 255).astype(np.uint8)
    r = _score(Image.fromarray(tinted, "RGBA"), canon_character)
    assert not r.passed
    assert r.palette_worst_de < SWATCH_TOLERANCE, (
        "no single swatch should be over tolerance - that is why the mean exists"
    )
    assert r.palette_mean_de > MEAN_DRIFT_TOLERANCE


def test_palette_gate_and_the_de_tolerances_cannot_disagree(canon_character):
    """palette_score >= 92 must mean exactly 'both dE rules satisfied'.

    They disagreed once: Clever under the red key had every swatch inside dE 12
    and an area-weighted mean of 1.4, yet scored 85.2 and was reported as
    'palette drift' when nothing had drifted past tolerance. A gate derived
    from one tolerance while the rule used another will always drift apart.
    """
    arr = np.asarray(canon_character).astype(float)
    for factor in (1.00, 0.97, 0.94, 0.90, 0.85, 0.75, 0.60):
        shifted = arr.copy()
        shifted[..., :3] *= np.array([factor, 1.0, 2.0 - factor])
        r = _score(Image.fromarray(np.clip(shifted, 0, 255).astype(np.uint8),
                                   "RGBA"), canon_character)
        within = (r.palette_mean_de <= MEAN_DRIFT_TOLERANCE
                  and r.palette_worst_de <= SWATCH_TOLERANCE)
        assert (r.palette_score >= 92.0) == within, (
            f"factor {factor}: score {r.palette_score:.1f} disagrees with "
            f"mean {r.palette_mean_de:.2f} / worst {r.palette_worst_de:.2f}"
        )


def test_control_hue_swap_fails(canon_character):
    arr = np.asarray(canon_character).copy()
    arr[..., [0, 1]] = arr[..., [1, 0]]
    result = _score(Image.fromarray(arr, "RGBA"), canon_character)
    assert not result.passed, "a hue-swapped character must not pass"


def test_control_desaturation_fails(canon_character):
    arr = np.asarray(canon_character).astype(float).copy()
    luma = (arr[..., :3] * [0.2126, 0.7152, 0.0722]).sum(axis=2, keepdims=True)
    arr[..., :3] = np.repeat(luma, 3, axis=2)
    result = _score(Image.fromarray(arr.astype(np.uint8), "RGBA"), canon_character)
    assert not result.passed, "a desaturated character must not pass"


def test_control_small_accent_recolour_fails(canon_character):
    """The accent is under 3% of the figure. Area weighting alone misses it.

    This is the case that survived two metric designs: recolouring the whole of
    NeonBlue's cyan crown scored 100.
    """
    arr = np.asarray(canon_character).copy()
    accent = (arr[..., 2] > 150) & (arr[..., 1] > 150) & (arr[..., 0] < 170)
    assert accent.sum() > 0, "fixture must contain an accent to destroy"
    assert accent.sum() / (arr.shape[0] * arr.shape[1]) < 0.05, "accent must be small"
    arr[..., :3][accent] = (200, 120, 60)
    result = _score(Image.fromarray(arr, "RGBA"), canon_character)
    assert not result.passed, "destroying a small identity accent must fail"


def test_control_free_tint_fails(canon_character):
    """The failure mode this whole module exists to catch."""
    free = relight(canon_character,
                   LightContract(**CYAN_LIGHT, protect_neutrals=0.0),
                   spill_color=(40, 90, 100))
    assert not _score(free, canon_character).passed


def test_control_crushed_lightness_fails(canon_character):
    arr = np.asarray(canon_character).astype(float).copy()
    arr[..., :3] *= 0.25
    result = _score(Image.fromarray(arr.astype(np.uint8), "RGBA"), canon_character)
    assert not result.passed


def test_control_contamination_fails(canon_character):
    result = measure(canon_character, canon_character, "MZ-CHAR-005",
                     contamination_px=6000)
    assert not result.passed


def test_correct_relight_still_passes(canon_character):
    """The positive control. If this fails, the gate is simply too tight."""
    safe = relight(canon_character,
                   LightContract(**CYAN_LIGHT, protect_neutrals=0.85),
                   spill_color=(40, 90, 100))
    assert _score(safe, canon_character).passed


def test_small_accent_is_actually_tracked_in_the_palette(canon_character):
    """Root cause of the third metric failure: the accent was never a swatch.

    It fragmented across 1087 RGB bins on the real layer and never cleared the
    share threshold, so changing it was literally not measured.
    """
    palette = extract_palette(canon_character)
    chromatic = [s for s in palette if max(s.rgb) - min(s.rgb) > 60]
    assert chromatic, f"no chromatic swatch tracked; palette was {[s.hex for s in palette]}"


def test_unaligned_comparison_is_reported_as_unmeasurable(canon_character):
    """A size mismatch must be loudly flagged, not silently scored."""
    smaller = canon_character.resize((canon_character.width // 2,
                                      canon_character.height // 2))
    result = measure(smaller, canon_character, "MZ-CHAR-005")
    assert any("UNMEASURABLE" in n for n in result.notes)
