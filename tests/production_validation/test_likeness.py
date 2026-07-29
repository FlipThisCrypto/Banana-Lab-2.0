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
    SWATCH_TOLERANCE, delta_e, extract_palette, measure, srgb_to_lab,
)

pytestmark = pytest.mark.production_validation


# --- colour maths ---------------------------------------------------------

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
    """dE between the two, after normalising away any luminance change.

    Isolates hue drift from the value change the light is supposed to cause.
    """
    a = np.asarray(before.convert("RGB")).astype(float).reshape(-1, 3).mean(axis=0)
    b = np.asarray(after.convert("RGB")).astype(float).reshape(-1, 3).mean(axis=0)
    weights = np.array([0.2126, 0.7152, 0.0722])
    la, lb = (a * weights).sum(), (b * weights).sum()
    if lb > 1e-4:
        b = np.clip(b * (la / lb), 0, 255)
    return float(delta_e(srgb_to_lab(a), srgb_to_lab(b)))


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
