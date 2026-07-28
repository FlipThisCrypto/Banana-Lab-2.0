# MonkeyZoo Automation Rules
**Version:** 1.0

Who does what, and what may run without a human.

---

## 1. Tool Roles

| Tool | Role |
|---|---|
| Claude Fable 5 | Showrunner, pipeline architect, continuity manager, script writer, prompt-pack generator, automation planner, QA checklist generator (Stages 1–5, 7*, 9*, 10 — * = report writing; approval clicks stay human) |
| Claude Code | Create folders, run `scripts/*.py`, validate JSON, rename files, package exports, append ledger entries, git commits |
| ComfyUI | Panel/cover/reference/background generation, upscaling, inpainting; workflows saved per shot-type and reused |
| Kohya SS | Train/update character LoRAs (trigger: 20+ approved refs per character, or identity QA failure rate >30%) |
| ControlNet | openpose (poses), depth (staging), canny/lineart (layout matching) |
| IPAdapter | Character identity lock + style lock from approved refs |
| Krita / Photoshop / CSP / Affinity / GIMP | Cleanup, lettering, bubbles, panel edits, final page corrections |
| Python | `new_issue.py` (scaffold), `validate_issue.py` (schemas + completeness), `build_release.py` (CBZ/renames/archive staging) |
| Git | Version control of the whole factory; canon history; rollback |

## 2. Automation Levels

- **AUTO (no approval needed):** folder scaffolding, JSON validation, file
  renaming to conventions, CBZ packaging, checksum computation, archive
  copying, ledger APPEND (drafted by agent, committed by script).
- **DRAFT (agent produces, human approves):** briefs, outlines, scripts,
  prompt packs, covers, social posts, metadata, QA reports.
- **HUMAN-ONLY:** canon approval (moving anything into 03_APPROVED_CANON),
  panel approve/reject final click, RELEASE decision, minting/publishing,
  any edit to a LOCKED bible section, character redesigns.

## 3. File & Naming Conventions (scripts enforce)

- **Issue format standard (owner directive 2026-07-17):** 16 story pages,
  ~96 panels total (target 6 per page), plus a single-panel FRONT cover
  and a single-panel BACK cover. The back cover always introduces the
  next issue (title + teaser image built from the next issue's location/
  cast). Existing shorter issues are decompressed to this format: each
  original story beat becomes a 4-panel acting sequence (establish →
  action → reaction → button) so published events and dialogue stay
  locked while page count doubles. Covers live outside page_panel_plan
  (cover_prompt.md; the final cover deliverable at generated_art/covers/main_cover.png,
  resolved by 00_SYSTEM/scripts/issue_cover.py); Gate B's "next-issue
  teaser on rear cover" item is now satisfied by the back-cover panel.
- Issue folder: `YYYY-MM_Issue_##` · Issue ID: `MZ-YYYY-MM-##`
- Panel ID: `MZ-YYYY-MM-##_P<page 2-digit>_PANEL<2-digit>`
- Raw art: `<panel_id>_seed<seed>_v<n>.png` in `raw_panels/`
- Selected: `<panel_id>.png` in `selected_panels/` (exactly one per panel)
- Upscaled: `<panel_id>_print.png` · Edited: `<panel_id>_final.png`
- Exports: `MonkeyZoo_Issue_##_Print.pdf`, `_Web.pdf`, `_CBZ.zip`, `cover.png`

## 3A. Source-Of-Truth Filing

- Franchise rules, visual rules, continuity ledger, prompt rules, schemas, and
  stage agents live in `00_SYSTEM/`.
- Season story bibles live in `story-bibles/seasons/<season-id>/`.
- Character canon is reviewed through the Character Bible system and must not
  be overwritten by story-development proposals without owner approval.
- Production image references live in `03_APPROVED_CANON/approved_characters/`.
- The current character/image routing page is
  `03_APPROVED_CANON/approved_characters/CHARACTER_IMAGE_INDEX.md`.
- Loose source cards copied into `source_images/` are provenance references.
  Use numbered approved pose/expression files for generation unless the index
  or issue plan explicitly says otherwise.
- Patch is filed from Issue 05/06 evidence as `zombie.png (#1997 = Patch)`;
  treat that as Patch-specific evidence, not a blanket Zombie/Stayed identity.

## 4. Pipeline Gates (a stage may not start until the previous gate passes)

```
G0 idea file exists            → Stage 1 Intake
G1 brief approved              → Stage 2 Continuity
G2 no unresolved conflicts     → Stage 3 Showrunner
G3 outline approved            → Stage 4 Script
G4 plan JSON validates         → Stage 5 Art Director
G5 pack JSON validates         → Stage 6 Generation (ComfyUI)
G6 batch complete              → Stage 7 Art QA
G7 every panel approved        → Stage 8 Layout & Lettering
G8 pages assembled             → Stage 9 Final QA
G9 RELEASE verdict             → Stage 10 Release + archive + git tag
```

