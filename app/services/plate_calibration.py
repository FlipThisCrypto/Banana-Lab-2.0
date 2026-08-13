"""Measure a plate's ground plane instead of guessing it.

The cover stood the cast above the horizon because someone assumed 0.42.
The plate's own buildings met the ground at 0.82. This module is that
lesson as a function: read the pixels, write a calibration, refuse to
invent a floor.

The measurement is a production convention, not a camera solve. Cel-shaded
plates cheat. The number still has to come from the picture, not from a
shot-type table.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from app.core import paths
from app.services.compositor import GroundPlane
from app.services.likeness import srgb_to_lab

#: Search band as a fraction of plate height. Sky-only or footer-only peaks
#: are not the ground line.
SEARCH_TOP = 0.22
#: Leave the last 14% alone — plate_finish vignette lives there and is not the floor.
SEARCH_BOTTOM = 0.86
CENTRE_WIDTH = 0.60


def measure_horizon_fraction(image: Image.Image) -> dict:
    """Row-wise L* profile down the centre strip. Horizon = strongest rise.

    Returns fractions of height, plus the profile so a wrong pick can be
    inspected rather than trusted.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=float)
    height, width, _ = rgb.shape
    x0 = int(width * (0.5 - CENTRE_WIDTH / 2))
    x1 = int(width * (0.5 + CENTRE_WIDTH / 2))
    strip = rgb[:, x0:x1, :]
    lab = srgb_to_lab(strip.reshape(-1, 3)).reshape(height, x1 - x0, 3)
    profile = lab[:, :, 0].mean(axis=1)

    y0 = int(height * SEARCH_TOP)
    y1 = int(height * SEARCH_BOTTOM)
    # Smooth so a single stall awning does not become the horizon.
    k = max(9, (height // 40) | 1)
    kernel = np.ones(k) / float(k)
    smooth = np.convolve(profile, kernel, mode="same")
    grad = np.abs(np.diff(smooth))
    window = grad[y0:y1]
    if window.size == 0:
        frac = 0.55
        peak = y0
    else:
        # Among the strongest few changes, pick the one that actually
        # separates two different lightness bands — not a vignette spike.
        order = np.argsort(window)[::-1][:8]
        best = int(order[0])
        best_sep = -1.0
        band = max(4, height // 30)
        for idx in order:
            row = int(y0 + idx)
            above = float(smooth[max(0, row - band):row].mean()) if row else 0.0
            below = float(smooth[row:min(height, row + band)].mean())
            sep = abs(below - above)
            if sep > best_sep:
                best_sep = sep
                best = row
        peak = best
        frac = peak / height

    frac = min(0.88, max(0.28, float(frac)))
    return {
        "horizon_fraction": round(frac, 4),
        "horizon_px": int(round(frac * height)),
        "peak_row": peak,
        "method": "row_wise_L_star_centre_60_max_positive_gradient",
        "search": [SEARCH_TOP, SEARCH_BOTTOM],
        "mean_L_above": round(float(profile[:peak].mean()) if peak else 0.0, 2),
        "mean_L_below": round(float(profile[peak:].mean()) if peak < height else 0.0, 2),
    }


def build_calibration(
    plate: Path,
    image: Image.Image,
    *,
    panel_id: str = "",
    character_share: float = 0.40,
) -> dict:
    """A GroundPlane-ready record measured from this plate."""
    measured = measure_horizon_fraction(image)
    width, height = image.size
    horizon_f = measured["horizon_fraction"]
    # Standing depth: well below the measured horizon, short of the footer.
    foot_f = min(0.97, max(horizon_f + 0.12, 0.88))
    height_f = character_share
    try:
        plate_ref = plate.resolve().relative_to(paths.REPO_ROOT).as_posix()
    except ValueError:
        plate_ref = plate.as_posix()
    return {
        "panel_id": panel_id or plate.stem.replace("_finished", ""),
        "plate": plate_ref,
        "plate_size": [width, height],
        "source": "MEASURED",
        "derivation_note": (
            "Horizon from the plate's own row-wise L* profile, centre 60%. "
            "Not a camera solve. Not a shot-type guess. Replace only with a "
            "better measurement of THIS plate."
        ),
        "horizon": measured,
        "ground_plane": {
            "horizon_y": int(round(horizon_f * height)),
            "horizon_fraction": horizon_f,
            "calib_foot_y": int(round(foot_f * height)),
            "calib_foot_fraction": round(foot_f, 4),
            "calib_height_px": int(round(height_f * height)),
            "calib_height_fraction": height_f,
            "calib_height_in_characters": 1.0,
            "calib_object": "measured standing depth on this plate",
        },
    }


def ground_from_calibration(calib: dict, size: tuple[int, int]) -> GroundPlane:
    """Rebuild a GroundPlane at the requested pixel size."""
    gp = calib["ground_plane"]
    width, height = size
    horizon_f = gp.get("horizon_fraction")
    foot_f = gp.get("calib_foot_fraction")
    height_f = gp.get("calib_height_fraction")
    if horizon_f is None:
        horizon_f = gp["horizon_y"] / calib["plate_size"][1]
    if foot_f is None:
        foot_f = gp["calib_foot_y"] / calib["plate_size"][1]
    if height_f is None:
        height_f = gp["calib_height_px"] / calib["plate_size"][1]
    return GroundPlane(
        horizon_y=horizon_f * height,
        calib_foot_y=foot_f * height,
        calib_height_px=height_f * height,
        calib_height_in_characters=gp.get("calib_height_in_characters", 1.0),
    )


def calibration_path(issue_dir: Path, panel_id: str) -> Path:
    return issue_dir / "06_backgrounds" / "calibrations" / f"{panel_id}.yaml"


def load_calibration(issue_dir: Path, panel_id: str) -> dict | None:
    path = calibration_path(issue_dir, panel_id)
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def write_calibration(issue_dir: Path, calib: dict) -> Path:
    path = calibration_path(issue_dir, calib["panel_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# Ground-plane calibration for {calib['panel_id']}\n"
        "# MEASURED from the plate. Do not replace with a shot-type guess.\n\n"
    )
    path.write_text(header + yaml.safe_dump(calib, sort_keys=False, width=100), encoding="utf-8")
    return path
