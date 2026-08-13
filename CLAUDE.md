# Instructions for Claude working in Banana Lab 2.0

Read this before touching anything. This file and `AGENTS.md` are kept identical
- edit both, or copy one over the other.

## What this repository is

A **structured comic-production system** for MonkeyZoo. Not an image generator,
not an art GUI. Every directory, schema and script exists to support one step of
a documented pipeline.

The current production goal is **Issue 001: NeonBlue — The Last Light of
Summer**.

## Read these first, in order

1. `README.md` — what this is and where it stands
2. `docs/audits/BOOTSTRAP_COMPLETION_REPORT.md` — what was actually done
3. `canon/rules/FORMAT_STANDARD.md` — page and panel counts. Owner-mandated.
4. `canon/style/HOUSE_STYLE.md` — the visual standard. Owner-designated.
5. `docs/quality/QUALITY_STANDARD.md` — what "good" means here
6. `docs/decisions/ADR-*.md` — why the system is shaped this way
7. `issues/issue-001-*/01_research/REBUILD_RECOMMENDATION.md` — the current plan

## Hard rules

### Never modify source material

`I:\MonkeyZoo Comic Strip\Fusion Squad\` and everything under it is **read-only**.
Never write, move, rename or delete anything there.

`source_material/` in this repository is an immutable copy. Only
`scripts/migration/import_source_material.py` writes it.
`app/core/paths.assert_safe_write_target()` refuses everything else.

### Never overwrite an approved asset

Anything under an `approved/` directory is human-approved. A revision is a
**new versioned file**; the old one stays. See ADR-002.

### Never confuse candidates with approved assets

`generated_candidates/` is unapproved output. It never enters a composite and
never gets promoted without human review. Directory location declares authority.

### Never approve anything

You may run validation. You may report failures. You may not write
`issues/*/13_approved/approval-record.yaml`, set `approval_status: approved`, or
move a file into `approved/`. See ADR-005.

Automated PASS does not authorize production. You may not write `human_pass`
into `12_qa/visual-review.yaml`. Visual review is a human art-direction gate
(`docs/quality/VISUAL_QUALITY_REVIEW.md`).

### Never declare completion without evidence

A stage is complete when its files exist and are non-empty — see
`app/domain/pipeline.py`. Check with:

```bash
python -m app.cli.main status
```

If the tool says a stage is incomplete, it is incomplete. Do not describe work
as finished because you wrote a plan for it.

## Working on an issue

Work **stage by stage**, in order. Do not skip ahead.

```
Research -> Issue Bible -> Script -> Storyboards -> Layouts ->
Backgrounds -> Character Staging -> Character Rendering -> Compositing ->
Lettering -> Effects -> QA -> Approval -> Export
```

Before changing any stage's status, run:

```bash
python -m app.cli.main validate
```

It checks schemas, panel scripts, the format standard, imported-source
integrity and repository hygiene. It must pass.

### Generated files — do not hand-edit

These are built from a source and will be overwritten:

| File | Built by |
|---|---|
| `03_script/panel-script.yaml` | `scripts/production/build_panel_script.py` |
| `03_script/dialogue-only.md` | `scripts/production/derive_script_views.py` |
| `03_script/visual-only.md` | `scripts/production/derive_script_views.py` |
| `05_layouts/layout-spec.yaml` | `scripts/production/build_layout_spec.py` |
| `04_storyboards/page-thumbnails/` | `scripts/production/render_layout_thumbnails.py` |
| `07_character_staging/*` | `scripts/production/build_character_coverage.py` |
| `06_backgrounds/staging-guides/` | `scripts/production/build_staging_guides.py` |
| `source_material/manifests/*` | `scripts/migration/import_source_material.py` |

Edit the source, then regenerate.

## Record provenance

Every generated image needs a job manifest — prompt, negative prompt, seed,
model, sampler, steps, cfg, dimensions, control images, output hash. See
`docs/workflows/COMFYUI_INTEGRATION_PLAN.md`. An image with no manifest cannot
be promoted.

## Do not add speculative features

Do not build a feature because it might be useful. Every addition must support a
named pipeline stage. See ADR-003.

If you find yourself building an asset browser, a plugin system or a general
purpose editor, stop.

## Stay bounded

The active production goal is Issue 001. Work that does not advance it needs a
reason. Do not:

- Redesign characters
- Rewrite MonkeyZoo canon
- Regenerate panels in bulk before the controlled test passes
- Delete or move anything in the old factory
- Add convenience features
- Mark AI output as approved

## When sources disagree

Precedence, highest first:

1. **Owner instruction** — e.g. the format standard, the house style
2. **Approved canon** — `source_material/imported_canon/`
3. **Character bibles** — identity, voice, forbidden changes
4. **Story bibles** — plot, structure, character function
5. **Older published issues** — supporting evidence
6. **Legacy production records** — evidence of what was attempted, never authority

Record the conflict. Do not silently invent a resolution. Issue 001 conflicts
`C-01` and `C-02` were owner-confirmed on 2026-08-13 (follow the season bible
in both cases). Recorded in `01_research/CANON_CONFLICTS.md` and the issue bible.

## Useful commands

```bash
python -m app.cli.main status      # where every issue stands
python -m app.cli.main validate    # every gate
python -m app.cli.main schemas     # available schemas
python -m app.cli.main comfy       # probe the local ComfyUI
python -m app.cli.main dashboard   # write the static HTML dashboard
python -m pytest                   # tests
```
