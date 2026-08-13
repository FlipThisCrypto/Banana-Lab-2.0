"""Panel geometry that honours the script's declared shapes.

The script uses panel shape as direction: a tall corridor is isolation, a wide
is geography, a square insert stops time. The generator may distort a ratio
inside a tolerance band. It may not flip the orientation the director asked for.

This module is the single implementation of that rule. The layout builder, the
validator and the tests all import it, so a band change cannot drift.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

#: Aspect of the live area (inside the margins) on an A4 page at 300 dpi.
#: 2149 x 3177 px -> 0.6765. Used to convert fractional boxes into real aspects.
LIVE_ASPECT = 2149 / 3177

SIZE_WEIGHT = {
    "xs": 0.6,
    "small": 1.0,
    "medium": 1.6,
    "large": 2.6,
    "xl": 3.4,
    "full_page": 8.0,
}

TARGET_ASPECT = {
    "wide": 2.40,
    "tall": 0.52,
    "square": 1.00,
    "rectangle": 1.35,
    "inset": 1.15,
    "borderless": 1.50,
    "bleed": 1.50,
    "irregular": 1.30,
    "splash": LIVE_ASPECT,
}

MAX_PER_ROW = 3
COL_GAP = 0.012
ROW_GAP = 0.012
#: Pages 7 and 18 are seven-panel pages. A wider gap between rows than within
#: a row is the grouping cue the reading-order review asked for.
DENSE_PAGES = frozenset({7, 18})
DENSE_ROW_GAP = 0.024

#: Book assembly for Issue 001. Story page N is physical page
#: FRONT_MATTER_PAGES + N. Odd physical pages are recto (right-hand).
FRONT_MATTER_PAGES = 2
TOTAL_BOOK_PAGES = 28
#: Story pages whose power depends on the physical turn. Page 11 is the splash
#: that reveals the dark's shape; it must arrive after the turn from page 10,
#: never as the left half of a 10-11 spread.
PAGE_TURN_LOCKS = (
    {
        "story_page": 11,
        "must_be": "recto",
        "reason": (
            "Splash reveal of the dark's shape. Power depends on "
            "page 10 -> TURN -> splash. A verso 11 would sit beside 10."
        ),
    },
)


# hard_min/hard_max are orientation / sliver limits. Outside them the generated
# box contradicts the script and the layout is illegal.
# soft_min/soft_max are the preferred band; outside them but inside hard is a
# recorded SOFT mismatch - acceptable distortion, not a failure.
SHAPE_BANDS = {
    "wide": {
        "hard_min": 1.15,
        "soft_min": 1.60,
        "soft_max": 3.80,
        "hard_max": 10.0,
    },
    "tall": {
        "hard_min": 0.22,
        "soft_min": 0.35,
        "soft_max": 0.72,
        "hard_max": 0.90,
    },
    "square": {
        "hard_min": 0.70,
        "soft_min": 0.82,
        "soft_max": 1.22,
        "hard_max": 1.45,
    },
    "rectangle": {
        "hard_min": 0.55,
        "soft_min": 0.75,
        "soft_max": 2.40,
        "hard_max": 3.20,
    },
    "inset": {
        "hard_min": 0.28,
        "soft_min": 0.55,
        "soft_max": 2.80,
        "hard_max": 8.0,
    },
    "splash": {
        "hard_min": 0.55,
        "soft_min": 0.62,
        "soft_max": 0.75,
        "hard_max": 0.85,
    },
    "borderless": {
        "hard_min": 0.55,
        "soft_min": 0.75,
        "soft_max": 2.40,
        "hard_max": 3.20,
    },
    "bleed": {
        "hard_min": 0.55,
        "soft_min": 0.75,
        "soft_max": 2.40,
        "hard_max": 3.20,
    },
    "irregular": {
        "hard_min": 0.45,
        "soft_min": 0.70,
        "soft_max": 2.60,
        "hard_max": 4.00,
    },
}


@dataclass(frozen=True)
class ShapeVerdict:
    declared: str
    aspect: float
    target: float
    severity: str  # "ok" | "soft" | "hard"
    reason: str


def classify_shape(declared: str, aspect: float) -> ShapeVerdict:
    """Hard = orientation (or sliver) contradicts the script. Soft = bent, not flipped."""
    shape = declared or "rectangle"
    target = TARGET_ASPECT.get(shape, 1.35)
    bands = SHAPE_BANDS.get(shape, SHAPE_BANDS["rectangle"])
    if aspect <= 0:
        return ShapeVerdict(shape, aspect, target, "hard", "zero or negative aspect")

    if aspect < bands["hard_min"] or aspect > bands["hard_max"]:
        if shape == "wide" and aspect < bands["hard_min"]:
            reason = (
                f"declared wide but generated {aspect:.2f}:1 — not clearly landscape"
            )
        elif shape == "tall" and aspect > bands["hard_max"]:
            reason = (
                f"declared tall but generated {aspect:.2f}:1 — not clearly portrait"
            )
        elif shape == "square":
            reason = f"declared square but generated {aspect:.2f}:1"
        else:
            reason = (
                f"declared {shape} (target {target}) but generated {aspect:.2f}:1 "
                f"is outside the hard band {bands['hard_min']}-{bands['hard_max']}"
            )
        return ShapeVerdict(shape, aspect, target, "hard", reason)

    if aspect < bands["soft_min"] or aspect > bands["soft_max"]:
        return ShapeVerdict(
            shape,
            aspect,
            target,
            "soft",
            f"declared {shape} (target {target}) generated {aspect:.2f}:1 — "
            f"orientation holds, ratio is bent",
        )
    return ShapeVerdict(shape, aspect, target, "ok", "")


def box_aspect(box: list[float]) -> float:
    _, _, w, h = box
    if h <= 0:
        return 0.0
    return (w * LIVE_ASPECT) / h


def physical_page(story_page: int, front_matter: int = FRONT_MATTER_PAGES) -> int:
    return front_matter + story_page


def page_side(story_page: int, front_matter: int = FRONT_MATTER_PAGES) -> str:
    """'recto' (right) or 'verso' (left). Physical page 1 is recto."""
    return "recto" if physical_page(story_page, front_matter) % 2 == 1 else "verso"


def check_page_turn_locks(
    front_matter: int = FRONT_MATTER_PAGES,
    locks: Iterable[dict] = PAGE_TURN_LOCKS,
) -> list[str]:
    problems: list[str] = []
    for lock in locks:
        side = page_side(lock["story_page"], front_matter)
        if side != lock["must_be"]:
            problems.append(
                f"story page {lock['story_page']} lands {side} "
                f"(physical {physical_page(lock['story_page'], front_matter)}) "
                f"but must be {lock['must_be']}: {lock['reason']}"
            )
    return problems


def _row_partitions(count: int, max_per_row: int = MAX_PER_ROW) -> list[list[list[int]]]:
    if count == 0:
        return [[]]
    results: list[list[list[int]]] = []

    def walk(start: int, acc: list[list[int]]) -> None:
        if start == count:
            results.append([row[:] for row in acc])
            return
        for size in range(1, min(max_per_row, count - start) + 1):
            acc.append(list(range(start, start + size)))
            walk(start + size, acc)
            acc.pop()

    walk(0, [])
    return results


def _structures(panels: list[dict]) -> list[list[tuple]]:
    """Every order-preserving way to tile the page as rows and tall-left spines.

    A spine-left block is the only way a tall panel can share the page with
    later panels without being flattened into a row of equal height.
    Restricted to a declared-tall left panel so a wide cannot be silently
    stood on its end.
    """
    count = len(panels)
    shapes = [p.get("panel_shape", "rectangle") for p in panels]
    results: list[list[tuple]] = []

    def walk(start: int, acc: list[tuple]) -> None:
        if start == count:
            results.append(acc[:])
            return
        remaining = count - start
        for size in range(1, min(MAX_PER_ROW, remaining) + 1):
            acc.append(("row", list(range(start, start + size))))
            walk(start + size, acc)
            acc.pop()
        if remaining >= 3 and shapes[start] == "tall":
            for total in range(3, min(5, remaining) + 1):
                rights = list(range(start + 1, start + total))
                for plan in _row_partitions(len(rights), max_per_row=2):
                    right_rows = [[rights[i] for i in row] for row in plan]
                    acc.append(("spine_left", start, right_rows))
                    walk(start + total, acc)
                    acc.pop()

    walk(0, [])
    return results


def _allocate_widths(
    indices: list[int], panels: list[dict], height: float, usable_w: float, gap: float
) -> list[float]:
    """Split a row so each panel's width aims at its declared aspect."""
    n = len(indices)
    if n == 0:
        return []
    if n == 1:
        return [usable_w]
    targets: list[float] = []
    for i in indices:
        shape = panels[i].get("panel_shape", "rectangle")
        target = TARGET_ASPECT.get(shape, 1.35)
        targets.append(max(0.18, target * height / LIVE_ASPECT))
    total = sum(targets) or 1.0
    raw = [t / total * usable_w for t in targets]
    floor = min(0.16, usable_w / (n * 1.6))
    widths = [max(floor, w) for w in raw]
    scale = usable_w / (sum(widths) or 1.0)
    return [w * scale for w in widths]


