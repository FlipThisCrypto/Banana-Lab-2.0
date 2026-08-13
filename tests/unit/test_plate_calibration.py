from pathlib import Path

import numpy as np
from PIL import Image

from app.services.plate_calibration import (
    build_calibration,
    ground_from_calibration,
    measure_horizon_fraction,
)


def _sky_over_ground(height: int = 200, width: int = 160) -> Image.Image:
    """Dark sky, bright ground. Horizon at mid-frame."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[: height // 2] = (30, 40, 70)
    arr[height // 2 :] = (180, 160, 90)
    return Image.fromarray(arr, "RGB")


def test_horizon_is_read_from_the_picture_not_guessed():
    measured = measure_horizon_fraction(_sky_over_ground())
    assert 0.42 < measured["horizon_fraction"] < 0.58
    assert measured["mean_L_below"] > measured["mean_L_above"]


def test_existing_cover_calibration_is_repo_relative():
    from app.core import paths

    path = (
        paths.ISSUES
        / "issue-001-neonblue-the-last-light-of-summer"
        / "06_backgrounds"
        / "calibrations"
        / "ISSUE001-COVER.yaml"
    )
    if not path.is_file():
        return
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert not data["plate"].startswith("R:")
    assert data["plate"].startswith("issues/")


def test_feet_sit_below_the_measured_horizon(tmp_path):
    plate = tmp_path / "ISSUE001-P01-01_finished.png"
    image = _sky_over_ground()
    image.save(plate)
    calib = build_calibration(plate, image, panel_id="ISSUE001-P01-01")
    ground = ground_from_calibration(calib, (160, 200))
    assert ground.calib_foot_y > ground.horizon_y
    assert ground.character_height_at(ground.calib_foot_y) > 0
    # A standing figure at the old 0.42 guess would be ABOVE this horizon.
    try:
        ground.character_height_at(0.42 * 200)
        raised = True
    except ValueError:
        raised = False
    assert raised is False
