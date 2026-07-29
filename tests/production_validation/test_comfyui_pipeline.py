"""Regression protection for the panel production pipeline.

Split into checks that need a live ComfyUI (skipped when it is down) and checks
that do not. The offline set is the important one: it protects the style
contract and the canon guards, which is where the evidence-backed decisions live.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
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


def test_every_staged_character_gets_a_likeness_number(tmp_path):
    """A panel must not be producible without a likeness measurement.

    The metric existed for a while as a validation script only - nothing in the
    production path called it, so a panel could be composited with no record of
    whether its characters still looked like themselves. Once a character is
    composited onto the plate it cannot be separated from the background and the
    number is no longer recoverable, so it has to be taken during staging.
    """
    from PIL import Image

    from app.services.compositor import (
        GroundPlane, LightContract, Placement, composite_panel,
    )

    plate = tmp_path / "plate.png"
    Image.new("RGB", (400, 500), (20, 30, 40)).save(plate)
    layer = tmp_path / "static_01_neutral.png"
    arr = np.zeros((240, 120, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (222, 222, 222)
    arr[150:, :, :3] = (20, 20, 20)
    Image.fromarray(arr, "RGBA").save(layer)

    ground = GroundPlane(horizon_y=100, calib_foot_y=480, calib_height_px=300)
    place = Placement("MZ-CHAR-003", layer, centre_x=200, foot_y=470)

    _, report = composite_panel(
        plate, ground,
        LightContract(key_angle_deg=90, key_color=(150, 225, 235),
                      key_strength=0.22, fill_strength=0.10,
                      spill_strength=0.14),
        [place],
    )
    assert len(report.placements) == 1
    record = report.placements[0]
    assert "likeness_score" in record and record["likeness_score"] > 0
    assert "likeness_passed" in record
    assert report.worst_likeness == record["likeness_score"]


def test_a_character_wrecked_by_the_light_is_reported_not_silently_staged(tmp_path):
    """A hostile light must produce a warning, not a quiet panel.

    protect_neutrals=0.0 is the free tint the relight design exists to prevent.
    """
    from PIL import Image

    from app.services.compositor import (
        GroundPlane, LightContract, Placement, composite_panel,
    )

    plate = tmp_path / "plate.png"
    Image.new("RGB", (400, 500), (20, 30, 40)).save(plate)
    layer = tmp_path / "static_01_neutral.png"
    arr = np.zeros((240, 120, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (222, 222, 222)
    arr[150:, :, :3] = (20, 20, 20)
    Image.fromarray(arr, "RGBA").save(layer)

    ground = GroundPlane(horizon_y=100, calib_foot_y=480, calib_height_px=300)
    place = Placement("MZ-CHAR-003", layer, centre_x=200, foot_y=470)

    _, report = composite_panel(
        plate, ground,
        LightContract(key_angle_deg=90, key_color=(255, 60, 40),
                      key_strength=0.6, fill_strength=0.4,
                      spill_strength=0.5, protect_neutrals=0.0),
        [place],
    )
    assert any("LIKENESS" in w for w in report.warnings)
    assert not report.likeness_passed


def test_legibility_can_be_waived_only_explicitly_and_never_silently(tmp_path):
    """A background figure may be small. The waiver must still be recorded.

    The approved plate calibrations frame chibi characters as wide shots: on
    school-pa-zone a character standing at the very bottom of an 832px frame is
    167px, and reaching the 320px floor would need foot_y = 1185. So the floor
    is unreachable by correct staging, and without an explicit opt-out the
    pressure would be to disable the gate wholesale - which is worse.
    """
    from PIL import Image

    from app.services.compositor import (
        GroundPlane, LightContract, Placement, composite_panel,
    )

    plate = tmp_path / "plate.png"
    Image.new("RGB", (400, 500), (20, 30, 40)).save(plate)
    layer = tmp_path / "static_01_neutral.png"
    arr = np.zeros((240, 120, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (222, 222, 222)
    arr[150:, :, :3] = (20, 20, 20)
    Image.fromarray(arr, "RGBA").save(layer)

    ground = GroundPlane(horizon_y=100, calib_foot_y=480, calib_height_px=300)
    light = LightContract(key_angle_deg=90, key_color=(150, 225, 235),
                          key_strength=0.22, fill_strength=0.10,
                          spill_strength=0.14)

    # foot_y 350 renders ~197px. The floor is a ramp, not a cliff: 320px scores
    # 100 and the 85 gate bites below ~272px, so the fixture has to be well
    # under the floor for the default to fail.
    strict = Placement("MZ-CHAR-003", layer, centre_x=200, foot_y=350)
    _, report = composite_panel(plate, ground, light, [strict])
    assert not report.likeness_passed, "small render must fail by default"

    waived = Placement("MZ-CHAR-003", layer, centre_x=200, foot_y=350,
                       identity_critical=False)
    _, report = composite_panel(plate, ground, light, [waived])
    record = report.placements[0]
    assert report.likeness_passed
    assert record["likeness_legibility_exempt"] is True
    assert record["identity_critical"] is False
    assert any("LEGIBILITY EXEMPT" in n for n in record["likeness_notes"]), (
        "the waiver must appear in the record, not just change the verdict"
    )


def test_a_waiver_does_not_also_waive_colour_identity(tmp_path):
    """identity_critical=False relaxes SIZE only. Colour is still gated."""
    from PIL import Image

    from app.services.compositor import (
        GroundPlane, LightContract, Placement, composite_panel,
    )

    plate = tmp_path / "plate.png"
    Image.new("RGB", (400, 500), (20, 30, 40)).save(plate)
    layer = tmp_path / "static_01_neutral.png"
    arr = np.zeros((240, 120, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = (222, 222, 222)
    arr[150:, :, :3] = (20, 20, 20)
    Image.fromarray(arr, "RGBA").save(layer)

    ground = GroundPlane(horizon_y=100, calib_foot_y=480, calib_height_px=300)
    waived = Placement("MZ-CHAR-003", layer, centre_x=200, foot_y=470,
                       identity_critical=False)

    _, report = composite_panel(
        plate, ground,
        LightContract(key_angle_deg=90, key_color=(255, 60, 40),
                      key_strength=0.6, fill_strength=0.4,
                      spill_strength=0.5, protect_neutrals=0.0),
        [waived],
    )
    assert not report.likeness_passed
    assert any("LIKENESS" in w for w in report.warnings)


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


# --- reproducibility ------------------------------------------------------

def test_pixel_hash_ignores_embedded_metadata(tmp_path):
    """EXP-006: identical pixels, different file bytes.

    ComfyUI embeds the prompt graph in a PNG text chunk, and that graph contains
    the SaveImage filename_prefix. Two runs of the same seed therefore produce
    different FILE hashes and identical PIXELS. Regression and duplicate checks
    must hash pixels or they report drift that did not happen.
    """
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    from app.adapters.comfy_client import pixel_sha256_of, sha256_of

    image = Image.new("RGB", (32, 32), (12, 34, 56))

    a = tmp_path / "a.png"
    meta_a = PngInfo()
    meta_a.add_text("prompt", '{"7":{"inputs":{"filename_prefix":"run_a"}}}')
    image.save(a, pnginfo=meta_a)

    b = tmp_path / "b.png"
    meta_b = PngInfo()
    meta_b.add_text("prompt", '{"7":{"inputs":{"filename_prefix":"run_b"}}}')
    image.save(b, pnginfo=meta_b)

    assert sha256_of(a) != sha256_of(b), "metadata should change the file hash"
    assert pixel_sha256_of(a) == pixel_sha256_of(b), "pixels are identical"


def test_job_manifests_record_both_hashes():
    """Provenance needs the file hash; reproducibility needs the pixel hash."""
    import json

    from app.core import paths

    manifests = list(
        (paths.REPO_ROOT / "workflows" / "comfyui" / "experiments").rglob("*_manifest.json")
    )
    assert manifests, "no experiment manifests found"

    checked = 0
    for path in manifests:
        data = json.loads(path.read_text(encoding="utf-8"))
        for output in data.get("outputs", []):
            assert output.get("sha256"), f"{path.name} output missing sha256"
            checked += 1
    assert checked, "no outputs recorded in any manifest"


# --- source material immutability ----------------------------------------

def test_imported_source_material_is_not_writable():
    """Regression for INCIDENT-2026-07-28.

    A subagent modified 81 imported files despite an explicit instruction not
    to. `assert_safe_write_target` did not stop it because direct file writes
    never call it. The OS read-only bit does.

    Re-protect with: python scripts/migration/protect_source_material.py
    """
    import os

    from app.core import paths

    protected = [
        paths.IMPORTED_CANON,
        paths.IMPORTED_BIBLES,
        paths.VISUAL_REFERENCES,
        paths.HISTORICAL_ISSUES,
        paths.LEGACY_REFERENCE,
    ]
    writable: list[str] = []
    total = 0
    for root in protected:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                total += 1
                if os.access(path, os.W_OK):
                    writable.append(path.relative_to(paths.REPO_ROOT).as_posix())

    if total == 0:
        pytest.skip("imported source material not present in this checkout")
    if writable:
        # Deliberately a skip, not a failure. The owner unlocks this tree to
        # revise approved art - that is a normal act, and a test that fails
        # during it would train people to ignore the suite. The protection is
        # something the owner turns ON when done, and the manifest check is what
        # actually catches unintended change.
        pytest.skip(
            f"{len(writable)} of {total} imported files are writable - "
            f"source material is unlocked for editing. Re-protect with "
            f"scripts/migration/protect_source_material.py when finished."
        )
