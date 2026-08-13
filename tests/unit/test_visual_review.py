"""Visual review may only reject. A machine cannot pass it."""

from __future__ import annotations

import yaml

from app.services.visual_review import check_review, final_approval_requested


def _write_review(path, **overrides):
    data = {
        "issue_id": "issue-001",
        "standard": "docs/quality/VISUAL_QUALITY_REVIEW.md",
        "verdict": "not_started",
        "actor": "",
        "date": "",
        "viewed_at_print_size": False,
        "five_questions": {
            "eye_goes_where_story_wants": "unanswered",
            "characters_belong_in_the_space": "unanswered",
            "readable_without_dialogue": "unanswered",
            "connected_to_neighbours": "unanswered",
            "nothing_accidentally_generated": "unanswered",
        },
    }
    data.update(overrides)
    (path / "12_qa").mkdir(parents=True)
    (path / "12_qa" / "visual-review.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


def test_missing_review_is_not_a_pass(tmp_path):
    assert check_review(tmp_path) == []
    errors = check_review(tmp_path, final_approval_requested=True)
    assert errors
    assert "missing" in errors[0].message


def test_machine_cannot_write_human_pass(tmp_path):
    _write_review(
        tmp_path,
        verdict="human_pass",
        actor="pipeline",
        date="2026-08-13",
        viewed_at_print_size=True,
        evidence_hash="abc",
        five_questions={
            "eye_goes_where_story_wants": "yes",
            "characters_belong_in_the_space": "yes",
            "readable_without_dialogue": "yes",
            "connected_to_neighbours": "yes",
            "nothing_accidentally_generated": "yes",
        },
    )
    errors = check_review(tmp_path)
    assert any("machine identity" in e.message for e in errors)


def test_scorecard_answers_are_not_a_pass(tmp_path):
    _write_review(
        tmp_path,
        verdict="human_pass",
        actor="pipeline",
        viewed_at_print_size=False,
        five_questions={
            "eye_goes_where_story_wants": "unanswered",
            "characters_belong_in_the_space": "unanswered",
            "readable_without_dialogue": "unanswered",
            "connected_to_neighbours": "unanswered",
            "nothing_accidentally_generated": "unanswered",
        },
    )
    errors = check_review(tmp_path)
    assert len(errors) >= 2


def test_honest_human_pass_is_legal(tmp_path):
    _write_review(
        tmp_path,
        verdict="human_pass",
        actor="FlipThisCrypto",
        date="2026-08-13",
        viewed_at_print_size=True,
        evidence_hash="deadbeef",
        five_questions={
            "eye_goes_where_story_wants": "yes",
            "characters_belong_in_the_space": "yes",
            "readable_without_dialogue": "yes",
            "connected_to_neighbours": "yes",
            "nothing_accidentally_generated": "yes",
        },
        notes="Looked at pages 1-2 at print size.",
    )
    assert check_review(tmp_path) == []


def test_final_approval_flag_reads_the_record(tmp_path):
    approved = tmp_path / "13_approved"
    approved.mkdir()
    (approved / "approval-record.yaml").write_text(
        "approvals:\n  approval:\n    approved: true\n",
        encoding="utf-8",
    )
    assert final_approval_requested(tmp_path) is True
    assert check_review(tmp_path, final_approval_requested=True)
