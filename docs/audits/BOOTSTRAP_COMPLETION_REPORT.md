# Banana Lab 2.0 — Bootstrap Completion Report

**Run date:** 2026-07-28
**Working directory:** `R:\BananaLab2.0`
**Remote:** https://github.com/FlipThisCrypto/Banana-Lab-2.0

---

## Honest status

### `FOUNDATION COMPLETE WITH DOCUMENTED LIMITATIONS`

The foundation is built, committed and pushed. Issue 001 is planned in full
detail through layout and validated against every gate.

**No artwork has been produced. No stage is approved.** Two canon conflicts need
an owner ruling before art production begins, and two production assets do not
exist yet.

Banana Lab 2.0 is **not** production-ready. It will be when Issue 001 has passed
its approval and quality gates, and not before.

---

## 1. Repository

| Property | Value |
|---|---|
| Local path | `R:\BananaLab2.0` |
| Remote | `https://github.com/FlipThisCrypto/Banana-Lab-2.0` |
| Branch | `main` |
| Starting state | Directory empty; remote repository had **no commits** (`isEmpty: true`) |
| Ending state | 204 files tracked, pushed, working tree clean |
| Commit SHA | `ecd8a087cf81627e189b38db8c78e3b59a82e4b5` |
| Commit message | `chore: establish Banana Lab 2.0 production foundation` |
| Push status | **Success** — verified via the GitHub API |
| Working tree | **Clean** — 0 uncommitted entries at commit time |

### Verification

```
gh repo view  -> isEmpty: false, defaultBranchRef: main
gh api .../commits/main -> ecd8a087cf81627e189b38db8c78e3b59a82e4b5
gh api .../git/trees/main?recursive=1 -> 204 blobs
```

Local SHA and remote SHA match. Local tracked count and remote blob count match.

### Large-file findings

**None.** Total staged size **4.04 MB** across 204 files. Largest tracked files:

| File | Size |
|---|---|
| `source_material/manifests/source-migration.json` | 1.32 MB |
| `source_material/manifests/source-migration.csv` | 774 KB |
| `.../04_storyboards/storyboard-contact-sheet.png` | 272 KB |
| `.../03_script/panel-script.yaml` | 206 KB |

The on-disk working directory is **1.7 GB** across 1522 files. The difference is
the imported binary corpus, which is git-ignored and rebuildable from the
manifest.

---

## 2. Source migration

| Measure | Value |
|---|---|
| Source roots inspected | 2 |
| Directories inventoried | Whole factory tree — 6997 files, 4.79 GB |
| Files copied | **1331** |
| Total copied size | **1661.65 MB** |
| Unique files by hash | 1008 |
| Duplicates detected | **323** |
| Hash verification | **60/60 random samples matched; 1331/1331 re-verified by `validate`** |
| Source modified | **No** |

### The source was not touched — proven, not assumed

```
PRE  files: 6997  fingerprint: f981279b4ae9c452379bf01b7ec44755ed7cc427e5d8409de9e78c6ab2d7bb6d
POST files: 6997  fingerprint: f981279b4ae9c452379bf01b7ec44755ed7cc427e5d8409de9e78c6ab2d7bb6d
SOURCE UNCHANGED: True
```

The fingerprint covers every path, size and mtime in the tree. It is identical
before and after. The migration script also refuses structurally, and
`paths.assert_safe_write_target()` raises on any write into `source_material/` or
the legacy factory — both covered by tests.

### By authority

| Authority | Files |
|---|---:|
| `authoritative` | 1008 |
| `approved-reference` | 180 |
| `candidate` | 63 |
| `historical-reference` | 47 |
| `superseded` | 33 |

### Materials intentionally not copied

`06_BACKUPS/` (full factory snapshot), Banana Lab 1.0 application source, the
GENESIS full art set, winter-edition video and audio (~1 GB), legacy hidden
workspaces, and monthly issues outside 001 and Mango Pier. Rationale per item in
`docs/migration/MIGRATION_REPORT.md`.

### Unresolved classifications