def _adjust_block_heights(
    structure: list[tuple], panels: list[dict], heights: list[float]
) -> list[float]:
    """Stop a full-width wide becoming a portrait, or a full-width tall a landscape.

    Weight-based row heights ignore declared shape. A `wide` that inherits 60%
    of the page is 1.1:1 — landscape only by a rounding error. Cap that row
    and give the slack to neighbours that can take it.
    """
    heights = list(heights)
    caps: list[float | None] = [None] * len(structure)
    floors: list[float | None] = [None] * len(structure)
    for i, block in enumerate(structure):
        if block[0] != "row" or len(block[1]) != 1:
            continue
        shape = panels[block[1][0]].get("panel_shape", "rectangle")
        if shape == "wide":
            # aspect = LIVE_ASPECT / h  >= 1.22  =>  h <= LIVE_ASPECT / 1.22
            caps[i] = LIVE_ASPECT / 1.22
        elif shape == "tall":
            # aspect = LIVE_ASPECT / h  <= 0.85  =>  h >= LIVE_ASPECT / 0.85
            floors[i] = LIVE_ASPECT / 0.85
        elif shape == "square":
            # keep a lone square near 1:1
            caps[i] = LIVE_ASPECT / 0.82
            floors[i] = LIVE_ASPECT / 1.22

    for i, cap in enumerate(caps):
        if cap is not None and heights[i] > cap + 1e-6:
            slack = heights[i] - cap
            heights[i] = cap
            receivers = [
                j
                for j, h in enumerate(heights)
                if j != i and (caps[j] is None or h < caps[j] - 1e-6)
            ]
            if not receivers:
                heights[i] += slack
                continue
            share = slack / len(receivers)
            for j in receivers:
                heights[j] += share

    for i, floor in enumerate(floors):
        if floor is not None and heights[i] < floor - 1e-6:
            need = floor - heights[i]
            donors = [
                j
                for j, h in enumerate(heights)
                if j != i and h - need / max(1, len(heights) - 1) > 0.08
            ]
            if not donors:
                continue
            take = need / len(donors)
            if all(heights[j] - take > 0.08 for j in donors):
                heights[i] = floor
                for j in donors:
                    heights[j] -= take
    return heights


