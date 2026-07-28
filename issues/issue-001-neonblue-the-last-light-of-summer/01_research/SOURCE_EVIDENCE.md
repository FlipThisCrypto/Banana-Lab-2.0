# Issue 001 — Source Evidence

Everything found about *NeonBlue — The Last Light of Summer*, where it came
from, and how much weight it carries.

Compiled 2026-07-28. All paths are repository-relative unless marked as source
paths. Every file listed here was copied read-only; the originating factory was
verified byte-identical before and after import (see
`docs/migration/MIGRATION_REPORT.md`).

---

## 1. Authoritative narrative sources

| Evidence | Path | Authority | Why it counts |
|---|---|---|---|
| Season bible, section 7 | `source_material/imported_bibles/story-bibles/seasons/2026-emo-monkeys-the-signal-between-us/SEASON-BIBLE.md` | authoritative | The complete Issue 001 plan: premise, emotional question, guest function, plot progression, Echo reveal, final image. This is the primary narrative source. |
| Issue 001 story brief | `.../story-bibles/seasons/2026-emo-monkeys-the-signal-between-us/issue-01-neonblue.md` | authoritative | Short form. Explicitly defers to section 7 of the season bible. Marks the issue `proposed story canon until owner-approved`. |
| Location and prop tracker | `.../story-bibles/seasons/2026-emo-monkeys-the-signal-between-us/location-and-prop-tracker.md` | authoritative | Issue 001 location and prop table. |
| NeonBlue character bible | `source_material/imported_bibles/character-bibles/MZ-CHAR-005/bible.md` + `bible.yaml` | authoritative | Identity source of truth. Outranks the season bible on who NeonBlue is and how he may be drawn. |
| Supporting character bibles | `.../character-bibles/MZ-CHAR-001..006`, `MZ-CHAR-LILDEVIL`, `MZ-CHAR-PATCH` | authoritative | Identity for the full cast. Patch has a bible despite never appearing on-page. |
| World bible and continuity ledger | `source_material/imported_bibles/system/monkeyzoo_master_bible.md`, `continuity_ledger.md` | authoritative | World rules and the running continuity record. |

### What the season bible establishes for Issue 001

- **Title** THE LAST LIGHT OF SUMMER. **Release** August 2026.
- **Featured** NeonBlue (`MZ-CHAR-005`). **Guest** Lil Devil (`MZ-CHAR-LILDEVIL`).
- **Setting** MonkeyZoo end-of-summer night festival.
- **Emotional question** Can NeonBlue acknowledge real danger without feeling
  he has betrayed hope?
- **Crisis** A small group is trapped in a dark service corridor while the final
  countdown pulls everyone's attention to the main stage. NeonBlue chooses the
  overlooked group.
- **Echo reveal** The cyan pulse forms one sixth of the Echo symbol. The relay
  activates *only after* NeonBlue chooses the unseen group over the spotlight.
- **New question** Why did the old relay recognise NeonBlue?
- **Final image** NeonBlue watches the restored lights while a small cyan symbol
  flickers behind him, unseen.
- **Guest constraint** Lil Devil's impatience *accidentally reveals* that the
  failures are not random, and he contributes decisive force only after NeonBlue
  identifies where force is safe.
- **Recommended shape** 8 pages, 20 panels, 2–4 panels per page, one splash or
  large reveal, one quiet emotional panel near the climax, one final-page hook.

---

## 2. Approved visual canon