## 5. Git Discipline

- Commit after every stage gate with message `MZ-YYYY-MM-##: <stage> done`.
- Tag releases `issue-##`. Bibles/ledger changes always in their own commit
  (`canon: <what changed>`), never mixed with issue files.
- Generated art is committed only from `selected_panels/` onward; `raw_panels/`
  is gitignored (bulk).

## 6. Byte-Exact Value Rule

Any byte-exact value written into a release file — sha256 hashes, IPFS CIDs,
the MonkeyZoo DID, seeds — must be produced by a disk/command read at the
moment of writing (`Get-FileHash`, reading the source file), NEVER transcribed
from conversation context or memory. Rationale + background: `tooling_pxpipe.md`
(context-compression tooling can silently confabulate hex). Stage 9 verifies
hashes by recomputation only.

## 6A. Character Integration Pipeline (optional Stage 6.5; built 2026-07-16, extended 2026-07-17)

For panels where characters are composited onto an *existing approved*
background plate (rather than generated monolithically in one prompt),
use `00_SYSTEM/scripts/integration/`:

```
alpha_matte.py     -- chroma-key a ref into a true-alpha layer (border-
                       connected flood fill; baked-ground-shadow stripper;
                       --inset mode for card-style refs like Clever's set)
gen_scene_pose.py  -- bespoke scene poses: TEXT2IMG from the calibrated
                       BASE prompt + pose clause. img2img from minted
                       cards drifts identity colors at any pose-changing
                       denoise (measured, Cycle 13) -- don't use it for
                       new poses.
compositor.py      -- single (pose_spec.json) or multi-character
                       (characters_spec.json) placement on a calibrated
                       ground plane: depth-sorted far-to-near, per-
                       character relight (shadow.py/relight.py), contact
                       shadow (ground-adaptive opacity), reflections
                       (reflection.py, per declared surface), depth haze
                       (haze.py, color sampled from the plate), behind-
                       geometry occlusion (traced occluder polygons),
                       foreground weather (occlusion.py), per-character
                       grounding_boost overrides, calib_to_character_factor
                       for non-chibi-scale calibration objects
calibrate_check.py -- renders horizon/calibration/lights/surfaces/
                       occluders over the plate; EVERY calibration value
                       gets a look-at-it verification image
identity_check.py  -- canon-palette drift detection for layers (catches
                       the beige-face class; NOT a character classifier)
validate_integration.py -- pixel QA gate: leftover reference/card colors
                       (plate-baseline-subtracted), flat debug overlays,
                       plate-diff grounding check under each foot anchor
stage_preview.py   -- stages finals + before/after sheets into the
                       issue's generated_art/integration_preview/
validate_issue.py --integration  -- runs the gate over all staged
                       previews (the Stage 9 hook; see qa_checklist v1.1
                       Gate A "Integration" section for the human items)
```

Plate calibrations for all five Issue-02 environments live in
`00_SYSTEM/integration_upgrade/plate_calibrations/` (measured horizons
with documented derivations and uncertainty bands). Issue 02 is fully
integrated: all 96 panels + front cover + Issue-03-teaser back cover
staged as integration previews (96/96 pass `validate_issue
--integration`); full flip-through at
`02_MONTHLY_ISSUES/2026-09_Issue_02/generated_art/integration_preview/
pages_preview/ISSUE_02_full_preview.png`. Per-panel specs live in
`00_SYSTEM/integration_upgrade/_specs/`; every panel regenerates via
`build_panel.py <spec.json>`.

This does **not** replace Stage 6 — it is an alternative path for
plate+character panels, and human Gate A/B sign-off still applies before
anything is promoted; `stage_preview.py` never writes `selected_panels/`.
Full build/verification record: `00_SYSTEM/integration_upgrade/
CYCLE_LEDGER.md` (30 cycles, including honest rejections — masked-ring
img2img edge unification was evaluated and REJECTED with evidence at cfg
1.0; see the Cycle 16 entry before reconsidering it).

## 7. Failure / Rollback Rules

- Schema validation failure → block gate, report exact field, never hand-fix
  JSON silently: fix the producing stage's output.
- Art QA failure rate >50% in a batch → stop generating; check identity stack
  (LoRA weight, refs loaded, ControlNet map) before burning more compute.
- Continuity conflict found after Stage 4 → return to Stage 2, do not patch
  dialogue locally.
- Anything canon-breaking discovered post-release → next issue addresses it or
  ledger records the erratum; never silently edit released files.