Four, all recorded: the 63 character concept renders (imported `candidate`), the
four plate calibrations (their own note calls them art-directed estimates), the
GENESIS material, and Mango Pier's demotion from presumed target to secondary
reference.

---

## 3. Architecture

### Final structure

280 directories. Top level:

```
config/     defaults, schemas, examples, local
docs/       architecture, audits, decisions, migration, production, quality, workflows
source_material/  manifests, imported_canon, imported_bibles, visual_references,
                  historical_issues, legacy_reference
canon/      universe, timelines, continuity, style, rules
characters/ locations/ props/   approved | working | generated_candidates | rejected
issues/     issue-001-neonblue-the-last-light-of-summer (00_brief .. 14_exports), templates
workflows/  comfyui, character, background, compositing, lettering, qa
app/        core, domain, services, adapters, cli, ui
scripts/    bootstrap, migration, inventory, validation, production, utilities
tests/      unit, integration, fixtures, production_validation
workspace/  inbox, active, review, approved, rejected, temp   (git-ignored)
vault/      superseded, failed_experiments, duplicate_material, do_not_use  (git-ignored)
```

### Schemas created — 7

| Schema | Fields | Required |
|---|---:|---:|
| character | 41 | 33 |
| issue | 37 | 34 |
| panel | 36 | 26 |
| location | 19 | 17 |
| expression | 17 | 16 |
| pose | 17 | 16 |
| prop | 13 | 10 |

Every field carries a description — enforced by a test.

### Decisions documented — 5 ADRs

| ADR | Decision |
|---|---|
| 001 | The filesystem is the source of truth |
| 002 | Authoritative and generated assets are strictly separated |
| 003 | The production pipeline comes before the GUI |
| 004 | Backgrounds first, characters composited into them |
| 005 | Human approval gates; machines may only reject |

Plus the owner-mandated `canon/rules/FORMAT_STANDARD.md` and owner-designated
`canon/style/HOUSE_STYLE.md`.

### Validation tools created

| Tool | Purpose |
|---|---|
| `app/core/schema.py` | Schema dialect loader and validator |
| `app/services/validation.py` | Documents, panel scripts, format standard, manifest integrity, hygiene |
| `app/domain/pipeline.py` | 14 stages, evidence requirements, dependency graph |
| `app/services/issue_status.py` | Reads production state from disk |
| `app/adapters/comfyui.py` | Read-only ComfyUI capability probe |
| `scripts/migration/import_source_material.py` | Provenance-recording import |
| `scripts/inventory/analyze_legacy_panels.py` | Background-plate reuse measurement |
| `scripts/production/build_panel_script.py` | Panel script generator |
| `scripts/production/build_layout_spec.py` | Layout generator |
| `scripts/production/render_layout_thumbnails.py` | Thumbnails plus geometry and reading-order validation |
| `scripts/production/build_character_coverage.py` | Asset gap analysis |
| `scripts/production/derive_script_views.py` | Dialogue and visual script views |
| `scripts/utilities/render_edition_pages.py` | Published-edition PDF page renders |

### Application components

CLI with five commands (`status`, `validate`, `schemas`, `comfy`, `dashboard`)
and a static HTML dashboard. Both are views. Neither can approve anything or
advance a stage.

### Deferred deliberately

ComfyUI job submission, style LoRA training, automated compositing, lettering
tooling, export pipeline, any richer GUI. See ADR-003.

---

## 4. Issue 001 — NeonBlue, The Last Light of Summer

### Source materials found

Season bible §7 (the authoritative plan), the Issue 001 story brief, location
and prop tracker, NeonBlue and full-cast character bibles, world bible and
continuity ledger, 417 approved character art files, 372 expression files, **139
true-alpha character layers**, four festival location plates, ten props, the
complete legacy production record, and — supplied by the owner mid-run — three
published Fiend Studios editions plus the collectible stamp.

### Story reconstruction status

**Complete and validated.** Rebuilt to the owner-mandated single-issue format.

