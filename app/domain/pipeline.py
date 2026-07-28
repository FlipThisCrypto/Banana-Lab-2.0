"""The production pipeline: stages, their evidence, and their gates.

A stage is complete when the files that prove it exist - not when somebody says
so. `Stage.required_paths` is that proof. This is the mechanism behind
ADR-005: the pipeline cannot mark itself finished.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Stage:
    key: str
    order: int
    title: str
    purpose: str
    #: Paths, relative to the issue directory, that must exist and be non-empty.
    required_paths: tuple[str, ...] = ()
    #: Directories that must contain at least one file matching the glob.
    required_globs: tuple[tuple[str, str], ...] = ()
    #: True if a human approval record is required before the next stage starts.
    human_gate: bool = False
    blocked_by: tuple[str, ...] = field(default=())


PIPELINE: tuple[Stage, ...] = (
    Stage(
        key="research",
        order=1,
        title="Research",
        purpose="Gather and classify every piece of evidence about the issue before deciding anything.",
        required_paths=(
            "01_research/SOURCE_EVIDENCE.md",
            "01_research/LEGACY_ISSUE_COMPARISON.md",
            "01_research/CANON_CONFLICTS.md",
            "01_research/VISUAL_PROBLEMS.md",
            "01_research/STORY_PROBLEMS.md",
            "01_research/SALVAGEABLE_ELEMENTS.md",
            "01_research/REBUILD_RECOMMENDATION.md",
            "01_research/panel-salvage-matrix.csv",
        ),
    ),
    Stage(
        key="issue_bible",
        order=2,
        title="Issue Bible",
        purpose="Fix the narrative contract: what happens, to whom, and why it matters.",
        required_paths=(
            "02_issue_bible/issue-bible.yaml",
            "02_issue_bible/issue-bible.md",
            "02_issue_bible/continuity-map.md",
            "02_issue_bible/character-arc-map.md",
            "02_issue_bible/location-prop-requirements.md",
            "02_issue_bible/approval-checklist.md",
        ),
        human_gate=True,
        blocked_by=("research",),
    ),
    Stage(
        key="script",
        order=3,
        title="Script",
        purpose="Turn the bible into panels, each with a stated job and enough direction to produce.",
        required_paths=(
            "03_script/full-script.md",
            "03_script/panel-script.yaml",
            "03_script/dialogue-only.md",
            "03_script/visual-only.md",
            "03_script/continuity-check.md",
        ),
        human_gate=True,
        blocked_by=("issue_bible",),
    ),
    Stage(
        key="storyboards",
        order=4,
        title="Storyboards",
        purpose="Thumbnail every page so pacing problems surface before art is made.",
        required_paths=("04_storyboards/storyboard-notes.md",),
        required_globs=(("04_storyboards/page-thumbnails", "*.png"),),
        blocked_by=("script",),
    ),
    Stage(
        key="layouts",
        order=5,
        title="Layouts",
        purpose="Fix panel geometry, reading order and lettering space. No art is approved before this is.",
        required_paths=(
            "05_layouts/layout-spec.yaml",
            "05_layouts/reading-order-validation.md",
            "05_layouts/lettering-safe-zones.md",
        ),
        human_gate=True,
        blocked_by=("storyboards",),
    ),
    Stage(
        key="backgrounds",
        order=6,
        title="Backgrounds",
        purpose="Produce frameless plates with staging specifications, not just pretty scenery.",
        required_globs=(
            ("06_backgrounds/staging-guides", "*.yaml"),
            ("06_backgrounds/approved_candidates", "*.png"),
        ),
        blocked_by=("layouts",),
    ),
    Stage(
        key="character_staging",
        order=7,
        title="Character Staging",
        purpose="Decide, per panel, exactly where each character stands and how they meet the light and ground.",
        required_paths=(
            "07_character_staging/character-coverage.md",
            "07_character_staging/expression-coverage.csv",
            "07_character_staging/pose-coverage.csv",
            "07_character_staging/missing-assets.md",
        ),
        blocked_by=("layouts",),
    ),
    Stage(
        key="character_renders",
        order=8,
        title="Character Rendering",
        purpose="Produce the character layers each panel needs, preserving approved identity.",
        required_globs=(("08_character_renders", "*.png"),),
        blocked_by=("character_staging",),
    ),
    Stage(
        key="composites",
        order=9,
        title="Compositing",
        purpose="Integrate characters into plates with correct scale, contact, shadow and light.",
        required_globs=(("09_composites", "*.png"),),
        blocked_by=("backgrounds", "character_renders"),
    ),
    Stage(
        key="lettering",
        order=10,
        title="Lettering",
        purpose="Place balloons and captions in the reserved zones without covering performance.",
        required_globs=(("10_lettering", "*.png"),),
        blocked_by=("composites",),
    ),
    Stage(
        key="effects",
        order=11,
        title="Effects and Final Integration",
        purpose="Final pass: SFX, glows, grain, page assembly.",
        required_globs=(("11_effects", "*.png"),),
        blocked_by=("lettering",),
    ),
    Stage(
        key="qa",
        order=12,
        title="QA",
        purpose="Run character, panel, page and issue gates and record every defect found.",
        required_paths=("12_qa/qa-report.md", "12_qa/defects.csv"),
        blocked_by=("effects",),
    ),
    Stage(
        key="approval",
        order=13,
        title="Approval",
        purpose="Human sign-off. Never automated.",
        required_paths=("13_approved/approval-record.yaml",),
        human_gate=True,
        blocked_by=("qa",),
    ),
    Stage(
        key="export",
        order=14,
        title="Export",
        purpose="Produce print, web and archive deliverables from approved pages only.",
        required_globs=(("14_exports", "*"),),
        blocked_by=("approval",),
    ),
)

STAGES_BY_KEY = {stage.key: stage for stage in PIPELINE}


def stage_status(issue_path: Path, stage: Stage) -> tuple[str, list[str]]:
    """Return (status, missing_evidence) for one stage.

    status is "complete", "partial" or "not_started".
    """
    missing: list[str] = []
    found = 0
    total = 0

    for rel in stage.required_paths:
        total += 1
        path = issue_path / rel
        if path.is_file() and path.stat().st_size > 0:
            found += 1
        else:
            missing.append(rel)

    for rel_dir, pattern in stage.required_globs:
        total += 1
        directory = issue_path / rel_dir
        if directory.is_dir() and any(
            p.is_file() and p.stat().st_size > 0 for p in directory.glob(pattern)
        ):
            found += 1
        else:
            missing.append(f"{rel_dir}/{pattern}")

    if total == 0:
        return "not_started", missing
    if found == total:
        return "complete", []
    if found == 0:
        return "not_started", missing
    return "partial", missing
