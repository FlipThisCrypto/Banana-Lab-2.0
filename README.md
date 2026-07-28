# Banana Lab 2.0

A structured comic-production system for **MonkeyZoo**.

Not an image generator. Not an art GUI. A pipeline that takes a story from canon
to a finished, approved, exportable comic — with the quality gates that were
missing the first time.

---

## The problem it solves

The previous system shipped an issue that had never been drawn.

Legacy Issue 001 was marked `published` with owner approvals recorded at every
stage and a QA report reading `VERDICT: PASS`. Its artwork consisted of
background plates with opaque character reference cards pasted in a row, plus
five images that were not comic panels at all — a character model sheet, a
blurred blob, two tiled wallpaper patterns, and a pile of monkey heads. Page 2
of the published issue contains no valid artwork. Page 1 shows five off-model
pink figures carrying Lil Devil's dialogue.

The QA gate that passed it checked file existence, format and dimensions. That
is all. A wallpaper pattern passes that test.

Full evidence: `issues/issue-001-*/01_research/VISUAL_PROBLEMS.md`.

Banana Lab 2.0 is built so that cannot happen again.

---

## Current status

**Foundation complete. Issue 001 is planned through layout. No artwork has been
produced.**

| Area | State |
|---|---|
| Directory structure and repository policy | Complete |
| Source migration — 1331 files, 1.66 GB, hashed | Complete, verified |
| Schemas — character, expression, pose, location, prop, issue, panel | Complete |
| Comic format standard, owner-mandated | Complete and enforced |
| House style, owner-designated | Documented |
| Issue 001 research and salvage analysis | Complete |
| Issue 001 bible, script, storyboards, layouts | Drafted, awaiting owner approval |
| ComfyUI capability audit | Complete, live probe |
| Validation tooling and CLI | Working |
| Issue 001 artwork | **Not started** |

Two canon conflicts need an owner ruling before art production begins. See
`issues/issue-001-*/01_research/CANON_CONFLICTS.md`.

---

## The production workflow

```
Project Canon
    -> Character Library
    -> Location and Prop Libraries
    -> Issue Bible
    -> Panel Script
    -> Page Layout and Thumbnails
    -> Background Production
    -> Character Staging
    -> Character Rendering and Placement
    -> Dialogue and Lettering
    -> Effects and Final Integration
    -> Panel QA -> Page QA -> Issue QA
    -> Approval
    -> Export
```

Every directory, schema and script supports one of those steps. Anything that
does not, does not belong here.

---

## Format standard

Owner-mandated on 2026-07-28 and enforced by the validator.

| Format | Total pages | Story pages |
|---|---|---|
| Single-issue comic | 24–32 | 20–22 |
| Trade paperback | 96–200 | — |
| Original graphic novel | 48–500 | — |

Panels per page: **average 5**, minimum 1 (splash), maximum 9.

Plus rhythm rules — at least four distinct panel counts across an issue, no more
than two consecutive pages with the same count, at least one splash, at least
one dense page, and no repeated grid on consecutive pages. Hitting an average of
five by putting five panels on every page reproduces the exact monotony this
rebuild exists to correct.

Details: `canon/rules/FORMAT_STANDARD.md`.

---

## Visual standard

The house style is defined by three published Fiend Studios editions, designated
by the owner on 2026-07-28:

| Edition | Title |
|---|---|
| One | MonkeyZoo: The Battle Against Inefficiency and Centralization |
| Two | FusionZoo: The De-Fusion Tapes |
| Three | Winter edition |

Irregular per-page panel grids on a coloured page ground, characters integrated
into illustrated environments with cast shadows and colour spill, large stylised
SFX, colour-coded balloons, and the Fiend Studios collectible stamp on every
cover.

Details: `canon/style/HOUSE_STYLE.md`.

---

## Directory structure

| Directory | Contents |
|---|---|
| `config/` | Schemas, format standard, import plan, local machine config |
| `docs/` | Architecture, audits, decisions, quality, workflows, migration |
| `source_material/` | **Immutable** imported copies plus manifests |
| `canon/` | Normalised written truth — style, rules, continuity |
| `characters/` `locations/` `props/` | `approved` / `working` / `generated_candidates` / `rejected` |
| `issues/` | Per-issue production, stages `00_brief` through `14_exports` |
| `workflows/` | ComfyUI and production workflow definitions |
| `app/` | Software: core, domain, services, adapters, cli, ui |
| `scripts/` | Bootstrap, migration, inventory, validation, production, utilities |
| `tests/` | Unit, integration, fixtures, production validation |
| `workspace/` | Disposable working material. Git-ignored. |
| `vault/` | Retained but excluded from discovery and production. Git-ignored. |

