"""Measure ground planes from existing finished plates.

Writes 06_backgrounds/calibrations/<panel>.yaml. Staging reads those instead
of the shot-type guess table.

    python scripts/production/measure_plate_calibrations.py <issue-slug>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from app.services.plate_calibration import build_calibration, write_calibration

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue")
    args = parser.parse_args()
    issue_dir = REPO_ROOT / "issues" / args.issue
    plates = issue_dir / "06_backgrounds" / "generated_candidates"
    if not plates.is_dir():
        print(f"no plates at {plates}", file=sys.stderr)
        return 1

    written = 0
    for plate in sorted(plates.glob("*_finished.png")):
        if "_take" in plate.stem:
            continue
        with Image.open(plate) as image:
            calib = build_calibration(plate, image.convert("RGB"))
        dest = write_calibration(issue_dir, calib)
        print(
            f"  {calib['panel_id']}: horizon {calib['ground_plane']['horizon_fraction']:.3f} "
            f"({calib['horizon']['method'].split('_')[0]})"
        )
        written += 1
        _ = dest
    print(f"wrote {written} calibrations")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