| Evidence | Path | Count | Notes |
|---|---|---|---|
| NeonBlue character art | `source_material/imported_canon/approved_characters/neonblue/` | 32 | Numbered set `00_clean_base` through `30_backview`, plus a legacy `.webp`. Opaque backgrounds. |
| NeonBlue expression art | `source_material/imported_canon/approved_expressions/neonblue/` | 31 | Substantially the same images as above; 321 duplicate files were detected by hash across the whole canon import. |
| Full cast character art | `.../approved_characters/` | 417 files, 12 characters | Ash, Cheeky, Clever, Emo, Lil Devil, Moodz, NeonBlue, Scarline, Static, Super, TwoTone, Zombie. |
| **True-alpha character layers** | `source_material/imported_canon/character_layers/` | 139 files, 8 characters | **The most valuable production asset found.** Background-removed, verified true alpha on all 139. NeonBlue has 17. |
| Layer index | `.../character_layers/layer_menu.json` | 1 | Maps character → pose slug → file. |
| Festival location plates | `source_material/imported_canon/approved_locations/festival-*/` | 4 plates | `festival-grounds`, `festival-main-stage`, `festival-service-corridor`, `festival-control-node`. All 1280×720, all with a `bible.md`. |
| Issue 001 props | `source_material/imported_canon/approved_props/` | 10 relevant | `control-box`, `service-gate`, `cyan-relay-marker`, `echo-symbol`, `public-projection-screen`, `festival-backup-panel`, and others. One primary view each. |
| Plate calibrations | `source_material/imported_canon/plate_calibrations/` | 4 | Ground-plane and horizon data — but for `old-relay-junction`, `school-pa-zone`, `storm-routines`, `transit-announcement-hub`. **No festival plate is calibrated.** |

### Verified asset facts

- All 139 character layers carry real alpha (minimum alpha channel value < 250
  on every file). Confirmed programmatically at import.
- **Lil Devil has no alpha layer.** The Issue 001 guest is absent from the layer
  library. This is the single largest character-asset gap.
- Only four festival plates exist. The legacy issue drew 19 of its 24 panels
  from these four.

---

## 3. Approved aesthetic reference

### Primary — the published Fiend Studios editions *(owner-designated)*

Supplied by the project owner on 2026-07-28 with the instruction *"This is the
artistic style that I want for each issue."* Imported at authority
`authoritative`.

| Edition | Title | Pages | Path |
|---|---|---|---|
| One | MonkeyZoo: The Battle Against Inefficiency and Centralization | 11 | `visual_references/published_editions/edition-01-the-fusion-squad/` |
| Two | FusionZoo: The De-Fusion Tapes | 9 | `.../edition-02-the-defusion-tapes/` |
| Three | Winter edition | 8 pages, 31 panels | `.../edition-03-winter/` |
| — | Fiend Studios collectible stamp | 1 | `.../_stamps/` |

Each PDF is kept untouched, with rendered page images in `_pages/` as a
normalised derivative (`scripts/utilities/render_edition_pages.py`).

These are finished, published comics — irregular per-page panel grids on a
coloured page ground, characters properly integrated into illustrated
environments with cast shadows and environment colour spill, large stylised
SFX, colour-coded balloons, and a collectible stamp on every cover.

**Edition Two is the primary target for Issue 001**: the Emo Monkey cast, at
night, in dark interiors lit by cyan and green technology. Tonally and
technically the closest match to a blacked-out festival with a reacting relay.

The full analysis is `canon/style/HOUSE_STYLE.md`.

### Secondary — Mango Pier

`source_material/visual_references/mango-pier/` — *The Meltdown at Mango Pier*,
20 panels, 8 pages, cover, script, brief, QA report, page plan, prompt pack.

A recent in-house production at a **lower finish level** than the published
editions. Useful for cast consistency and as a comparison point, but it is not
the target. Its defects are recorded in `VISUAL_PROBLEMS.md` §8.

### Also found

`source_material/visual_references/character_concepts/` — 63 per-character
concept renders for NeonBlue, Ash, Static and Scarline, imported at authority
`candidate`. Useful for expression and pose ideas. **Not approved canon**, and
must not override `imported_canon`.

`source_material/imported_bibles/emo-editions/MonkeyZoo_Emo_Edition4_STILL_ME.md`
— the Emo Monkey Edition 4 bible, establishing the cast voice and the
FusionZoo-chamber premise, plus the published cover-design conventions.

---

## 4. The legacy Issue 001 production record

`source_material/legacy_reference/issue-001-2026-08/` — the previous attempt,
issue ID `MZ-2026-08-01`, imported at authority `historical-reference`
(documents) and `superseded` (artwork).