Full semantics: `docs/architecture/REPOSITORY_POLICY.md`.

---

## Getting started

```bash
pip install -e ".[dev]"

python -m app.cli.main status      # where every issue stands
python -m app.cli.main validate    # every gate
python -m app.cli.main comfy       # probe the local ComfyUI
python -m app.cli.main dashboard   # write the static HTML dashboard
python -m pytest                   # tests
```

### Importing source material

The repository ships with manifests but not the binaries. Rebuild the imported
corpus from the read-only source:

```bash
python scripts/migration/import_source_material.py --dry-run
python scripts/migration/import_source_material.py
```

The plan is `config/defaults/import-plan.yaml`. The script never writes to the
source and refuses to run if it could. Every copied file is hashed;
`validate` re-checks all 1331 against the manifest.

### Working on an issue

Stage by stage, in order. Never skip ahead.

```bash
python -m app.cli.main status issue-001-neonblue-the-last-light-of-summer -v
```

Regenerate derived artefacts after changing a script:

```bash
python scripts/production/build_panel_script.py
python scripts/production/derive_script_views.py <issue-slug>
python scripts/production/build_layout_spec.py <issue-slug>
python scripts/production/render_layout_thumbnails.py <issue-slug>
python scripts/production/build_character_coverage.py <issue-slug>
```

---

## How approvals work

**A machine gate may only reject. It may never approve.**

Automated validation checks schemas, panel scripts, format compliance, manifest
integrity, hygiene and layout geometry. Any of them can fail an issue. None can
pass one.

Approval lives in `issues/<issue>/13_approved/approval-record.yaml`, written by
hand, naming a person and referencing an evidence hash. No script in this
repository writes that file.

Details: `docs/quality/APPROVAL_WORKFLOW.md` and ADR-005.

---

## How ComfyUI fits

Live at `http://127.0.0.1:8188` — AMD Radeon RX 6800 via ZLUDA, 17.2 GB VRAM,
ComfyUI 0.19.3, 1158 node types. ControlNet Union, IP-Adapter Plus, depth and
OpenPose preprocessors, inpainting and background removal are all present.

**There is no MonkeyZoo style LoRA, and the two installed checkpoints are
photorealistic and anime.** So:

- **Character identity comes from approved art**, never from text-to-image.
- **Backgrounds are generated**, then human-selected.
- **Characters are composited into plates** with real ground contact, shadow and
  light matching.

The adapter is read-only — it discovers capability and does not queue jobs.
Generation is added after a controlled single-panel test proves identity
preservation and scene integration.

Details: `docs/workflows/COMFYUI_CAPABILITY_AUDIT.md` and
`COMFYUI_INTEGRATION_PLAN.md`.

---

## Issue 001 production status

**NeonBlue — The Last Light of Summer.** 28 pages, 22 story pages, 103 panels.

```
[x] Research
[x] Issue Bible          (awaiting owner approval)
[x] Script               (awaiting owner approval)
[x] Storyboards
[x] Layouts              (awaiting owner approval)
[ ] Backgrounds
[ ] Character Staging    (coverage reports done; staging plans pending)
[ ] Character Rendering
[ ] Compositing
[ ] Lettering
[ ] Effects
[ ] QA
[ ] Approval
[ ] Export
```

**Blockers**

1. Owner ruling on conflict **C-01** — does the Echo activate after the choice
   (season bible) or at the midpoint (legacy script)?
2. Owner ruling on conflict **C-02** — does Lil Devil's interference cause the
   discovery?
3. **Lil Devil has no true-alpha layer set.** He appears in 17 panels.
4. **No festival location plate is calibrated.** Character scale has no
   defensible basis until they are.

**Next production action:** calibrate the four festival plates and produce the
Lil Devil alpha layer set. Both are unblocked and independent.

---

## What is not built

- Any Issue 001 artwork
- ComfyUI job submission
- A style LoRA
- Automated compositing
- Lettering tooling
- Export pipeline
- Any GUI beyond a static dashboard

All deferred deliberately. See ADR-003.

---

## Git and asset policy

Git tracks decisions, specifications and provenance. It does not track pixels.

The migration manifest records path, size, SHA-256, classification and authority
for all 1331 imported files, so the corpus is rebuildable and verifiable without
being committed. Git LFS is not enabled; the reasoning and the conditions that
would change it are in `docs/architecture/ASSET_VERSIONING_POLICY.md`.

---

## Source material

Imported read-only from the MonkeyZoo Comic Factory and the published editions.
**The originals were verified byte-identical before and after the migration.**

Provenance: `source_material/manifests/source-migration.csv`.
Report: `docs/migration/MIGRATION_REPORT.md`.