| Measure | Value |
|---|---|
| Total pages | 28 |
| Story pages | 22 |
| Panels | 103 |
| Average panels per page | 4.68 |
| Distribution | 4, 6, 5, 5, 6, 4, 7, 5, 6, 5, **1**, 6, 3, 5, 3, 4, 2, 7, 2, 6, 5, 6 |
| Distinct page grids | 22 of 22 |
| Silent panels | 19 |
| Balloons | 103 panels, average 7.1 words, **0 over the 15-word limit** |

### Canon conflicts — 8 found

| ID | Conflict | Status |
|---|---|---|
| C-01 | Echo reveal timing — after the choice, or at the midpoint? | **Owner ruling required** |
| C-02 | Does Lil Devil's interference cause the discovery? | **Owner ruling required** |
| C-03 | Ash's line wording drifted | Resolved |
| C-04 | Invented specifics dating FusionZoo infrastructure | Resolved — removed |
| C-05 | Legacy script 19 panels vs page plan 24 | Resolved |
| C-06 | Scarline had one line and no function | Resolved |
| C-07 | Trapped group anonymous and unrendered | Resolved |
| C-08 | 27-panel draft vs the 20-panel season recommendation | Superseded by the format standard |

### Legacy panels classified — all 24

| Disposition | Panels |
|---|---:|
| KEEP | **0** |
| KEEP_WITH_MINOR_REPAIR | **0** |
| RECOMPOSE | 7 |
| RENDER_NEW_CHARACTERS | 7 |
| RENDER_NEW_BACKGROUND | 0 |
| REBUILD | 4 |
| REMOVE | 6 |

Severity: 6 BLOCKER, 11 CRITICAL, 7 MAJOR. **No legacy panel is approvable.**

Key evidence:
- 19 of 24 panels are self-labelled `DRAFT COMPOSITE` — plates with opaque
  character reference cards pasted in a row.
- 5 are not comic panels at all: a character model sheet, a blurred blob, two
  tiled wallpaper patterns, a pile of monkey heads.
- **Page 2 of the published issue contains no valid artwork.** Page 1 shows five
  off-model pink figures carrying Lil Devil's dialogue.
- Measured background reuse: **24 panels drew on 4 real plates**, the festival
  grounds plate appearing 8 times pixel-identical.
- For every panel ID, **four different images exist** across `selected_panels/`,
  `draft_composites/`, `.art-workspace/attempts/` and the assembled page. Zero
  match by hash.
- The legacy QA report reads `VERDICT: PASS`.

### New layout plan status

**Complete and validated.** 22 distinct grids, no repeats, no overlaps, no
panels escaping the live area, reading order strictly top-to-bottom and
left-to-right on every page. Page frame colours track the issue's light
progression.

A reading-order defect was found and fixed during the build: the generator's
first version varied page shapes by reversing row plans, which resequenced
panels. Page 2 read 6, 4, 5, 2, 3, 1. A permanent check now runs on every build.

### Expression and pose coverage

126 character-in-frame staging records across 103 panels. **100 percent** carry a
declared ground contact, eye line, scale reference and depth plane — enforced by
the panel schema and by a test.

| Character | Panels | Approved alpha layers |
|---|---:|---:|
| NeonBlue | 46 | 17 |
| **Lil Devil** | **17** | **0 — BLOCKER** |
| Static | 15 | 18 |
| TwoTone | 13 | 19 |
| Ash | 13 | 18 |
| Scarline | 12 | 17 |
| Moodz | 10 | 18 |

### Background requirements

47 distinct new assets identified, including 18 new location plate setups, the
page 11 full-page splash plate, three trapped festival-goer figures, a crowd
silhouette set, and prop state variants.

### Production blockers

1. **Owner ruling on C-01** — Echo reveal timing. Affects pages 13, 14 and 22.
2. **Owner ruling on C-02** — Lil Devil's guest function. Affects pages 12, 13
   and 21.
3. **Lil Devil has no true-alpha layer set.** 17 panels.
4. **No festival plate is calibrated.** Character scale has no defensible basis.
5. **The controlled generation test has not been run.**

