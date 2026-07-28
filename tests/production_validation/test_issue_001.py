"""Validate the real Issue 001 content, not fixtures.

These tests fail if the project's own documents drift out of compliance. They
are marked `production_validation` so they can be deselected when only unit
tests are wanted.
"""

from __future__ import annotations

import csv

import pytest
import yaml

from app.core import paths
from app.services import validation

pytestmark = pytest.mark.production_validation

ISSUE = "issue-001-neonblue-the-last-light-of-summer"
ISSUE_DIR = paths.ISSUES / ISSUE


@pytest.fixture(scope="module")
def script() -> dict:
    path = ISSUE_DIR / "03_script" / "panel-script.yaml"
    if not path.is_file():
        pytest.skip("panel script not present")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def bible() -> dict:
    path = ISSUE_DIR / "02_issue_bible" / "issue-bible.yaml"
    if not path.is_file():
        pytest.skip("issue bible not present")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# --- schema and format -----------------------------------------------------

def test_all_bound_documents_validate():
    results = validation.validate_documents()
    failures = {r.document: [str(f) for f in r.errors] for r in results if not r.ok}
    assert not failures, failures


def test_panel_script_validates():
    result = validation.validate_panel_script(ISSUE_DIR / "03_script" / "panel-script.yaml")
    assert result.ok, [str(f) for f in result.errors]


def test_issue_meets_the_format_standard():
    result = validation.validate_issue_format(ISSUE_DIR)
    assert result.ok, [str(f) for f in result.errors]


def test_panel_ids_are_unique(script):
    ids = [p["panel_id"] for p in script["panels"]]
    assert len(ids) == len(set(ids))


def test_declared_counts_match_reality(script, bible):
    pages = {p["page_number"] for p in script["panels"]}
    assert len(pages) == bible["story_page_count"]
    assert len(script["panels"]) == bible["target_panel_count"]


# --- the integration contract ----------------------------------------------

def test_every_character_in_frame_has_a_staging_record(script):
    """The defect the previous system shipped: characters with no staging."""
    problems = []
    for panel in script["panels"]:
        present = set(panel.get("characters_present") or [])
        staged = {b["character_id"] for b in panel.get("character_blocking") or []}
        if present - staged:
            problems.append((panel["panel_id"], sorted(present - staged)))
    assert not problems, problems


def test_every_staging_record_declares_integration_fields(script):
    """ground_contact, eye_line and scale_note are what QA checks against."""
    problems = []
    for panel in script["panels"]:
        for entry in panel.get("character_blocking") or []:
            for field in ("ground_contact", "eye_line", "scale_note", "depth_plane"):
                if not entry.get(field):
                    problems.append((panel["panel_id"], entry["character_id"], field))
    assert not problems, problems


def test_every_panel_declares_a_light_contract(script):
    problems = []
    for panel in script["panels"]:
        lighting = panel.get("lighting") or {}
        for field in ("key_direction", "key_color", "fill", "contact_shadow"):
            if not lighting.get(field):
                problems.append((panel["panel_id"], field))
    assert not problems, problems


def test_every_panel_has_a_stated_purpose(script):
    """No filler panels."""
    for panel in script["panels"]:
        assert panel.get("narrative_purpose"), panel["panel_id"]
        assert panel.get("visual_beat"), panel["panel_id"]


# --- canon constraints -----------------------------------------------------

def test_dialogue_stays_within_the_balloon_budget(script):
    over = []
    for panel in script["panels"]:
        balloons = panel.get("dialogue") or []
        assert len(balloons) <= 2, f"{panel['panel_id']} has {len(balloons)} balloons"
        for balloon in balloons:
            words = len(balloon["text"].split())
            if words > 15:
                over.append((panel["panel_id"], words))
    assert not over, over


def test_ash_speaks_exactly_once(script):
    lines = [
        b for p in script["panels"] for b in (p.get("dialogue") or [])
        if b["speaker"] == "MZ-CHAR-004"
    ]
    assert len(lines) == 1, f"Ash has {len(lines)} lines"
    assert lines[0]["text"] == "Hope can read warnings."


def test_patch_is_named_exactly_once(script):
    mentions = [
        p["panel_id"] for p in script["panels"]
        for b in (p.get("dialogue") or []) if "Patch" in b["text"]
    ]
    assert len(mentions) == 1, mentions


def test_no_forbidden_invented_specifics(script):
    """Removed from the legacy script; they must not come back."""
    banned = ["thirteen-year-old", "five thousand", "eight rides"]
    hits = [
        (p["panel_id"], term)
        for p in script["panels"]
        for b in (p.get("dialogue") or [])
        for term in banned
        if term in b["text"].lower()
    ]
    assert not hits, hits


def test_exactly_one_echo_segment_panel(script):
    """A hard season constraint: one of six segments, never more."""
    panels = [
        p["panel_id"] for p in script["panels"]
        if "PROP-echo-symbol" in " ".join(p.get("required_source_assets") or [])
        and p["camera_shot"] in ("extreme_close", "insert")
    ]
    assert len(panels) == 1, panels


# --- rhythm ----------------------------------------------------------------

def test_panel_shapes_and_shots_are_varied(script):
    shapes = {p["panel_shape"] for p in script["panels"]}
    shots = {p["camera_shot"] for p in script["panels"]}
    angles = {p["camera_angle"] for p in script["panels"]}
    assert len(shapes) >= 5, shapes
    assert len(shots) >= 8, shots
    assert len(angles) >= 4, angles


def test_the_issue_contains_silent_panels(script):
    silent = [p for p in script["panels"] if not p.get("dialogue")]
    assert len(silent) >= 10, f"only {len(silent)} silent panels"


# --- provenance ------------------------------------------------------------

def test_imported_source_matches_the_manifest():
    checked, problems = validation.validate_manifest()
    assert checked > 0, "manifest present but nothing was checked"
    assert not problems, problems[:10]


def test_manifest_records_authority_for_every_file():
    manifest = paths.MANIFESTS / "source-migration.csv"
    if not manifest.is_file():
        pytest.skip("manifest not present")
    allowed = {
        "authoritative", "approved-reference", "historical-reference",
        "candidate", "superseded", "rejected", "unknown",
    }
    with manifest.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    for row in rows:
        assert row["authority"] in allowed, row["new_path"]
        assert row["sha256"], row["new_path"]


def test_repository_hygiene_is_clean():
    report = validation.validate_hygiene()
    assert not report.suspicious_paths, report.suspicious_paths
    assert not report.large_files, report.large_files
    assert not report.absolute_paths_in_config, report.absolute_paths_in_config


# --- approval --------------------------------------------------------------

def test_no_stage_is_approved_yet():
    """Nothing in this run may have approved anything."""
    record = ISSUE_DIR / "13_approved" / "approval-record.yaml"
    if not record.is_file():
        return
    data = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
    approved = [k for k, v in (data.get("approvals") or {}).items() if v.get("approved")]
    assert not approved, f"unexpected approvals: {approved}"


def test_open_canon_conflicts_are_recorded(bible):
    blocking = [
        c for c in bible.get("canon_conflicts", []) if c.get("requires_owner_decision")
    ]
    assert len(blocking) == 2, [c["conflict_id"] for c in blocking]
