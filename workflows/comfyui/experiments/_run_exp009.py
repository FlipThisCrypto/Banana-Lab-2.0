"""exp009 - prove the likeness gate is wired into the production path.

The metric spent most of its life as a validation script that nothing in the
pipeline called. A panel could be composited with no record of whether its
characters still looked like themselves. This re-stages a real panel on a real
calibrated plate with real approved layers and reads the numbers back out of the
CompositeReport, which is where a panel-approval step would read them.

Writes: workflows/comfyui/experiments/exp009-likeness-in-pipeline/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.services.compositor import (  # noqa: E402
    GroundPlane, LightContract, Placement, composite_panel,
)

PLATE = Path("workflows/comfyui/experiments/exp002-p16-02-plate/"
             "exp002_seed760201.png")
LAYERS = Path("characters/working/repaired_layers")
FALLBACK = Path("source_material/imported_canon/character_layers")
OUT = Path("workflows/comfyui/experiments/exp009-likeness-in-pipeline")


def layer(rel: str) -> Path:
    path = LAYERS / rel
    return path if path.is_file() else FALLBACK / rel


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # school-pa-zone calibration, scaled to this plate's height. The plate is
    # 1216x832 against the calibration's 1280x720, so the vertical values are
    # rescaled rather than reused blind.
    scale_y = 832 / 720
    ground = GroundPlane(
        horizon_y=385 * scale_y,
        calib_foot_y=688 * scale_y,
        calib_height_px=131 * scale_y,
    )
    light = LightContract(
        key_angle_deg=90.0, key_color=(150, 225, 235),
        fill_color=(30, 70, 80), key_strength=0.22, fill_strength=0.10,
        rim_strength=0.10, spill_strength=0.14, protect_neutrals=0.85,
    )

    placements = [
        Placement("MZ-CHAR-005", layer("neonblue/neonblue_16_worried.png"),
                  centre_x=330, foot_y=790, depth_plane="midground"),
        Placement("MZ-CHAR-001", layer("moodz/moodz_00_clean_base.png"),
                  centre_x=760, foot_y=760, depth_plane="midground"),
    ]

    panel, report = composite_panel(PLATE, ground, light, placements)
    panel.convert("RGB").save(OUT / "exp009_panel.png")

    payload = {
        "placements": report.placements,
        "warnings": report.warnings,
        "likeness_passed": report.likeness_passed,
        "worst_likeness": report.worst_likeness,
    }
    (OUT / "exp009_report.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8"
    )

    print(f"panel: {OUT / 'exp009_panel.png'}")
    print(f"{'character':14s}{'layer':30s}{'height':>8s}{'score':>7s}"
          f"{'palette dE':>12s}{'pixel dE':>10s}  verdict")
    for p in report.placements:
        print(f"{p['character_id']:14s}{p['layer']:30s}"
              f"{p['rendered_height_px']:8d}{p['likeness_score']:7.1f}"
              f"{p['likeness_palette_de']:12.2f}{p['likeness_pixel_drift_de']:10.2f}"
              f"  {'PASS' if p['likeness_passed'] else 'FAIL'}")
        for note in p["likeness_notes"]:
            print(f"    - {note}")

    print(f"\npanel likeness passed: {report.likeness_passed}   "
          f"worst {report.worst_likeness:.1f}")
    for warning in report.warnings:
        print(f"  ! {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
