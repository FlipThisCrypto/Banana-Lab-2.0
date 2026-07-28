# Source Migration Report

**Executed 2026-07-28** by `scripts/migration/import_source_material.py`, driven
by `config/defaults/import-plan.yaml`.

---

## Result

| Measure | Value |
|---|---|
| Files copied | **1331** |
| Total size | **1661.65 MB** |
| Unique files by hash | 1008 |
| Duplicates detected | **323** |
| Import rules executed | 30 |
| Source roots | 2 |
| **Source modified** | **No** |

---

## The source was not touched

The read-only guarantee was verified, not assumed. The factory tree was
fingerprinted before and after the migration — every file path, size and
modification time, hashed together:

```
PRE  files: 6997  fingerprint: f981279b4ae9c452379bf01b7ec44755ed7cc427e5d8409de9e78c6ab2d7bb6d
POST files: 6997  fingerprint: f981279b4ae9c452379bf01b7ec44755ed7cc427e5d8409de9e78c6ab2d7bb6d
SOURCE UNCHANGED: True
```

The script also refuses structurally: it exits if the repository root resolves
inside either source root, and `app/core/paths.assert_safe_write_target()`
raises on any write into `source_material/` or the legacy factory. Both are
covered by tests.

### Copy verification

60 randomly sampled copies were re-hashed against the manifest immediately after
the run: **0 mismatches**. The full check runs on demand:

```bash
python -m app.cli.main validate     # re-hashes all 1331
```

---

## Source roots

| Root | Path | Purpose |
|---|---|---|
| `factory` | `I:\MonkeyZoo Comic Strip\Fusion Squad\MonkeyZoo_Comic_Factory` | Approved canon, bibles, legacy production |
| `published` | `I:\MonkeyZoo Comic Strip\Fusion Squad` | The three published Fiend Studios editions |

The `published` root was added mid-run when the owner designated the published
editions as the authoritative style target.

---

## By authority

| Authority | Files | What it is |
|---|---:|---|
| `authoritative` | 1008 | Approved canon, bibles, published editions |
| `approved-reference` | 180 | Human-reviewed derivatives — alpha layers, Mango Pier |
| `candidate` | 63 | Per-character concept renders. **Not canon.** |
| `historical-reference` | 47 | Published PDFs, GENESIS, the 1.0 review app |
| `superseded` | 33 | Legacy Issue 001 artwork. Evidence only. |

---

## By rule

| Rule | Files | Authority |
|---|---:|---|
| `canon-characters` | 417 | authoritative |
| `canon-expressions` | 372 | authoritative |
| `character-layers` | 139 | approved-reference |
| `canon-props` | 63 | authoritative |
| `character-concept-art` | 63 | candidate |
| `character-bibles` | 50 | authoritative |
| `canon-locations` | 41 | authoritative |
| `edition-three-winter-pages` | 31 | authoritative |
| `legacy-issue01-panels` | 24 | superseded |
| `mango-pier-panels` | 20 | approved-reference |
| `story-bibles` | 15 | authoritative |
| `legacy-issue01-docs` | 14 | historical-reference |
| `historical-pdfs` | 12 | historical-reference |
| `genesis-docs` | 10 | historical-reference |
| `character-bible-schema` | 9 | historical-reference |
| `legacy-issue01-pages`, `mango-pier-pages` | 8 each | superseded / approved-reference |
| `mango-pier-docs` | 7 | approved-reference |
| `edition-one-fusion-squad` | 6 | authoritative |
| `master-bible` | 5 | authoritative |
| `edition-three-covers`, `plate-calibrations` | 4 each | authoritative / approved-reference |
| `edition-two-defusion-tapes` | 2 | authoritative |
| `edition-stamps`, `emo-edition-4-bible`, `genesis-pdf`, `legacy-html-app`, `legacy-issue01-cover`, `mango-pier-cover`, `character-layer-menu` | 1 each | mixed |

---

## Duplicates

**323 files (24 percent) are byte-identical to another file in the import.**

Almost all sit between `approved_characters/` and `approved_expressions/` — the
same PNGs filed twice under the source project's two organising schemes.

They were **copied, not deduplicated**. The manifest's `duplicate_of` column
records the first path each hash was seen at. The reasoning: the source
project's directory structure is itself information, and collapsing it would
lose the distinction between "this is a character reference" and "this is an
expression reference" even when the bytes match.

Deduplication, if wanted later, is a manifest query rather than a re-import.

---

## Normalisation

**None.** Every file is a byte-for-byte copy; the `normalization` column reads
`none (byte-for-byte copy)` throughout.

One derivative was produced separately, after import:
`scripts/utilities/render_edition_pages.py` renders the three published-edition
PDFs to page images in `_pages/` directories. The PDFs are untouched; the page
images are a convenience derivative and are git-ignored.

---

## Deliberately not copied

| Not copied | Why |
|---|---|
| `06_BACKUPS/` | A full snapshot of the factory. Would have doubled the import. |
| `.git/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` | Caches and history. |
| Banana Lab 1.0 application source | The workflow is being replaced, not ported. ADR-003. |
| GENESIS full art set (~105 PNGs) | The collected PDF and records were taken. Panel art is not needed. |
| `.art-workspace/`, `.qa-workspace/`, `.story-workspace/` | Legacy hidden workspaces. Their *contents* were analysed and the findings recorded in the research documents; the files themselves are not needed. |
| Winter edition videos, audio and archives (~1 GB) | Not production reference. |
| `02_MONTHLY_ISSUES` art for issues other than 001 and Mango Pier | Out of scope for this issue. |

Anything in this list can be added by extending the import plan and re-running.

---

## Unresolved classifications

| Item | Question |
|---|---|
| `character_concepts/` (63 files) | Imported as `candidate`. Some may be approvable; the owner has not ruled. |
| `plate_calibrations/` (4 files) | Imported as `approved-reference`. Their own note says values are *"art-directed estimates, not measured facts"*. Correct authority is arguable. |
| GENESIS material | Imported as `historical-reference`. Its canon standing was never established in the source project. |
| Mango Pier | Was the presumed style target until the owner designated the published editions. Now `approved-reference`, not authoritative. |

---

## Conflicts found during migration

Two rules initially matched zero files because `**/*.png` does not match a file
sitting directly in the base directory — the pattern needs a separator for `**/`
to consume. Fixed in `matches_any()`; the fix is why
`canon-characters` rose from 414 to 417 files and six rules went from empty to
populated.

No conflicts were found in the source content itself. Content conflicts relevant
to Issue 001 are recorded in
`issues/issue-001-*/01_research/CANON_CONFLICTS.md`.

---

## Reproducing

```bash
python scripts/migration/import_source_material.py --dry-run
python scripts/migration/import_source_material.py
```

Idempotent — re-running overwrites the imported copies with identical bytes and
rebuilds both manifests. It cannot write to either source root.

---

## Manifests

| File | Contents |
|---|---|
| `source_material/manifests/source-migration.csv` | One row per file: original path, new path, filename, type, size, SHA-256, import date, classification, authority, related character, related issue, git safety, duplicate-of, normalisation, notes |
| `source_material/manifests/source-migration.json` | The same data plus summary aggregates |

Both are committed. The imported binaries are not — see
`docs/architecture/REPOSITORY_POLICY.md`.