### Exact next production action

> Calibrate the four festival location plates (horizon, named scale reference,
> light direction and colour, ground surface, traced occluders) to the format in
> `source_material/imported_canon/plate_calibrations/`, and produce the Lil
> Devil true-alpha layer set with RemBG over approved Lil Devil art.

Both are unblocked, independent of the owner rulings, and required by everything
downstream.

---

## 5. ComfyUI

| Property | Value |
|---|---|
| Connection status | **Reachable** at `http://127.0.0.1:8188` |
| Version | 0.19.3 |
| Hardware confirmed | **AMD Radeon RX 6800 via ZLUDA**, 17.2 GB VRAM, 137.4 GB RAM |
| Node types | 1158 |

### Models discovered

| Class | Installed |
|---|---|
| Checkpoints | `RealVisXL_V4.0`, `animagine-xl-4.0` |
| UNet | `z_image_turbo_bf16` |
| VAE | 7 |
| ControlNet | `controlnet-union-sdxl-1.0-promax` |
| IP-Adapter | `ip-adapter-plus_sdxl_vit-h` + CLIP-ViT-H |
| **LoRA** | **0** |
| **Upscale models** | **0** |

### Capabilities confirmed

ControlNet with union type selection, IP-Adapter (incl. FaceID), OpenPose, depth
and canny preprocessors, inpainting, background removal, transparent-background
session, mask compositing, CLIP vision. All present.

### The finding that shaped the plan

**No style LoRA exists, and neither checkpoint produces the MonkeyZoo house
style.** Character identity therefore comes from approved art, never from
text-to-image. This is ADR-004 and the whole production strategy.

### Integration tests performed

**None.** No image was generated in this run.

| Outcome | Count |
|---|---|
| Successful generation outputs | 0 |
| Failed generation outputs | 0 |

Capability discovery only. The adapter is read-only by design.

### Remaining blockers

The controlled single-panel test (`ISSUE001-P16-02`) has not been run. Identity
preservation via IP-Adapter, ControlNet pose transfer onto chibi proportions,
RemBG quality on flat cel-shaded art, generation speed and batch stability are
all **unmeasured**. Plan: `docs/workflows/COMFYUI_INTEGRATION_PLAN.md`.

---

## 6. Tests and validation

### `python -m pytest -q`

```
........................................................                 [100%]
56 passed in 3.67s
```

| Result | Count |
|---|---:|
| Passed | **56** |
| Failed | 0 |
| Skipped | 0 |

| Suite | Tests |
|---|---:|
| `tests/unit/test_schema.py` | 17 |
| `tests/unit/test_pipeline_and_paths.py` | 18 |
| `tests/production_validation/test_issue_001.py` | 21 |

### `python -m app.cli.main validate`

```
== schema validation ==
  [OK] .../02_issue_bible/issue-bible.yaml (issue)

== panel scripts ==
  [OK] .../03_script/panel-script.yaml

== comic format standard ==
  [OK] issue-001-neonblue-the-last-light-of-summer
      [WARNING] page 7: 7 panels, above the soft maximum of 6 - confirm this is intended
      [WARNING] page 18: 7 panels, above the soft maximum of 6 - confirm this is intended

== imported source integrity ==
  1331 files re-hashed against the manifest

== repository hygiene ==
  clean

PASS - 0 problem(s)
```

Both warnings are intentional dense pages, confirmed in the storyboard notes.

### `python scripts/production/render_layout_thumbnails.py`

```
wrote 22 thumbnails
geometry OK: no overlaps, no escapes, no repeated grids
```

### `python -m app.cli.main comfy`

Live probe succeeded. Full output recorded in the capability audit.

---

## 7. Evidence

