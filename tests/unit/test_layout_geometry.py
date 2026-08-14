"""Shape bands, page-turn locks, and the packer refusing to flip orientation."""

from __future__ import annotations

from app.services.layout_geometry import (
    classify_shape,
    check_page_turn_locks,
    layout_page,
    page_side,
    physical_page,
)


def test_strip_panels_do_not_get_medium_figure_share():
    from scripts.production.run_sample_pages import figure_share

    # 1896x608 is the page-1/2/3 wide strip. Crowd-scale, not 34%.
    assert figure_share("wide", 1896, 608) <= 0.20
    assert figure_share("medium_close", 1192, 968) >= 0.50


def test_wide_staying_landscape_is_ok_or_soft():
    assert classify_shape("wide", 2.4).severity == "ok"
    assert classify_shape("wide", 1.7).severity == "ok"
    assert classify_shape("wide", 1.45).severity == "soft"
    assert classify_shape("wide", 4.5).severity == "soft"


def test_wide_becoming_portrait_is_hard():
    verdict = classify_shape("wide", 0.79)
    assert verdict.severity == "hard"


def test_tall_becoming_landscape_is_hard():
    verdict = classify_shape("tall", 1.10)
    assert verdict.severity == "hard"


def test_square_at_two_and_a_half_is_hard():
    assert classify_shape("square", 2.48).severity == "hard"
    assert classify_shape("square", 1.00).severity == "ok"


def test_rectangle_may_be_portrait_or_landscape():
    assert classify_shape("rectangle", 0.80).severity in {"ok", "soft"}
    assert classify_shape("rectangle", 2.00).severity in {"ok", "soft"}


def test_page_11_is_recto_in_the_28_page_book():
    assert physical_page(11) == 13
    assert page_side(11) == "recto"
    assert page_side(10) == "verso"
    assert check_page_turn_locks() == []


def test_page_11_fails_if_front_matter_shifts_it_to_a_verso():
    problems = check_page_turn_locks(front_matter=1)
    assert problems
    assert "verso" in problems[0]


def test_packer_will_not_return_a_hard_mismatch():
    panels = [
        {"panel_id": "A", "panel_shape": "tall", "relative_panel_size": "medium", "dialogue": []},
        {"panel_id": "B", "panel_shape": "wide", "relative_panel_size": "small", "dialogue": []},
        {"panel_id": "C", "panel_shape": "inset", "relative_panel_size": "small", "dialogue": []},
        {"panel_id": "D", "panel_shape": "rectangle", "relative_panel_size": "medium", "dialogue": []},
        {"panel_id": "E", "panel_shape": "rectangle", "relative_panel_size": "small", "dialogue": []},
    ]
    result = layout_page(4, panels)
    assert result.hard == 0
    assert result.structure_name.startswith("spine")
    by_id = {b["panel_id"]: b for b in result.boxes}
    assert by_id["A"]["actual_aspect"] < 0.90
    assert by_id["B"]["actual_aspect"] > 1.15
