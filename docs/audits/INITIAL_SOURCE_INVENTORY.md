# Initial Source Inventory

**Compiled 2026-07-28**, before any architectural decision was made and before
anything was copied. All inspection was read-only.

---

## Directories inspected

| Path | Files | Size |
|---|---:|---:|
| `I:\MonkeyZoo Comic Strip\Fusion Squad\MonkeyZoo_Comic_Factory` | **6997** | **4.79 GB** |
| `.../MonkeyZoo_Comic_Factory\03_APPROVED_CANON` | 895 | 497.7 MB |
| `.../character-bibles` | 292 | 60.1 MB |
| `.../story-bibles` | 15 | 0.1 MB |
| `.../02_MONTHLY_ISSUES\2026-07_Mango_Pier` | 206 | 188.9 MB |
| `.../02_MONTHLY_ISSUES\2026-08_Issue_01` | 160 | 411.9 MB |
| `.../00_SYSTEM\integration_upgrade` | 474 | 188.8 MB |
| `.../GENESIS` | 170 | 290.2 MB |
| `I:\MonkeyZoo Comic Strip\Fusion Squad\1` (Edition One) | 17 | ~52 MB |
| `.../Fusion Squad\2\nft` (Edition Two) | 2 | ~17 MB |
| `.../Fusion Squad\3\winter edition 3` (Edition Three) | ~60 | ~1.1 GB |
| `.../Fusion Squad\Bible and other files` | ~15 | — |

The two edition directories and the extra bible folder were added mid-run when
the owner designated the published editions as the style target.

---

## What was found

### Authoritative

| Material | Location | Detail |
|---|---|---|
| **Season bible** | `story-bibles/seasons/2026-emo-monkeys-the-signal-between-us/SEASON-BIBLE.md` | 1572 lines. Section 7 is the complete Issue 001 plan: premise, emotional question, guest function, plot progression, Echo reveal, final image. |
| Issue 001 brief | `.../issue-01-neonblue.md` | Short form; defers to §7. Marks the issue `proposed story canon until owner-approved`. |
| Character bibles | `character-bibles/MZ-CHAR-*/` | 12 characters, each with `bible.md`, `bible.yaml`, continuity log, development notes. Patch has a bible despite never appearing. |
| Approved character art | `03_APPROVED_CANON/approved_characters/` | 417 files across 12 characters. Numbered sets `00_clean_base` through `30_backview`. |
| Approved expressions | `.../approved_expressions/` | 372 files. Substantially overlaps the character set. |
| Approved locations | `.../approved_locations/` | 20 locations, 1280×720 plates plus a `bible.md` each. **Only four are festival locations.** |
| Approved props | `.../approved_props/` | 31 props, one primary view each. |
| World bible, continuity ledger | `00_SYSTEM/` | Master bible, continuity ledger, prompt and automation rules. |
| **Published editions** | `Fusion Squad\1`, `\2\nft`, `\3\winter edition 3` | Three finished Fiend Studios comics — 11, 9 and 8 pages. Owner-designated style target. |
| Fiend Studios stamp | `Fusion Squad\2\Fiend_Studios_Stamp_2-removebg-preview.png` | Circular collectible stamp appearing on every published cover. |
| Emo Edition 4 bible | `Bible and other files/MonkeyZoo_Emo_Edition4_STILL_ME.md` | Cast voice and the FusionZoo-chamber premise. |

### Approved reference

| Material | Location | Detail |
|---|---|---|
| **True-alpha character layers** | `00_SYSTEM/integration_upgrade/character_layers/` | **139 files across 8 characters.** All verified true alpha. The most valuable production asset found. **Lil Devil is absent.** |
| Layer index | `.../layer_menu.json` | Maps character to pose slug to file. |
| Plate calibrations | `.../plate_calibrations/` | 4 locations with horizon and scale-reference data. **None is a festival location.** Their own note calls the values art-directed estimates. |
| Mango Pier | `02_MONTHLY_ISSUES/2026-07_Mango_Pier/` | 20 finished panels, 8 pages, cover, script, QA report. A genuinely finished comic at a lower finish level than the published editions. |

### Historical reference

13 published issue PDFs across `02_MONTHLY_ISSUES/*/exports/` and
`05_RELEASE_ARCHIVE/`, plus the GENESIS collected edition and its records.

### Superseded

