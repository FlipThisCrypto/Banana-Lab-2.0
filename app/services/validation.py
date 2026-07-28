"""Project-level validation services.

Three distinct kinds of check, deliberately separated:

* `validate_documents`  - do the YAML documents satisfy their schemas?
* `validate_manifest`   - does every imported file still match its recorded hash?
* `validate_hygiene`    - would committing this repository do something regrettable?

None of these approve anything. They can only reject. See ADR-005.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.core import paths
from app.core.schema import Finding, SchemaRegistry, ValidationResult

#: Documents in the project mapped to the schema they must satisfy.
DOCUMENT_BINDINGS: tuple[tuple[str, str], ...] = (
    ("issues/*/02_issue_bible/issue-bible.yaml", "issue"),
    ("characters/approved/*/character.yaml", "character"),
    ("characters/working/*/character.yaml", "character"),
    ("locations/approved/*/location.yaml", "location"),
    ("locations/working/*/location.yaml", "location"),
    ("props/approved/*/prop.yaml", "prop"),
    ("props/working/*/prop.yaml", "prop"),
)

#: Files above this size are flagged before they can be committed by accident.
LARGE_FILE_BYTES = 25 * 1024 * 1024


@dataclass
class HygieneReport:
    large_files: list[tuple[str, int]]
    suspicious_paths: list[str]
    absolute_paths_in_config: list[tuple[str, str]]

    @property
    def ok(self) -> bool:
        return not (self.large_files or self.suspicious_paths or self.absolute_paths_in_config)


def registry() -> SchemaRegistry:
    return SchemaRegistry(paths.SCHEMAS)


def validate_documents(repo: Path | None = None) -> list[ValidationResult]:
    """Validate every bound document against its schema."""
    repo = repo or paths.REPO_ROOT
    reg = registry()
    results: list[ValidationResult] = []
    by_schema: dict[str, list[tuple[str, dict]]] = {}

    for pattern, schema_id in DOCUMENT_BINDINGS:
        if schema_id not in reg:
            continue
        for path in sorted(repo.glob(pattern)):
            try:
                doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                result = ValidationResult(str(path.relative_to(repo)), schema_id)
                result.findings.append(Finding("error", "<file>", f"YAML parse error: {exc}"))
                results.append(result)
                continue
            name = path.relative_to(repo).as_posix()
            results.append(reg[schema_id].validate(doc, name))
            by_schema.setdefault(schema_id, []).append((name, doc))

    # Identity uniqueness is a cross-document property, checked once per schema.
    for schema_id, docs in by_schema.items():
        findings = reg.check_identity_uniqueness(schema_id, docs)
        if findings:
            result = ValidationResult(f"<{schema_id} library>", schema_id)
            result.findings.extend(findings)
            results.append(result)

    return results


def validate_panel_script(script_path: Path) -> ValidationResult:
    """Validate a panel script: every panel against the panel schema, plus IDs."""
    reg = registry()
    schema = reg["panel"]
    name = script_path.name
    result = ValidationResult(name, "panel")

    if not script_path.is_file():
        result.findings.append(Finding("error", "<file>", "panel script not found"))
        return result

    try:
        data = yaml.safe_load(script_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        result.findings.append(Finding("error", "<file>", f"YAML parse error: {exc}"))
        return result

    panels = data.get("panels", [])
    if not panels:
        result.findings.append(Finding("error", "panels", "no panels defined"))
        return result

    seen: dict[str, int] = {}
    for index, panel in enumerate(panels):
        sub = schema.validate(panel, f"{name}#panel[{index}]")
        for finding in sub.findings:
            result.findings.append(
                Finding(finding.severity, f"panels[{index}].{finding.path}", finding.message)
            )
        if not isinstance(panel, dict):
            continue

        panel_id = panel.get("panel_id")
        if panel_id:
            if panel_id in seen:
                result.findings.append(
                    Finding(
                        "error",
                        f"panels[{index}].panel_id",
                        f"duplicate panel id {panel_id!r} (first seen at index {seen[panel_id]})",
                    )
                )
            else:
                seen[panel_id] = index

        result.findings.extend(_check_blocking_coverage(panel, index))

    return result


def _check_blocking_coverage(panel: dict, index: int) -> list[Finding]:
    """Every character in frame must have a staging record.

    The schema cannot express this: both fields are individually optional,
    because inserts and establishing shots legitimately have no cast. But a
    panel that names a character and does not say where they stand cannot be
    QA'd for scale, ground contact or eye line - which is the exact defect the
    previous system shipped.
    """
    present = panel.get("characters_present") or []
    if not present:
        return []

    blocking = panel.get("character_blocking") or []
    if not blocking:
        return [
            Finding(
                "error",
                f"panels[{index}].character_blocking",
                f"{len(present)} character(s) in frame but no staging record",
            )
        ]

    staged = {
        entry.get("character_id")
        for entry in blocking
        if isinstance(entry, dict)
    }
    findings = []
    for character in present:
        if character not in staged:
            findings.append(
                Finding(
                    "error",
                    f"panels[{index}].character_blocking",
                    f"{character} is in frame but has no staging record",
                )
            )
    for character in staged - set(present):
        if character:
            findings.append(
                Finding(
                    "warning",
                    f"panels[{index}].character_blocking",
                    f"{character} is staged but not listed in characters_present",
                )
            )
    return findings


def load_format_standards() -> dict:
    """Read the owner-mandated comic format standard."""
    path = paths.CONFIG_DEFAULTS / "format-standards.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate_issue_format(issue_dir: Path) -> ValidationResult:
    """Check an issue against the owner-mandated format standard.

    Page counts, panel counts and rhythm. See canon/rules/FORMAT_STANDARD.md.
    """
    name = issue_dir.name
    result = ValidationResult(name, "format")

    standards = load_format_standards()
    if not standards:
        result.findings.append(
            Finding("error", "<config>", "config/defaults/format-standards.yaml not found")
        )
        return result

    bible_path = issue_dir / "02_issue_bible" / "issue-bible.yaml"
    script_path = issue_dir / "03_script" / "panel-script.yaml"
    if not bible_path.is_file() or not script_path.is_file():
        return result  # nothing to check yet; stage gates handle absence

    try:
        bible = yaml.safe_load(bible_path.read_text(encoding="utf-8")) or {}
        script = yaml.safe_load(script_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        result.findings.append(Finding("error", "<file>", f"YAML parse error: {exc}"))
        return result

    format_key = bible.get("format", "single_issue")
    spec = (standards.get("formats") or {}).get(format_key)
    if not spec:
        result.findings.append(
            Finding("error", "format", f"unknown format {format_key!r}")
        )
        return result

    # --- page counts -------------------------------------------------------
    total_pages = bible.get("page_count")
    story_pages = bible.get("story_page_count")

    limits = spec["total_pages"]
    if isinstance(total_pages, int) and not (limits["min"] <= total_pages <= limits["max"]):
        result.findings.append(
            Finding(
                "error",
                "page_count",
                f"{total_pages} total pages outside {format_key} range "
                f"{limits['min']}-{limits['max']}",
            )
        )

    limits = spec["story_pages"]
    if story_pages is None:
        result.findings.append(
            Finding("error", "story_page_count", "issue bible does not declare story_page_count")
        )
    elif not (limits["min"] <= story_pages <= limits["max"]):
        result.findings.append(
            Finding(
                "error",
                "story_page_count",
                f"{story_pages} story pages outside {format_key} range "
                f"{limits['min']}-{limits['max']}",
            )
        )

    # --- panel counts ------------------------------------------------------
    panels = script.get("panels") or []
    if not panels:
        return result

    per_page: dict[int, int] = {}
    for panel in panels:
        if isinstance(panel, dict) and isinstance(panel.get("page_number"), int):
            per_page[panel["page_number"]] = per_page.get(panel["page_number"], 0) + 1

    if not per_page:
        return result

    pmin = spec["panels_per_page"]["min"]
    pmax = spec["panels_per_page"]["max"]
    soft = spec["panels_per_page"].get("soft_max", pmax)
    target = spec["panels_per_page"]["average_target"]
    tolerance = spec["panels_per_page"]["average_tolerance"]

    for page in sorted(per_page):
        count = per_page[page]
        if count < pmin:
            result.findings.append(
                Finding("error", f"page {page}", f"{count} panels, below minimum {pmin}")
            )
        elif count > pmax:
            result.findings.append(
                Finding("error", f"page {page}", f"{count} panels, above maximum {pmax}")
            )
        elif count > soft:
            result.findings.append(
                Finding(
                    "warning",
                    f"page {page}",
                    f"{count} panels, above the soft maximum of {soft} - confirm this is intended",
                )
            )

    average = len(panels) / len(per_page)
    if abs(average - target) > tolerance:
        result.findings.append(
            Finding(
                "error",
                "panels_per_page",
                f"issue average {average:.2f} outside {target} +/- {tolerance}",
            )
        )

    # Story page count must agree with what the script actually covers.
    if story_pages is not None and len(per_page) != story_pages:
        result.findings.append(
            Finding(
                "error",
                "story_page_count",
                f"bible declares {story_pages} story pages, script covers {len(per_page)}",
            )
        )

    declared_panels = bible.get("target_panel_count")
    if isinstance(declared_panels, int) and declared_panels != len(panels):
        result.findings.append(
            Finding(
                "error",
                "target_panel_count",
                f"bible declares {declared_panels} panels, script contains {len(panels)}",
            )
        )

    result.findings.extend(_check_rhythm(standards.get("rhythm") or {}, per_page, issue_dir))
    return result


def _check_rhythm(rules: dict, per_page: dict[int, int], issue_dir: Path) -> list[Finding]:
    """Variety rules. An average of 5 hit by putting 5 on every page is the defect."""
    findings: list[Finding] = []
    counts = [per_page[p] for p in sorted(per_page)]

    if rules.get("require_panel_count_variety"):
        distinct = len(set(counts))
        needed = rules.get("min_distinct_panel_counts", 4)
        if distinct < needed:
            findings.append(
                Finding(
                    "error",
                    "rhythm",
                    f"only {distinct} distinct panel counts across the issue, need {needed}",
                )
            )

    limit = rules.get("max_consecutive_pages_same_count")
    if limit:
        run = 1
        for i in range(1, len(counts)):
            run = run + 1 if counts[i] == counts[i - 1] else 1
            if run > limit:
                findings.append(
                    Finding(
                        "error",
                        "rhythm",
                        f"{run} consecutive pages with {counts[i]} panels, limit is {limit}",
                    )
                )
                break

    if rules.get("require_at_least_one_splash") and 1 not in counts:
        findings.append(Finding("error", "rhythm", "no splash page (1 panel) in the issue"))

    if rules.get("require_at_least_one_dense_page") and not any(c >= 7 for c in counts):
        findings.append(Finding("error", "rhythm", "no dense page (7+ panels) in the issue"))

    if rules.get("no_repeated_grid_on_consecutive_pages"):
        spec_path = issue_dir / "05_layouts" / "layout-spec.yaml"
        if spec_path.is_file():
            try:
                spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                spec = {}
            grids = [p.get("grid_name") for p in spec.get("pages") or []]
            for i in range(1, len(grids)):
                if grids[i] and grids[i] == grids[i - 1]:
                    findings.append(
                        Finding(
                            "error",
                            "rhythm",
                            f"pages {i} and {i + 1} share grid {grids[i]!r}",
                        )
                    )
    return findings


def validate_manifest(repo: Path | None = None) -> tuple[int, list[str]]:
    """Re-hash imported files and report any that drifted from the manifest.

    Returns (files_checked, problems).
    """
    repo = repo or paths.REPO_ROOT
    manifest = repo / "source_material" / "manifests" / "source-migration.csv"
    if not manifest.is_file():
        return 0, ["source-migration.csv not found - run the migration script"]

    problems: list[str] = []
    checked = 0
    with manifest.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            path = repo / row["new_path"]
            if not path.is_file():
                problems.append(f"MISSING  {row['new_path']}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            checked += 1
            if digest != row["sha256"]:
                problems.append(f"CHANGED  {row['new_path']}")
    return checked, problems


def validate_hygiene(repo: Path | None = None) -> HygieneReport:
    """Look for things that should not reach a commit."""
    repo = repo or paths.REPO_ROOT
    large: list[tuple[str, int]] = []
    suspicious: list[str] = []
    absolute: list[tuple[str, str]] = []

    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache", ".ruff_cache"}
    secret_names = {".env", "credentials.json", "secrets.yaml", "id_rsa"}
    secret_suffixes = {".key", ".pem", ".pfx", ".safetensors", ".ckpt"}

    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if skip_dirs & set(path.parts):
            continue
        rel = path.relative_to(repo).as_posix()

        if path.name in secret_names or path.suffix in secret_suffixes:
            suspicious.append(rel)

        # Only flag size for files that are actually tracked-eligible; the
        # migration deliberately imports large binaries that .gitignore excludes.
        if not rel.startswith(("source_material/", "workspace/", "vault/")):
            size = path.stat().st_size
            if size > LARGE_FILE_BYTES:
                large.append((rel, size))

    # Runtime config must not hard-code machine-specific drive paths.
    for path in sorted((repo / "config").rglob("*.yaml")):
        rel = path.relative_to(repo).as_posix()
        if rel.startswith("config/defaults/import-plan.yaml"):
            continue  # the import plan legitimately points at the source machine
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if ":\\" in stripped or ":/" in stripped and stripped.split(":/")[0][-1:].isalpha():
                if any(f"{drive}:" in stripped for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ"):
                    absolute.append((rel, f"line {line_no}: {stripped[:80]}"))

    return HygieneReport(sorted(large), sorted(suspicious), absolute)
