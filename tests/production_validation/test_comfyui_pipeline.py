"""Regression protection for the panel production pipeline.

Split into checks that need a live ComfyUI (skipped when it is down) and checks
that do not. The offline set is the important one: it protects the style
contract and the canon guards, which is where the evidence-backed decisions live.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import paths
from app.services import workflows as wf

pytestmark = pytest.mark.production_validation

TEMPLATES = paths.REPO_ROOT / "workflows" / "comfyui" / "api_payloads"


# --- style contract -------------------------------------------------------

def test_style_contract_weights_the_load_bearing_terms():
    """Experiment 002 vs 003: unweighted style tokens lose to a long scene."""
    assert "(flat 2d vector cartoon illustration:1.5)" in wf.STYLE_POSITIVE
    assert "(thick uniform black outlines:1.4)" in wf.STYLE_POSITIVE


def test_style_is_restated_after_the_scene():
    """The suffix is what stops a long prompt diluting the style."""
    graph = wf.background_plate(prompt="A" * 400, width=960, height=1024, seed=1)
    positive = graph["2"]["inputs"]["text"]
    assert positive.startswith(wf.STYLE_POSITIVE)
    assert positive.endswith(wf.STYLE_SUFFIX)


def test_photorealism_is_strongly_negative():
    for term in ("(photorealistic:1.6)", "(photograph:1.6)"):
        assert term in wf.STYLE_NEGATIVE


def test_background_negative_excludes_characters_text_and_borders():
    """A background plate must be frameless, textless and empty of cast."""
    graph = wf.background_plate(prompt="a room", width=960, height=1024, seed=1)
    negative = graph["3"]["inputs"]["text"]
    for term in ("characters", "text", "watermark", "panel border", "speech bubble"):
        assert term in negative, term


def test_default_checkpoint_is_the_one_that_won():
    """Experiment 001: animagine-xl produced incoherent output for this style."""
    graph = wf.background_plate(prompt="x", width=960, height=1024, seed=1)
    assert graph["1"]["inputs"]["ckpt_name"] == wf.SDXL_CHECKPOINT
    assert wf.SDXL_CHECKPOINT == "RealVisXL_V4.0.safetensors"


def test_seed_is_always_explicit():
    """An unreproducible image cannot be iterated on."""
    graph = wf.background_plate(prompt="x", width=960, height=1024, seed=12345)
    assert graph["5"]["inputs"]["seed"] == 12345


# --- graph shape ----------------------------------------------------------

def test_every_builder_produces_a_saveable_graph():
    builders = {
        "background_plate": dict(prompt="x", width=960, height=1024, seed=1),
        "background_from_reference": dict(prompt="x", reference_image="r.png",
                                          width=960, height=1024, seed=1),
        "inpaint_repair": dict(prompt="x", image_name="p.png", mask_name="m.png", seed=1),
    }
    for name, kwargs in builders.items():
        graph = wf.BUILDERS[name](**kwargs)
        classes = {n["class_type"] for n in graph.values()}
        assert "SaveImage" in classes, name
        assert "KSampler" in classes, name
        for node in graph.values():
            assert "class_type" in node and "inputs" in node


def test_reference_workflow_actually_uses_controlnet():
    """The previous system had zero ControlNet nodes. This one must not."""
    graph = wf.background_from_reference(prompt="x", reference_image="r.png",
                                         width=960, height=1024, seed=1)
    classes = {n["class_type"] for n in graph.values()}
    assert "ControlNetLoader" in classes
    assert "SetUnionControlNetType" in classes
    assert "DepthAnythingV2Preprocessor" in classes


def test_api_payload_templates_are_saved():
    assert TEMPLATES.is_dir(), "workflows/comfyui/api_payloads missing"
    for name in ("background_plate", "background_from_reference", "inpaint_repair"):
        path = TEMPLATES / f"{name}.api.json"
        assert path.is_file(), path
        json.loads(path.read_text(encoding="utf-8"))


# --- canon guards in the compositor ---------------------------------------

def test_asymmetric_characters_are_never_mirrored():
    """Iteration 4 mirrored Moodz and moved his blue accent to the wrong eye."""
    from app.services.compositor import NO_FLIP

    for character in ("MZ-CHAR-001", "MZ-CHAR-006", "MZ-CHAR-005"):
        assert character in NO_FLIP, character


def test_compositor_refuses_a_canon_violating_flip(tmp_path):
    from PIL import Image

    from app.services.compositor import (
        GroundPlane, LightContract, Placement, composite_panel,
    )

    plate = tmp_path / "plate.png"
    Image.new("RGB", (400, 400), (20, 20, 20)).save(plate)
    layer = tmp_path / "moodz_00_clean_base.png"
    Image.new("RGBA", (60, 120), (200, 200, 200, 255)).save(layer)

    ground = GroundPlane(horizon_y=100, calib_foot_y=380, calib_height_px=180)
    light = LightContract(key_angle_deg=90, key_color=(255, 255, 255))
    place = Placement("MZ-CHAR-001", layer, centre_x=200, foot_y=370, flip=True)

    _, report = composite_panel(plate, ground, light, [place])
    assert any("CANON" in w for w in report.warnings)
    assert place.flip is False


def test_non_standing_pose_without_offset_is_flagged(tmp_path):
    """Iteration 4 placed a seated NeonBlue as if standing."""
    from PIL import Image

    from app.services.compositor import (
        GroundPlane, LightContract, Placement, composite_panel,
    )

    plate = tmp_path / "plate.png"
    Image.new("RGB", (400, 400), (20, 20, 20)).save(plate)
    layer = tmp_path / "neonblue_27_defeated.png"
    Image.new("RGBA", (60, 120), (200, 200, 200, 255)).save(layer)

    ground = GroundPlane(horizon_y=100, calib_foot_y=380, calib_height_px=180)
    light = LightContract(key_angle_deg=90, key_color=(255, 255, 255))
    place = Placement("MZ-CHAR-005", layer, centre_x=200, foot_y=370)

    _, report = composite_panel(plate, ground, light, [place])
    assert any("STAGING" in w for w in report.warnings)


def test_ground_plane_scale_falls_off_with_depth():
    """A character further from camera must render smaller. This is the maths
    that stops the cast reading as an equal-sized row."""
    from app.services.compositor import GroundPlane

    ground = GroundPlane(horizon_y=430, calib_foot_y=1000, calib_height_px=460)
    near = ground.character_height_at(1000)
    far = ground.character_height_at(700)
    assert near == pytest.approx(460)
    assert far < near
    assert far == pytest.approx(460 * (700 - 430) / (1000 - 430))


def test_feet_above_the_horizon_are_rejected():
    from app.services.compositor import GroundPlane

    ground = GroundPlane(horizon_y=430, calib_foot_y=1000, calib_height_px=460)
    with pytest.raises(ValueError):
        ground.character_height_at(300)


# --- live environment (skipped when ComfyUI is down) ----------------------

@pytest.fixture(scope="module")
def live():
    from app.adapters.comfyui import probe

    report = probe()
    if not report.reachable:
        pytest.skip("ComfyUI not reachable")
    return report


def test_required_checkpoint_is_installed(live):
    assert wf.SDXL_CHECKPOINT in live.checkpoints


def test_required_controlnet_is_installed(live):
    assert wf.CONTROLNET_UNION in live.controlnets


def test_no_unexpected_fallback_model(live):
    """If the checkpoint the locked workflow names disappears, fail loudly
    rather than let ComfyUI substitute something else."""
    assert live.checkpoints, "no checkpoints at all"
    assert wf.SDXL_CHECKPOINT in live.checkpoints, (
        f"locked workflow names {wf.SDXL_CHECKPOINT}, host has {live.checkpoints}"
    )


def test_capabilities_the_pipeline_depends_on(live):
    for capability in ("controlnet", "controlnet_union", "depth_preprocessor",
                       "inpaint", "background_removal", "mask_composite"):
        assert live.capabilities.get(capability), capability