The complete legacy Issue 001 production record — script, page plan, metadata,
QA report, workflow status, 24 panel images, 8 assembled pages, cover, exports.

### Uncertain at inspection time

| Item | Question |
|---|---|
| `character_concepts` (63 renders) | Never classified in the source project. Imported as `candidate`. |
| Plate calibrations | Self-described as estimates. Authority arguable. |
| GENESIS | Canon standing never established. |
| Mango Pier | Presumed style target until the owner ruled otherwise. |

---

## The "older HTML comic"

The brief anticipated one. **There is none.**

What exists is `docs/index.html` and
`character-bibles/_review_app/static/index.html` — both the Banana Lab 1.0
**review application** shell, a studio UI for browsing character bibles. Not a
comic. Recorded so the question is closed.

---

## Duplicate detection

By hash across the import set: **323 duplicate files out of 1331 (24 percent)**,
1008 unique.

Almost all sit between `approved_characters/` and `approved_expressions/` — the
same PNGs filed twice under two organising schemes. They were copied, not
collapsed; the source project's structure is itself information.

---

## Local generation capability

ComfyUI was **live** at `http://127.0.0.1:8188` during the audit and was queried
directly: version 0.19.3, AMD Radeon RX 6800 via ZLUDA, 17.2 GB VRAM, 1158 node
types.

Two SDXL checkpoints (photorealistic and anime), one ControlNet union model, one
IP-Adapter, **zero LoRAs**, **zero upscale models**.

Full audit: `docs/workflows/COMFYUI_CAPABILITY_AUDIT.md`.

---

## What is missing

| Gap | Consequence |
|---|---|
| No Lil Devil alpha layer | The Issue 001 guest cannot be staged from approved art |
| No festival plate calibration | Character scale has no defensible basis |
| Only 4 festival plates | Cannot carry 22 story pages without visible repetition |
| No style LoRA | Generated backgrounds will not match the house style unaided |
| No crowd or extras assets | The festival reads as empty; the crisis needs a trapped group that does not exist |
| No approved Patch visual | The midpoint beat has no anchor beyond the relay-marker prop |
| No lettering font recorded | Balloon style unspecified anywhere, including the published editions |
| No upscale model | Cannot enlarge panel art for print |

---

## Conflicts found

Eight, all relating to Issue 001, recorded in full in
`issues/issue-001-*/01_research/CANON_CONFLICTS.md`. Two require an owner
ruling: the Echo reveal timing (C-01) and Lil Devil's guest function (C-02).

---

## What can be reused

- **The writing.** The legacy script is substantially faithful to the season
  bible and was rebuilt from rather than replaced.
- **The 139 true-alpha layers.** Composite-ready, covering 6 of 7 Issue 001
  characters.
- **The approved canon library.** 417 character files, 372 expressions, 20
  locations, 31 props.
- **The integration method.** The source project's `integration_upgrade` track
  solved ground-plane placement, contact shadows, reflections, relighting,
  occlusion and depth-sorted staging — proven on 96 panels of Issue 02, never
  applied to Issue 001.
- **A rejection worth inheriting.** That track tested img2img edge unification
  and rejected it with measured identity-drift evidence. Not retrying it is as
  valuable as adopting the techniques.
- **The plate calibration format.** The format is the asset; festival plates need
  their own built to it.

## What should not be reused

- **All 24 legacy Issue 001 panel images.** 19 are draft composites; 5 are not
  comic panels.
- **The 8 assembled legacy pages**, which carry visible `DRAFT COMPOSITE`
  headers.
- **The legacy QA report.** Its `PASS` verdict is evidence of gate failure, not
  of quality.
- **The legacy page plan**, which contradicts its own script and was never
  reconciled.
- **Mango Pier's staging.** Front-facing lineups, eye-level everything, blob
  crowd extras, and logo bars and name labels baked into the panel art.

---

## What should remain reference-only

`historical_issues/` and `legacy_reference/` are evidence, not source. The
published editions are authoritative for **style**; they are not story canon for
this season. The character concept renders are `candidate` until the owner rules.

---

## Recommendation carried forward

Copy the approved canon, the bibles, the alpha layer library, the published
editions, the Mango Pier reference and the complete legacy Issue 001 record —
every file hashed and classified, nothing normalised, nothing deleted, and the
source left byte-identical.

That is what the migration did. Result: `docs/migration/MIGRATION_REPORT.md`.
