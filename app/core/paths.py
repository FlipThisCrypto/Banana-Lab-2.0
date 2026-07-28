"""Repository layout constants.

The filesystem is the source of truth (ADR-001). Every other module resolves
locations through here so that a directory rename is one edit, not a search.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CONFIG = REPO_ROOT / "config"
SCHEMAS = CONFIG / "schemas"
CONFIG_DEFAULTS = CONFIG / "defaults"

DOCS = REPO_ROOT / "docs"

SOURCE_MATERIAL = REPO_ROOT / "source_material"
MANIFESTS = SOURCE_MATERIAL / "manifests"
IMPORTED_CANON = SOURCE_MATERIAL / "imported_canon"
IMPORTED_BIBLES = SOURCE_MATERIAL / "imported_bibles"
VISUAL_REFERENCES = SOURCE_MATERIAL / "visual_references"
HISTORICAL_ISSUES = SOURCE_MATERIAL / "historical_issues"
LEGACY_REFERENCE = SOURCE_MATERIAL / "legacy_reference"

CANON = REPO_ROOT / "canon"
CHARACTERS = REPO_ROOT / "characters"
LOCATIONS = REPO_ROOT / "locations"
PROPS = REPO_ROOT / "props"
ISSUES = REPO_ROOT / "issues"
WORKFLOWS = REPO_ROOT / "workflows"
SCRIPTS = REPO_ROOT / "scripts"
TESTS = REPO_ROOT / "tests"
WORKSPACE = REPO_ROOT / "workspace"
VAULT = REPO_ROOT / "vault"

#: Directories a production step may never write into.
READ_ONLY_TREES = (SOURCE_MATERIAL,)

#: Directories that hold human-approved assets. Overwriting these requires an
#: explicit approval action, never an automated one.
APPROVED_TREES = (
    CHARACTERS / "approved",
    LOCATIONS / "approved",
    PROPS / "approved",
)

#: The external project this repository imports from. Strictly read-only.
LEGACY_FACTORY = Path("I:/MonkeyZoo Comic Strip/Fusion Squad/MonkeyZoo_Comic_Factory")


def issue_dir(issue_slug: str) -> Path:
    return ISSUES / issue_slug


def is_within(path: Path, parent: Path) -> bool:
    """True if `path` is inside `parent`."""
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def assert_safe_write_target(path: Path) -> None:
    """Raise if a write would land somewhere it must never land.

    Guards the two rules that cost the most if broken: never write into imported
    source material, and never write outside the repository.
    """
    resolved = path.resolve()
    for tree in READ_ONLY_TREES:
        if is_within(resolved, tree):
            raise PermissionError(
                f"refusing to write into read-only tree {tree.name}: {resolved}"
            )
    if is_within(resolved, LEGACY_FACTORY):
        raise PermissionError(f"refusing to write into the legacy factory: {resolved}")
    if not is_within(resolved, REPO_ROOT):
        raise PermissionError(f"refusing to write outside the repository: {resolved}")