| Claim | Evidence |
|---|---|
| Source untouched | Fingerprint `f981279b...bb6d` identical pre and post |
| Copies are faithful | 1331 files re-hashed against the manifest by `validate` |
| Legacy art is draft-tier | `01_research/VISUAL_PROBLEMS.md`, `panel-salvage-matrix.csv` |
| Background reuse measured | `scripts/inventory/analyze_legacy_panels.py` — 24 panels, 4 plates |
| Four images per panel ID | `LEGACY_ISSUE_COMPARISON.md` §5, hash comparisons |
| Layout is non-uniform | `04_storyboards/storyboard-contact-sheet.png`, 22 distinct grids |
| Reading order correct | `check_reading_order` passes on all 22 pages |
| Format compliance | `validate_issue_format` passes |
| ComfyUI capability | `docs/workflows/COMFYUI_CAPABILITY_AUDIT.md`, live probe |
| Nothing approved | `test_no_stage_is_approved_yet` passes |

Manifests: `source_material/manifests/source-migration.{csv,json}`.
Contact sheets: `04_storyboards/`.
Git: commit `ecd8a087`, 204 files, clean tree, pushed to `origin/main`.

---

## 8. Definition of success — assessed

| # | Criterion | Status |
|---|---|---|
| 1 | `R:\BananaLab2.0` cleanly structured | **Met** — 280 directories, documented semantics |
| 2 | Old factory untouched | **Met** — fingerprint verified |
| 3 | Approved material copied with provenance | **Met** — 1331 files, hashed, classified |
| 4 | Canon and generated candidates separated | **Met** — ADR-002, enforced by paths and .gitignore |
| 5 | Production workflow documented | **Met** — 14 stages with evidence requirements |
| 6 | Issue 001 has a bible and panel-production plan | **Met** — 28 pages, 103 panels, validated |
| 7 | Layout monotony has a correction strategy | **Met** — 22 distinct grids, enforced by the format standard |
| 8 | Natural character integration has staging and QA requirements | **Met** — 126 staging records, mandatory fields, integration defect class |
| 9 | ComfyUI capabilities documented | **Met** — live audit |
| 10 | Clean first commit and push | **Met** — `ecd8a087`, pushed and verified |
| 11 | Final report proves what was completed | **Met** — this document |
| 12 | Future agents can continue without rediscovery | **Met** — `AGENTS.md`, `CLAUDE.md`, ADRs, this report |

All twelve met.

---

## 9. Limitations

Stated plainly.

1. **No artwork exists.** Issue 001 is planned, not drawn.
2. **Nothing is approved.** No approval record exists, by design.
3. **No image has been generated.** ComfyUI capability is documented; nothing was
   queued.
4. **Generation speed and batch stability are unmeasured.** Do not plan
   schedules against a guess.
5. **Two canon conflicts are open** and need an owner ruling.
6. **Lil Devil has no alpha layer** despite appearing in 17 panels.
7. **No festival plate is calibrated.**
8. **The lettering font is unspecified** — not recorded anywhere in the project,
   including the published editions.
9. **The edition number for the cover stamp is undecided.**
10. **Balloon colour assignment is proposed, not approved.**
11. **Pages 2, 3, 7 and 18** need a human read-through at final size before
    layout approval; automated geometry cannot judge whether a gutter reads as a
    row boundary.
12. **`00_brief` and several stage directories are empty**, correctly — that work
    has not happened.

---

## 10. Conclusion

### `FOUNDATION COMPLETE WITH DOCUMENTED LIMITATIONS`

The foundation is complete: a clean structure, verified provenance for 1331
imported files, seven schemas, an enforced format standard, a documented house
style drawn from the owner's published editions, a 14-stage pipeline with
evidence requirements, quality gates that a wallpaper pattern could not pass, and
56 passing tests — committed and pushed.

Issue 001 is reconstructed to the owner-mandated single-issue format and planned
in full production detail through layout, with every panel carrying a staging
contract that QA can check against.

The limitations are the reason this is not `FOUNDATION COMPLETE`: no artwork
exists, nothing is approved, no image has been generated, and five production
blockers stand between here and the first panel. All are documented above with
the exact next action.

Banana Lab 2.0 is not production-ready, and will not be described as such until
Issue 001 has passed its approval and quality gates.