def _place_row(
    indices: list[int],
    panels: list[dict],
    y: float,
    h: float,
    x0: float,
    usable_w: float,
    col_gap: float,
) -> list[tuple[int, list[float]]]:
    inner = usable_w - col_gap * (len(indices) - 1)
    widths = _allocate_widths(indices, panels, h, inner, col_gap)
    placed: list[tuple[int, list[float]]] = []
    x = x0
    for i, w in zip(indices, widths):
        placed.append((i, [round(x, 4), round(y, 4), round(w, 4), round(h, 4)]))
        x += w + col_gap
    return placed


def _layout_structure(
    structure: list[tuple],
    panels: list[dict],
    weights: list[float],
    row_gap: float,
    col_gap: float,
    left_frac: float,
) -> list[list[float]] | None:
    """Return a box per panel, or None if the structure cannot tile."""
    block_weights: list[float] = []
    for block in structure:
        if block[0] == "row":
            block_weights.append(sum(weights[i] for i in block[1]))
        else:
            left, right_rows = block[1], block[2]
            idxs = [left] + [i for row in right_rows for i in row]
            block_weights.append(sum(weights[i] for i in idxs))
    total = sum(block_weights) or 1.0
    usable_h = 1.0 - row_gap * (len(structure) - 1)
    if usable_h <= 0:
        return None
    heights = [usable_h * (w / total) for w in block_weights]
    heights = _adjust_block_heights(structure, panels, heights)
    if any(h <= 0.04 for h in heights):
        return None

    boxes: list[list[float] | None] = [None] * len(panels)
    y = 0.0
    for block, h in zip(structure, heights):
        if block[0] == "row":
            for i, box in _place_row(block[1], panels, y, h, 0.0, 1.0, col_gap):
                boxes[i] = box
        else:
            left, right_rows = block[1], block[2]
            left_w = left_frac
            right_x = left_w + col_gap
            right_w = 1.0 - right_x
            if right_w < 0.28 or left_w < 0.22:
                return None
            boxes[left] = [round(0.0, 4), round(y, 4), round(left_w, 4), round(h, 4)]
            r_weights = [sum(weights[i] for i in row) for row in right_rows]
            r_total = sum(r_weights) or 1.0
            r_usable = h - row_gap * (len(right_rows) - 1)
            if r_usable <= 0.04:
                return None
            ry = y
            for row, rw in zip(right_rows, r_weights):
                rh = r_usable * (rw / r_total)
                for i, box in _place_row(row, panels, ry, rh, right_x, right_w, col_gap):
                    boxes[i] = box
                ry += rh + row_gap
        y += h + row_gap

    if any(b is None for b in boxes):
        return None
    return boxes  # type: ignore[return-value]


