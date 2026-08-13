"""Human visual-quality review. Machines may only reject.

See docs/quality/VISUAL_QUALITY_REVIEW.md. This module loads the record and
reports why a pass is illegal. It never writes human_pass.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.core.schema import Finding

MACHINE_ACTORS = frozenset(
    {
        "",
        "pipeline",
        "validate",
        "scorecard",
        "aesthetic_loop",
        "likeness",
        "bananalab",
        "comfy",
        "agent",
        "automation",
        "machine",
    }
)

FIVE_KEYS = (
    "eye_goes_where_story_wants",
    "characters_belong_in_the_space",
    "readable_without_dialogue",
    "connected_to_neighbours",
    "nothing_accidentally_generated",
)


def review_path(issue_dir: Path) -> Path:
    return issue_dir / "12_qa" / "visual-review.yaml"


def load_review(issue_dir: Path) -> dict | None:
    path = review_path(issue_dir)
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def check_review(issue_dir: Path, final_approval_requested: bool = False) -> list[Finding]:
    """Reject illegal passes. Absence is not a pass."""
    findings: list[Finding] = []
    data = load_review(issue_dir)
    if data is None:
        if final_approval_requested:
            findings.append(
                Finding(
                    "error",
                    "12_qa/visual-review.yaml",
                    "final approval requires a human visual review; the record is missing",
                )
            )
        return findings

    verdict = data.get("verdict")
    actor = str(data.get("actor") or "").strip()
    questions = data.get("five_questions") or {}

    if verdict == "human_pass":
        if actor.lower() in MACHINE_ACTORS:
            findings.append(
                Finding(
                    "error",
                    "visual_review.actor",
                    f"human_pass cannot be written by {actor!r}; that is a machine identity",
                )
            )
        if not data.get("viewed_at_print_size"):
            findings.append(
                Finding(
                    "error",
                    "visual_review.viewed_at_print_size",
                    "human_pass requires the reviewer to have viewed the pages at print size",
                )
            )
        if not data.get("evidence_hash"):
            findings.append(
                Finding(
                    "error",
                    "visual_review.evidence_hash",
                    "human_pass requires a hash of the pages that were actually looked at",
                )
            )
        for key in FIVE_KEYS:
            if questions.get(key) != "yes":
                findings.append(
                    Finding(
                        "error",
                        f"visual_review.five_questions.{key}",
                        "human_pass requires every one of the five questions to be yes",
                    )
                )
        notes = (data.get("notes") or "").lower()
        if "8/8" in notes and "scorecard" in notes and "only" in notes:
            findings.append(
                Finding(
                    "error",
                    "visual_review.notes",
                    "a scorecard result is not a visual review",
                )
            )

    if verdict == "changes_required" and not (data.get("notes") or "").strip():
        findings.append(
            Finding(
                "error",
                "visual_review.notes",
                "changes_required must say what failed",
            )
        )

    if final_approval_requested and verdict != "human_pass":
        findings.append(
            Finding(
                "error",
                "visual_review.verdict",
                f"final approval requires human_pass; record says {verdict!r}",
            )
        )
    return findings


def final_approval_requested(issue_dir: Path) -> bool:
    record = issue_dir / "13_approved" / "approval-record.yaml"
    if not record.is_file():
        return False
    try:
        data = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return False
    entry = (data.get("approvals") or {}).get("approval") or {}
    return entry.get("approved") is True
