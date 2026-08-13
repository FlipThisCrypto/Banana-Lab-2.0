from app.services.lettering_collision import Box, collisions, overlap_area, placement_box


def test_disjoint_boxes_do_not_overlap():
    assert overlap_area(Box(0, 0, 0.2, 0.2), Box(0.5, 0.5, 0.2, 0.2)) == 0.0


def test_face_in_upper_left_zone_is_a_collision():
    face = Box(0.08, 0.06, 0.18, 0.22)
    zone = Box(0.04, 0.05, 0.42, 0.20)
    hits = collisions([("MZ-CHAR-005", face)], [("MZ-CHAR-005", zone)])
    assert hits
    assert hits[0].character_id == "MZ-CHAR-005"


def test_placement_box_is_in_panel_fractions():
    box = placement_box(500, 900, 200, 400, 1000, 1000)
    assert abs(box.x - 0.4) < 1e-6
    assert abs(box.y - 0.5) < 1e-6
    assert abs(box.w - 0.2) < 1e-6
    assert abs(box.h - 0.4) < 1e-6


def test_character_in_the_lower_third_clears_an_upper_zone():
    body = Box(0.30, 0.45, 0.25, 0.50)
    zone = Box(0.04, 0.05, 0.42, 0.20)
    assert collisions([("MZ-CHAR-001", body)], [("caption", zone)]) == []
