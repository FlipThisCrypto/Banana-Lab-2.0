"""Copy source material into Banana Lab 2.0 and record provenance.

The source tree is treated as strictly read-only. This script opens source files
for reading only, never writes into the source root, and refuses to run if the
resolved destination would land inside the source root.

Outputs:
    source_material/manifests/source-migration.csv
    source_material/manifests/source-migration.json

Usage:
    python scripts/migration/import_source_material.py [--dry-run] [--plan PATH]
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("PyYAML is required: pip install pyyaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = REPO_ROOT / "config" / "defaults" / "import-plan.yaml"
MANIFEST_DIR = REPO_ROOT / "source_material" / "manifests"

# File types that are safe to commit to Git. Everything else is manifest-only.
GIT_SAFE_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".csv", ".txt", ".toml"}

# Substrings that link a file to a character or an issue, used to populate the
# related_character / related_issue manifest columns.
CHARACTER_TOKENS = {
    "neonblue": "MZ-CHAR-005",
    "moodz": "MZ-CHAR-001",
    "twotone": "MZ-CHAR-002",
    "static": "MZ-CHAR-003",
    "ash": "MZ-CHAR-004",
    "scarline": "MZ-CHAR-006",
    "lil devil": "MZ-CHAR-LILDEVIL",
    "lildevil": "MZ-CHAR-LILDEVIL",
    "clever": "MZ-CHAR-CLEVER",
    "cheeky": "MZ-CHAR-CHEEKY",
    "zombie": "MZ-CHAR-ZOMBIE",
    "super": "MZ-CHAR-SUPER",
    "patch": "MZ-CHAR-PATCH",
    "emo": "MZ-CHAR-EMO",
    "mz-char-001": "MZ-CHAR-001",
    "mz-char-002": "MZ-CHAR-002",
    "mz-char-003": "MZ-CHAR-003",
    "mz-char-004": "MZ-CHAR-004",
    "mz-char-005": "MZ-CHAR-005",
    "mz-char-006": "MZ-CHAR-006",
}

ISSUE_TOKENS = {
    "2026-08-01": "issue-001",
    "2026-08_issue_01": "issue-001",
    "issue-01": "issue-001",
    "issue-001": "issue-001",
    "mango": "issue-mango-pier",
    "2026-07-mango": "issue-mango-pier",
    "2026-09-01": "issue-002",
    "2026-09-02": "issue-genesis-0902",
    "2026-10-01": "issue-003",
    "genesis": "issue-genesis",
}

MANIFEST_FIELDS = [
    "rule_id",
    "original_path",
    "new_path",
    "original_filename",
    "file_type",
    "size_bytes",
    "sha256",
    "import_date",
    "classification",
    "authority",
    "related_character",
    "related_issue",
    "git_safe",
    "duplicate_of",
    "normalization",
    "notes",
]


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def matches_any(rel_posix: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel_posix, pat):
            return True
        # `**/*.png` should also match a file sitting directly in the base dir,
        # where the relative path has no separator for `**/` to consume.
        if pat.startswith("**/") and fnmatch.fnmatch(rel_posix, pat[3:]):
            return True
    return False


def is_excluded(rel_posix: str, excludes: list[str]) -> bool:
    for pat in excludes:
        if fnmatch.fnmatch(rel_posix, pat):
            return True
        # `**/x/**` should also exclude a path that merely contains `/x/`.
        core = pat.strip("*/")
        if core and f"/{core}/" in f"/{rel_posix}/":
            return True
    return False


def detect_character(text: str) -> str:
    lowered = text.lower()
    for token, char_id in CHARACTER_TOKENS.items():
        if token in lowered:
            return char_id
    return ""


def detect_issue(text: str) -> str:
    lowered = text.lower().replace("_", "-")
    for token, issue_id in ISSUE_TOKENS.items():
        if token.replace("_", "-") in lowered:
            return issue_id
    return ""


def rule_root(roots: dict[str, Path], rule: dict) -> Path:
    """Resolve which read-only source root a rule reads from."""
    return roots[rule.get("root", "factory")]


def collect_rule_files(source_root: Path, rule: dict, excludes: list[str]) -> list[Path]:
    base = source_root / rule["source"]
    if not base.exists():
        print(f"  ! MISSING SOURCE: {base}")
        return []

    recursive = rule.get("recursive", True)
    includes = rule["include"]
    found: list[Path] = []

    iterator = base.rglob("*") if recursive else base.glob("*")
    for path in iterator:
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        full_rel = path.relative_to(source_root).as_posix()
        if is_excluded(full_rel, excludes):
            continue
        if not matches_any(rel, includes):
            continue
        found.append(path)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plan = yaml.safe_load(args.plan.read_text(encoding="utf-8"))
    excludes = plan.get("global_excludes", [])

    roots: dict[str, Path] = {"factory": Path(plan["source_root"]).resolve()}
    if plan.get("published_root"):
        roots["published"] = Path(plan["published_root"]).resolve()

    for label, root in roots.items():
        if not root.exists():
            sys.exit(f"BLOCKER: source root {label!r} does not exist: {root}")
        # Refuse to run if we could ever write into a source tree.
        try:
            REPO_ROOT.relative_to(root)
        except ValueError:
            continue
        sys.exit(f"BLOCKER: repository root is inside source root {label!r}. Refusing to run.")

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []
    hash_index: dict[str, str] = {}
    per_rule: dict[str, int] = defaultdict(int)
    copied_bytes = 0
    duplicate_count = 0

    for label, root in roots.items():
        print(f"Source root ({label}): {root}")
    print(f"Destination : {REPO_ROOT}")
    print(f"Mode        : {'DRY RUN' if args.dry_run else 'COPY'}\n")

    for rule in plan["rules"]:
        rule_id = rule["id"]
        source_root = rule_root(roots, rule)
        files = collect_rule_files(source_root, rule, excludes)
        dest_base = REPO_ROOT / rule["dest"]
        source_base = source_root / rule["source"]
        print(f"[{rule_id}] {len(files)} file(s) -> {rule['dest']}")

        for src in files:
            rel = src.relative_to(source_base)
            dst = dest_base / rel
            digest = sha256_of(src)
            size = src.stat().st_size

            duplicate_of = hash_index.get(digest, "")
            if duplicate_of:
                duplicate_count += 1
            else:
                hash_index[digest] = dst.relative_to(REPO_ROOT).as_posix()

            if not args.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                # copy2 preserves mtime; source is only ever opened for reading.
                shutil.copy2(src, dst)
                copied_bytes += size

            hay = f"{src.as_posix()} {rel.as_posix()}"
            rows.append(
                {
                    "rule_id": rule_id,
                    "original_path": str(src),
                    "new_path": dst.relative_to(REPO_ROOT).as_posix(),
                    "original_filename": src.name,
                    "file_type": src.suffix.lower().lstrip(".") or "none",
                    "size_bytes": size,
                    "sha256": digest,
                    "import_date": stamp,
                    "classification": rule.get("classification", "unclassified"),
                    "authority": rule.get("authority", "unknown"),
                    "related_character": detect_character(hay),
                    "related_issue": detect_issue(hay),
                    "git_safe": "yes" if src.suffix.lower() in GIT_SAFE_SUFFIXES else "no",
                    "duplicate_of": duplicate_of,
                    "normalization": "none (byte-for-byte copy)",
                    "notes": (rule.get("notes") or "").strip().replace("\n", " "),
                }
            )
            per_rule[rule_id] += 1

    if args.dry_run:
        print(f"\nDRY RUN: {len(rows)} files would be copied.")
        return 0

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = MANIFEST_DIR / "source-migration.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    by_authority: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    for row in rows:
        by_authority[row["authority"]] += 1
        by_type[row["file_type"]] += 1

    payload = {
        "generated_at": stamp,
        "source_roots": {k: str(v) for k, v in roots.items()},
        "repository_root": str(REPO_ROOT),
        "plan_file": str(args.plan.relative_to(REPO_ROOT)),
        "summary": {
            "files_copied": len(rows),
            "bytes_copied": copied_bytes,
            "megabytes_copied": round(copied_bytes / 1e6, 2),
            "duplicate_files": duplicate_count,
            "unique_hashes": len(hash_index),
            "rules_executed": len(plan["rules"]),
            "by_authority": dict(sorted(by_authority.items())),
            "by_file_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
            "by_rule": dict(sorted(per_rule.items())),
        },
        "files": rows,
    }
    json_path = MANIFEST_DIR / "source-migration.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"\nCopied {len(rows)} files ({copied_bytes / 1e6:.1f} MB)")
    print(f"Duplicates detected by hash: {duplicate_count}")
    print(f"Manifest CSV : {csv_path.relative_to(REPO_ROOT)}")
    print(f"Manifest JSON: {json_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
