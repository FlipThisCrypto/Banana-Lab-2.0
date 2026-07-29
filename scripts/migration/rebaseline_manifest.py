"""Record a deliberate owner revision of imported source material.

THE PROBLEM THIS FIXES
----------------------
`validate` re-hashes every imported file against the migration manifest and
reports any difference. That is correct when the difference is corruption. It is
wrong when the owner has deliberately revised or curated the approved art -
which is a normal, expected thing to do.

On 2026-07-28 that distinction was missing and it cost real work: 81 owner-edited
files were "restored" from the older factory copies, destroying the edits. See
docs/audits/INCIDENT-2026-07-28-source-material-mutation.md.

So: the manifest is a record of what was imported, not a claim that the art can
never change. When the owner changes it, the manifest is re-baselined - the new
state becomes the truth, and the change is recorded rather than reverted.

WHAT THIS IS NOT
----------------
It is not automatic. Nothing calls it during validation or production. Silently
re-baselining on every difference would defeat the entire point of the manifest,
which is to catch changes nobody intended.

Every re-baseline records who did it, when, and why, and keeps the previous
manifest alongside so the change is auditable and reversible.

Usage:
    python scripts/migration/rebaseline_manifest.py --dry-run
    python scripts/migration/rebaseline_manifest.py \
        --actor "Richard" --reason "curated approved_characters to the 15-30 series"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO_ROOT / "source_material" / "manifests"
CSV_PATH = MANIFEST_DIR / "source-migration.csv"
JSON_PATH = MANIFEST_DIR / "source-migration.json"
HISTORY = MANIFEST_DIR / "rebaseline-history.json"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def survey() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Compare the manifest against what is actually on disk."""
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    unchanged: list[dict] = []
    modified: list[dict] = []
    removed: list[dict] = []

    tracked = set()
    for row in rows:
        path = REPO_ROOT / row["new_path"]
        tracked.add(row["new_path"])
        if not path.is_file():
            removed.append(row)
        elif sha256_of(path) != row["sha256"]:
            modified.append(row)
        else:
            unchanged.append(row)

    # Files present in an imported tree but absent from the manifest.
    added: list[dict] = []
    for tree in ("imported_canon", "imported_bibles"):
        root = REPO_ROOT / "source_material" / tree
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(REPO_ROOT).as_posix()
                if rel not in tracked:
                    added.append({"new_path": rel})

    return unchanged, modified, removed, added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--actor", default="", help="who is making this revision")
    parser.add_argument("--reason", default="", help="why the art changed")
    args = parser.parse_args()

    if not CSV_PATH.is_file():
        print(f"no manifest at {CSV_PATH}", file=sys.stderr)
        return 1

    unchanged, modified, removed, added = survey()
    total = len(unchanged) + len(modified) + len(removed)

    print(f"manifest records {total} files")
    print(f"  unchanged {len(unchanged)}")
    print(f"  modified  {len(modified)}")
    print(f"  removed   {len(removed)}")
    print(f"  added     {len(added)} (present on disk, not in the manifest)")

    if not (modified or removed or added):
        print("\nnothing to re-baseline; manifest already matches disk")
        return 0

    for label, items in (("removed", removed), ("modified", modified), ("added", added)):
        if not items:
            continue
        print(f"\n{label}:")
        for item in items[:8]:
            print(f"  {item['new_path']}")
        if len(items) > 8:
            print(f"  ... and {len(items) - 8} more")

    if args.dry_run:
        print("\nDRY RUN - nothing written")
        return 0

    if not args.actor or not args.reason:
        print("\nrefusing to re-baseline without --actor and --reason.", file=sys.stderr)
        print("A revision of approved art is a deliberate act and must be attributable.",
              file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Keep the previous manifest so the change is auditable and reversible.
    archive = MANIFEST_DIR / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    tag = stamp.replace(":", "").replace("-", "")
    shutil.copy2(CSV_PATH, archive / f"source-migration-{tag}.csv")

    # Rewrite: drop removed rows, re-hash modified rows, keep the rest.
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)

    removed_paths = {r["new_path"] for r in removed}
    modified_paths = {r["new_path"] for r in modified}

    kept: list[dict] = []
    for row in rows:
        if row["new_path"] in removed_paths:
            continue
        if row["new_path"] in modified_paths:
            path = REPO_ROOT / row["new_path"]
            row["sha256"] = sha256_of(path)
            row["size_bytes"] = str(path.stat().st_size)
            row["import_date"] = stamp
            row["notes"] = (row.get("notes", "") + f" | rebaselined {stamp}: {args.reason}").strip(" |")
        kept.append(row)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)

    if JSON_PATH.is_file():
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        payload["files"] = kept
        payload.setdefault("summary", {})["files_copied"] = len(kept)
        payload["rebaselined_at"] = stamp
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.is_file() else []
    history.append({
        "at": stamp, "actor": args.actor, "reason": args.reason,
        "modified": len(modified), "removed": len(removed), "added_not_tracked": len(added),
        "files_before": total, "files_after": len(kept),
        "archived_manifest": f"archive/source-migration-{tag}.csv",
        "removed_paths": [r["new_path"] for r in removed],
        "modified_paths": [r["new_path"] for r in modified],
    })
    HISTORY.write_text(json.dumps(history, indent=2), encoding="utf-8")

    print(f"\nre-baselined: {total} -> {len(kept)} tracked files")
    print(f"  previous manifest archived to {archive.name}/source-migration-{tag}.csv")
    print(f"  recorded in {HISTORY.relative_to(REPO_ROOT).as_posix()}")
    print(f"  actor : {args.actor}")
    print(f"  reason: {args.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
