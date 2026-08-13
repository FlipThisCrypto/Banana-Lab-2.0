"""Detect when a character occupies reserved lettering space.

Lettering is placed in space the artwork reserved. If a face or torso sits in
a bubble zone, the panel fails visual review regardless of likeness score.
This module only rejects. It never moves a balloon and it never approves.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    """Axis-aligned box in panel-fraction coordinates (origin top-left)."""

    x: float
    y: float
    w: float
    h: float

    @property
    def x1(self) -> float:
        return self.x + self.w

    @property
    def y1(self) -> float:
        return self.y + self.h


@dataclass(frozen=True)
class Collision:
    character_id: str
    zone_for: str
    overlap: float
    reason: str


def overlap_area(a: Box, b: Box) -> float:
    w = min(a.x1, b.x1) - max(a.x, b.x)
    h = min(a.y1, b.y1) - max(a.y, b.y)
    if w <= 0 or h <= 0:
        return 0.0
    return w * h


def placement_box(
    centre_x: float,
    foot_y: float,
    rendered_w: float,
    rendered_h: float,
    panel_w: float,
    panel_h: float,
) -> Box:
    """Convert a compositor placement into a panel-fraction box."""
    x = (centre_x - rendered_w / 2.0) / panel_w
    y = (foot_y - rendered_h) / panel_h
    return Box(x, y, rendered_w / panel_w, rendered_h / panel_h)


def collisions(
    characters: list[tuple[str, Box]],
    zones: list[tuple[str, Box]],
    *,
    min_overlap: float = 0.01,
) -> list[Collision]:
    """Report every character box that substantially enters a reserved zone."""
    found: list[Collision] = []
    for character_id, body in characters:
        for owner, zone in zones:
            area = overlap_area(body, zone)
            if area >= min_overlap:
                found.append(
                    Collision(
                        character_id,
                        owner,
                        round(area, 4),
                        f"{character_id} occupies reserved lettering space for {owner}",
                    )
                )
    return found
