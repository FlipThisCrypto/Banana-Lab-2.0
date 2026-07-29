"""Regression protection for the scene-integration measure.

Every number asserted here was measured. This measure exists because the
likeness metric has a degenerate optimum: identity preservation is trivially
maximised by not lighting the character at all, so likeness alone drives
protect_neutrals to 1.00, where the character stops responding to the scene and
reads as a cut-out.

See docs/audits/LIKENESS_TUNING_REPORT.md.
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.services.compositor import LightContract, relight
from app.services.integration import measure_integration

pytestmark = pytest.mark.production_validation

COOL = dict(key_color=(150, 225, 235), fill_color=(30, 70, 80))
SPILL = (40, 90, 100)


def _light(protect: float, angle: float = 90.0) -> LightContract:
    return LightContract(key_angle_deg=angle, key_strength=0.22,
                         fill_strength=0.10, rim_strength=0.10,
                         spill_strength=0.14, protect_neutrals=protect, **COOL)


@pytest.fixture
def character() -> Image.Image:
    """Mostly neutral with a small accent - the shape of the real problem."""
    rng = np.random.default_rng(3)
    arr = np.zeros((420, 300, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[:, :, :3] = (216, 216, 216)
    arr[260:, :, :3] = (24, 24, 24)
    arr[30:70, 110:190, :3] = (52, 229, 232)
    # A little texture, so the luminance field is not perfectly flat.
    noise = rng.integers(-6, 7, size=(420, 300, 1))
    arr[..., :3] = np.clip(arr[..., :3].astype(int) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


@pytest.fixture
def plate() -> Image.Image:
    """A cool-cast plate, so the cool contract agrees with it."""
    arr = np.zeros((900, 900, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (96, 132, 146)
    return Image.fromarray(arr, "RGBA")


def _box(character: Image.Image):
    return (300, 300, 300 + character.width, 300 + character.height)


def _score(image, character, plate, contract):
    return measure_integration(image, character, plate, _box(character),
                               contract, spill_color=SPILL).score


def test_integration_falls_as_protection_rises(character, plate):
    """The whole point: monotone in the OPPOSITE direction to likeness.

    Without this there is no interior optimum and protect_neutrals cannot be
    chosen - likeness alone picks 1.00, where the character ignores the light.
    """
    scores = []
    for protect in (0.0, 0.25, 0.5, 0.7, 0.85, 1.0):
        contract = _light(protect)
        scores.append(_score(relight(character, contract, spill_color=SPILL),
                             character, plate, contract))

    assert all(a >= b - 1e-9 for a, b in zip(scores, scores[1:])), scores
    assert scores[0] - scores[-1] > 40, (
        f"needs real dynamic range to be usable as an axis, got {scores}"
    )


def test_a_flat_colour_filter_is_not_mistaken_for_lighting(character, plate):
    """The adversary that killed the first draft of this measure.

    A uniform colour multiply reproduces the honest relight's mean colour
    without ever lighting anything. The first draft scored it 46.6 against the
    honest relight's 47.2 - a dead heat - because it correlated the two dL*
    fields raw. relight() and a multiply are BOTH multiplicative, so both
    produce a dL* field proportional to the figure's own albedo, and that shared
    component dominated the correlation (measured r = 0.8398).

    light_shape is now a PARTIAL correlation, controlling for the figure's
    luminance, so only the part a light's direction contributes is compared.
    """
    contract = _light(0.5)
    honest = relight(character, contract, spill_color=SPILL)

    arr = np.asarray(character).astype(float)
    lit = np.asarray(honest).astype(float)
    opaque = arr[..., 3] == 255
    ratio = ((lit[..., :3][opaque].mean(axis=0) + 1e-6)
             / (arr[..., :3][opaque].mean(axis=0) + 1e-6))
    decal = arr.copy()
    decal[..., :3] = np.clip(arr[..., :3] * ratio, 0, 255)
    decal_img = Image.fromarray(decal.astype(np.uint8), "RGBA")

    good = _score(honest, character, plate, contract)
    bad = _score(decal_img, character, plate, contract)
    assert bad < good - 20, (
        f"a flat tint must not read as lighting: honest {good:.1f}, decal {bad:.1f}"
    )


def test_the_partial_correlation_is_what_rejects_the_decal(character, plate):
    """Guard the mechanism, not just the outcome.

    If light_shape ever reverts to a raw correlation this still passes on the
    score alone for a while, so assert the thing that actually does the work:
    the decal's dL* field is almost entirely explained by the figure's own
    luminance, and the honest relight's is not.
    """
    contract = _light(0.5)
    honest = relight(character, contract, spill_color=SPILL)

    arr = np.asarray(character).astype(float)
    lit = np.asarray(honest).astype(float)
    opaque = arr[..., 3] == 255
    ratio = ((lit[..., :3][opaque].mean(axis=0) + 1e-6)
             / (arr[..., :3][opaque].mean(axis=0) + 1e-6))
    decal = np.clip(arr[..., :3] * ratio, 0, 255)

    weights = np.array([0.2126, 0.7152, 0.0722])
    base = arr[..., :3][opaque] @ weights
    d_honest = (lit[..., :3][opaque] @ weights) - base
    d_decal = (decal[opaque] @ weights) - base

    def explained(field):
        basis = np.stack([np.ones_like(base), base], axis=1)
        coef, *_ = np.linalg.lstsq(basis, field, rcond=None)
        residual = field - basis @ coef
        return 1.0 - residual.var() / field.var()

    assert explained(d_decal) > 0.99, (
        "a uniform multiply's lightness change should be fully explained by "
        "the figure's own albedo"
    )
    assert explained(d_honest) < explained(d_decal), (
        "an honest relight must carry a directional component the multiply "
        "does not"
    )


def test_light_direction_is_actually_measured(character, plate):
    """A character lit from the wrong side does not belong in this panel."""
    contract = _light(0.5)
    right = relight(character, contract, spill_color=SPILL)
    wrong = relight(character, _light(0.5, angle=270.0), spill_color=SPILL)

    assert (_score(wrong, character, plate, contract)
            < _score(right, character, plate, contract) - 20)


def test_an_untouched_cutout_scores_far_below_a_relit_character(character, plate):
    contract = _light(0.5)
    honest = relight(character, contract, spill_color=SPILL)
    assert (_score(character, character, plate, contract)
            < _score(honest, character, plate, contract) - 20)


def test_a_plate_with_no_illuminant_is_reported_unscoreable(character):
    """Grey-world cannot recover a light from a neutral plate, and the measure
    must say so rather than invent a number."""
    neutral = Image.new("RGBA", (900, 900), (128, 128, 128, 255))
    contract = _light(0.5)
    honest = relight(character, contract, spill_color=SPILL)
    result = measure_integration(honest, character, neutral, _box(character),
                                 contract, spill_color=SPILL)
    assert result.score == 0.0
    assert result.notes, "an unscoreable result must explain itself"


def test_the_plate_is_load_bearing(character, plate):
    """Every one of the four rejected first-round designs failed this.

    In one of them, deleting the plate changed the score by 0.000000. If the
    plate can be swapped for a differently-lit one without moving the number,
    the measure is not measuring integration.
    """
    contract = _light(0.5)
    honest = relight(character, contract, spill_color=SPILL)

    warm_plate = Image.fromarray(
        np.clip(np.asarray(plate).astype(float)
                * np.array([1.6, 1.0, 0.55, 1.0]), 0, 255).astype(np.uint8),
        "RGBA",
    )
    assert (_score(honest, character, plate, contract)
            != _score(honest, character, warm_plate, contract))