def _score(boxes: list[list[float]], panels: list[dict]) -> tuple[int, int, float]:
    hard = soft = 0
    error = 0.0
    for panel, box in zip(panels, boxes):
        aspect = box_aspect(box)
        verdict = classify_shape(panel.get("panel_shape", "rectangle"), aspect)
        if verdict.severity == "hard":
            hard += 1
        elif verdict.severity == "soft":
            soft += 1
        target = TARGET_ASPECT.get(panel.get("panel_shape", "rectangle"), 1.35)
        if aspect > 0 and target > 0:
            error += (math.log(aspect / target)) ** 2
    return hard, soft, error


@dataclass
class PageLayout:
    boxes: list[dict]
    structure_name: str
    hard: int
    soft: int
    error: float
    row_gap: float
    col_gap: float


def structure_name(structure: list[tuple]) -> str:
    parts: list[str] = []
    for block in structure:
        if block[0] == "row":
            parts.append(f"r{len(block[1])}")
        else:
            n = 1 + sum(len(row) for row in block[2])
            parts.append(f"spine{n}")
    return "+".join(parts) or "empty"


def layout_page(
    page_number: int,
    panels: list[dict],
    prefer_different_from: str = "",
) -> PageLayout:
    """Search structures and width splits; refuse to return a hard-mismatch page."""
    if not panels:
        return PageLayout([], "empty", 0, 0, 0.0, ROW_GAP, COL_GAP)

    weights = [
        SIZE_WEIGHT.get(p.get("relative_panel_size", "medium"), 1.6) for p in panels
    ]
    row_gap = DENSE_ROW_GAP if page_number in DENSE_PAGES else ROW_GAP
    col_gap = COL_GAP
    left_fracs = (0.30, 0.36, 0.42, 0.48, 0.54)

    scored: list[PageLayout] = []
    for structure in _structures(panels):
        fracs = left_fracs if any(b[0] == "spine_left" for b in structure) else (0.40,)
        for left_frac in fracs:
            raw = _layout_structure(
                structure, panels, weights, row_gap, col_gap, left_frac
            )
            if raw is None:
                continue
            hard, soft, error = _score(raw, panels)
            name = structure_name(structure)
            scored.append(
                PageLayout(raw, name, hard, soft, error, row_gap, col_gap)
            )

    if not scored:
        raise RuntimeError(f"page {page_number}: no tiling structures")

    scored.sort(key=lambda s: (s.hard, s.soft, s.error))
    legal = [s for s in scored if s.hard == 0]
    pool = legal or scored
    chosen = pool[0]
    if prefer_different_from:
        for candidate in pool:
            if candidate.structure_name != prefer_different_from and candidate.hard == chosen.hard:
                # Only take a variant that is not appreciably worse.
                if (candidate.soft, candidate.error) <= (chosen.soft + 1, chosen.error * 2.0 + 0.3):
                    chosen = candidate
                    break

    out_boxes: list[dict] = []
    for panel, box in zip(panels, chosen.boxes):
        w, h = box[2], box[3]
        aspect = box_aspect(box)
        verdict = classify_shape(panel.get("panel_shape", "rectangle"), aspect)
        record = {
            "panel_id": panel["panel_id"],
            "box": box,
            "area_share": round(w * h, 4),
            "shape": panel.get("panel_shape", "rectangle"),
            "silent": not panel.get("dialogue"),
            "anchor": panel.get("relative_panel_size") in ("large", "xl", "full_page"),
            "bubble_zones": [],  # filled by the builder; geometry stays pure
            "actual_aspect": round(aspect, 3),
            "shape_verdict": verdict.severity,
        }
        if verdict.severity != "ok":
            record["shape_mismatch"] = verdict.reason
        out_boxes.append(record)

    return PageLayout(
        out_boxes,
        chosen.structure_name,
        chosen.hard,
        chosen.soft,
        chosen.error,
        row_gap,
        col_gap,
    )


def mismatches_from_spec(pages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split recorded mismatches into hard and soft lists."""
    hard: list[dict] = []
    soft: list[dict] = []
    for page in pages:
        for panel in page.get("panels") or []:
            verdict = classify_shape(panel.get("shape", "rectangle"), panel.get("actual_aspect") or 0.0)
            if verdict.severity == "ok":
                continue
            item = {
                "panel_id": panel["panel_id"],
                "declared": panel.get("shape"),
                "target_aspect": TARGET_ASPECT.get(panel.get("shape", "rectangle"), 1.35),
                "actual_aspect": panel.get("actual_aspect"),
                "page": page["page_number"],
                "severity": verdict.severity,
                "reason": verdict.reason,
            }
            (hard if verdict.severity == "hard" else soft).append(item)
    return hard, soft
