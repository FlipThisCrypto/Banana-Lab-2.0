"""Measure background-plate reuse across a set of legacy panel images.

Produces the evidence behind `VISUAL_PROBLEMS.md`: how many distinct background
plates a set of panels actually draws on. Reuse is not automatically a defect —
a scene should look like one place — but eight panels sharing one unchanged
plate with no camera move is a pacing problem, not economy.

Method: sample a horizontal band from the upper part of each panel (above the
character row and caption bar in the legacy draft-composite format), reduce it
to a coarse 16x8 RGB signature, and greedily cluster on mean absolute
difference. Deliberately crude: it answers "is this literally the same plate?",
not "are these visually similar?".

Usage:
    python scripts/inventory/analyze_legacy_panels.py <glob> [--threshold 12]
"""

from __future__ import annotations

import argparse
import glob as globmod
import os
import sys

import numpy as np
from PIL import Image

# Fraction of panel height sampled. Skips the top title bar and stops above the
# character-card row used by the legacy draft-composite format.
BAND_TOP = 0.06
BAND_BOTTOM = 0.42


def signature(path: str) -> np.ndarray:
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        band = rgb.crop(
            (0, int(rgb.height * BAND_TOP), rgb.width, int(rgb.height * BAND_BOTTOM))
        ).resize((16, 8))
    return np.asarray(band, dtype=float).ravel()


def cluster(sigs: dict[str, np.ndarray], threshold: float) -> list[list[str]]:
    groups: list[list[str]] = []
    for name, vec in sigs.items():
        for group in groups:
            if np.abs(vec - sigs[group[0]]).mean() < threshold:
                group.append(name)
                break
        else:
            groups.append([name])
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pattern", help="glob for panel images")
    parser.add_argument("--threshold", type=float, default=12.0)
    args = parser.parse_args()

    files = sorted(globmod.glob(args.pattern))
    if not files:
        print(f"no files matched {args.pattern!r}", file=sys.stderr)
        return 1

    sigs = {os.path.basename(f): signature(f) for f in files}
    groups = cluster(sigs, args.threshold)

    print(f"{len(files)} panels -> {len(groups)} distinct background plates\n")
    for group in sorted(groups, key=lambda g: -len(g)):
        print(f"  reuse x{len(group):2d}: {', '.join(sorted(group))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
