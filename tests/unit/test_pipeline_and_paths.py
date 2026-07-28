"""Pipeline stage evidence, approval gating, and write-target safety."""

from __future__ import annotations

import pytest

from app.core import paths
from app.domain.pipeline import PIPELINE, STAGES_BY_KEY, Stage, stage_status
from app.services import issue_status


# --- pipeline shape --------------------------------------------------------

def test_pipeline_is_ordered_and_unique():
    orders = [s.order for s in PIPELINE]
    assert orders == sorted(orders)
    assert len(set(s.key for s in PIPELINE)) == len(PIPELINE)


def test_every_blocked_by_reference_resolves():
    for stage in PIPELINE:
        for dep in stage.blocked_by:
            assert dep in STAGES_BY_KEY, f"{stage.key} blocked by unknown stage {dep}"


def test_dependencies_point_backwards():
    """A stage cannot depend on one that runs later."""
    for stage in PIPELINE:
        for dep in stage.blocked_by:
            assert STAGES_BY_KEY[dep].order < stage.order


def test_every_stage_declares_evidence():
    for stage in PIPELINE:
        assert stage.required_paths or stage.required_globs, (
            f"{stage.key} has no evidence requirement, so it can never be proven complete"
        )


def test_approval_stage_is_human_gated():
    assert STAGES_BY_KEY["approval"].human_gate
    assert STAGES_BY_KEY["layouts"].human_gate
    assert STAGES_BY_KEY["script"].human_gate
    assert STAGES_BY_KEY["issue_bible"].human_gate


# --- evidence detection ----------------------------------------------------

@pytest.fixture
def stage() -> Stage:
    return Stage(
        key="demo", order=1, title="Demo", purpose="test",
        required_paths=("a/one.md", "a/two.md"),
        required_globs=(("b", "*.png"),),
    )


def test_not_started_when_nothing_exists(tmp_path, stage):
    status, missing = stage_status(tmp_path, stage)
    assert status == "not_started"
    assert len(missing) == 3


def test_partial_when_some_evidence_exists(tmp_path, stage):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "one.md").write_text("x", encoding="utf-8")
    status, missing = stage_status(tmp_path, stage)
    assert status == "partial"
    assert "a/two.md" in missing


def test_complete_only_when_all_evidence_exists(tmp_path, stage):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "one.md").write_text("x", encoding="utf-8")
    (tmp_path / "a" / "two.md").write_text("x", encoding="utf-8")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "p.png").write_bytes(b"\x89PNG")
    status, missing = stage_status(tmp_path, stage)
    assert status == "complete"
    assert missing == []


def test_empty_file_does_not_count_as_evidence(tmp_path, stage):
    """A touched placeholder must not satisfy a gate."""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "one.md").write_text("", encoding="utf-8")
    (tmp_path / "a" / "two.md").write_text("", encoding="utf-8")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "p.png").write_bytes(b"")
    status, _ = stage_status(tmp_path, stage)
    assert status == "not_started"


# --- approval gating -------------------------------------------------------

def test_missing_approval_record_means_not_approved(tmp_path):
    gated = STAGES_BY_KEY["script"]
    assert issue_status._approval_state(tmp_path, gated) is False


def test_stage_without_human_gate_reports_none(tmp_path):
    ungated = STAGES_BY_KEY["research"]
    assert issue_status._approval_state(tmp_path, ungated) is None


def test_approval_requires_explicit_true(tmp_path):
    record = tmp_path / "13_approved"
    record.mkdir()
    (record / "approval-record.yaml").write_text(
        "approvals:\n  script:\n    approved: false\n", encoding="utf-8"
    )
    assert issue_status._approval_state(tmp_path, STAGES_BY_KEY["script"]) is False

    (record / "approval-record.yaml").write_text(
        "approvals:\n  script:\n    approved: true\n", encoding="utf-8"
    )
    assert issue_status._approval_state(tmp_path, STAGES_BY_KEY["script"]) is True


def test_malformed_approval_record_is_not_approved(tmp_path):
    record = tmp_path / "13_approved"
    record.mkdir()
    (record / "approval-record.yaml").write_text("{{{ not yaml", encoding="utf-8")
    assert issue_status._approval_state(tmp_path, STAGES_BY_KEY["script"]) is False


# --- write-target safety ---------------------------------------------------

def test_refuses_to_write_into_source_material():
    with pytest.raises(PermissionError):
        paths.assert_safe_write_target(paths.SOURCE_MATERIAL / "imported_canon" / "x.png")


def test_refuses_to_write_into_the_legacy_factory():
    with pytest.raises(PermissionError):
        paths.assert_safe_write_target(paths.LEGACY_FACTORY / "anything.txt")


def test_refuses_to_write_outside_the_repository(tmp_path):
    with pytest.raises(PermissionError):
        paths.assert_safe_write_target(tmp_path / "escape.txt")


def test_allows_a_normal_repository_target():
    paths.assert_safe_write_target(paths.WORKSPACE / "dashboard.html")


def test_is_within_is_not_fooled_by_sibling_prefixes(tmp_path):
    parent = tmp_path / "assets"
    sibling = tmp_path / "assets_backup"
    parent.mkdir()
    sibling.mkdir()
    assert not paths.is_within(sibling / "f.png", parent)
