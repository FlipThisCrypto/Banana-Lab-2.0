"""Read an issue's production state from disk.

There is no status database. An issue is at the stage its files prove it is at.
This is ADR-001 in practice: delete the tooling and the project still knows
where it stands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.core import paths
from app.domain.pipeline import PIPELINE, Stage, stage_status


@dataclass
class StageState:
    stage: Stage
    status: str
    missing: list[str]
    approved: bool | None  # None when the stage has no human gate


@dataclass
class IssueState:
    slug: str
    title: str
    issue_id: str
    stages: list[StageState]

    @property
    def current_stage(self) -> StageState | None:
        """The first stage that is not complete."""
        for state in self.stages:
            if state.status != "complete":
                return state
        return None

    @property
    def completed_count(self) -> int:
        return sum(1 for s in self.stages if s.status == "complete")

    def blockers(self) -> list[str]:
        """Reasons the pipeline cannot advance past the current stage."""
        reasons: list[str] = []
        current = self.current_stage
        if current is None:
            return reasons
        for dep_key in current.stage.blocked_by:
            dep = next((s for s in self.stages if s.stage.key == dep_key), None)
            if dep and dep.status != "complete":
                reasons.append(f"{current.stage.title} is blocked by incomplete {dep.stage.title}")
            elif dep and dep.stage.human_gate and dep.approved is not True:
                reasons.append(f"{dep.stage.title} awaits human approval")
        return reasons


def _approval_state(issue_path: Path, stage: Stage) -> bool | None:
    """Read a human approval record, if the stage requires one.

    Approval lives in `13_approved/approval-record.yaml` under a per-stage key.
    Absence means not approved. Nothing here can write approval.
    """
    if not stage.human_gate:
        return None
    record = issue_path / "13_approved" / "approval-record.yaml"
    if not record.is_file():
        return False
    try:
        data = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return False
    entry = (data.get("approvals") or {}).get(stage.key)
    return bool(entry and entry.get("approved") is True)


def load_issue(issue_path: Path) -> IssueState:
    bible = issue_path / "02_issue_bible" / "issue-bible.yaml"
    title = issue_path.name
    issue_id = issue_path.name
    if bible.is_file():
        try:
            data = yaml.safe_load(bible.read_text(encoding="utf-8")) or {}
            title = data.get("title", title)
            issue_id = data.get("issue_id", issue_id)
        except yaml.YAMLError:
            pass

    states: list[StageState] = []
    for stage in PIPELINE:
        status, missing = stage_status(issue_path, stage)
        states.append(StageState(stage, status, missing, _approval_state(issue_path, stage)))

    return IssueState(slug=issue_path.name, title=title, issue_id=issue_id, stages=states)


def all_issues() -> list[IssueState]:
    if not paths.ISSUES.is_dir():
        return []
    return [
        load_issue(child)
        for child in sorted(paths.ISSUES.iterdir())
        if child.is_dir() and child.name != "templates"
    ]