| Artefact | State |
|---|---|
| `issue_script.md` | 8 pages, **19 panels**. Substantially faithful to the season bible. The most reusable legacy artefact. |
| `page_panel_plan.json` | 8 pages, **24 panels**. Disagrees with the script. |
| `metadata.json` | Declares `panel_count: 24` and `ArtTier: draft_composite`. Status `release`. |
| `.workflow-status.json` | `active_stage: published`. Owner approvals recorded at canon_review, script, art_production, qa and release. |
| `qa_report.md` | **VERDICT: PASS.** |
| `selected_panels/` | 24 PNGs. 19 are draft composites; 5 are raw generation artefacts. |
| `pages/` | 8 assembled print pages, 2480×3508. |
| `main_cover.png` | Draft cover. |

---

## 5. Historical issues

`source_material/historical_issues/` — 13 published PDFs plus the GENESIS
collected edition and its records. Imported at `historical-reference`.

These inform continuity and show how earlier issues were shaped. None of them
is automatically approved, and none supersedes the season bible.

---

## 6. The "older HTML comic"

The brief anticipated an older HTML comic. There is none. What exists is
`source_material/legacy_reference/banana-lab-1-html/index.html`: the Banana
Lab 1.0 **review application** shell — a studio UI for browsing character
bibles, not a comic. Recorded here so the question is closed rather than left
open.

---

## 7. Local generation capability

ComfyUI is **live** at `http://127.0.0.1:8188` and was queried directly during
this audit. Full findings: `docs/workflows/COMFYUI_CAPABILITY_AUDIT.md`.

Headlines relevant to Issue 001:

- AMD Radeon RX 6800 via ZLUDA, 16 GB VRAM, ComfyUI 0.19.3, 1158 node types.
- Checkpoints available: `RealVisXL_V4.0` (photoreal) and `animagine-xl-4.0`
  (anime). **Neither produces the MonkeyZoo flat-vector house style.**
- **Zero LoRAs installed.** There is no MonkeyZoo style model.
- ControlNet Union SDXL promax, IP-Adapter Plus SDXL, CLIP-ViT-H, depth and
  OpenPose preprocessors, and background-removal nodes are all present.

The absence of a style LoRA is the fact that shapes the whole production plan:
character identity cannot be trusted to text-to-image, so it must come from
approved art. See `REBUILD_RECOMMENDATION.md`.

---

## 8. Prior art worth keeping: the integration upgrade track

`00_SYSTEM/integration_upgrade/` in the source factory records a serious body of
work that solved much of the staging problem — for Issue 02, not Issue 001. Its
own `ARCHITECTURE_FINDINGS.md` reports:

- True-alpha character layers, built and verified.
- Ground-plane placement calibrated against measured horizons.
- Contact shadows with ground-adaptive opacity, reflections, relighting, depth
  haze, geometry occlusion, depth-sorted multi-character staging.
- 96 integrated panels for Issue 02, all passing an integration validator.
- Edge unification via img2img **rejected with measured evidence** — the engine
  hallucinates at cfg 1.0.

Banana Lab 2.0 inherits the layer library and the method. Those techniques were
never applied to Issue 001, which is why Issue 001 still ships card cut-outs.

---

## 9. What is missing

| Gap | Consequence |
|---|---|
| No Lil Devil alpha layer | The guest character cannot be staged from approved art. |
| No festival plate calibration | Character scale and ground contact have no measurable basis in any Issue 001 location. |
| Only 4 festival plates | Cannot support 20 panels without visible repetition. |
| No style LoRA | Generated backgrounds will not match the house style without heavy prompt and post control. |
| No crowd or extras assets | The festival reads as empty; the crisis needs a trapped group that does not exist as art. |
| No approved Patch visual | The midpoint recognition beat has no on-page anchor beyond the relay marker prop. |
| No lettering assets or font record | Balloon style is not specified anywhere. |

---

## 10. Conflicts found

Recorded in full in `CANON_CONFLICTS.md`. Summary: 7 conflicts, of which 2
require an owner decision before art production begins.
