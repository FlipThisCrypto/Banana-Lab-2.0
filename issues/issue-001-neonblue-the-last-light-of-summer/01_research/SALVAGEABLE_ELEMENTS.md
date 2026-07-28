# Issue 001 — Salvageable Elements

What survives the rebuild, at what authority, and what it costs to reuse.

---

## Keep as-is

| Element | Source | Why |
|---|---|---|
| **Season bible §7 plan** | `imported_bibles/story-bibles/.../SEASON-BIBLE.md` | The authoritative Issue 001 structure. The rebuild restores it rather than replacing it. |
| **Title** — "The Last Light of Summer" | Season bible | Carries theme, lighting and colour progression. Nothing better exists. |
| **Story spine** | Legacy script | Arrival → first blackout → travelling outages → Patch recognition → corridor discovery → honest plan → rescue → reduced festival → Echo hook. Faithful to the bible and sound. |
| **Resolution line** | Legacy script 8.1 | *"Main stage finale was half-lit. Carousel stayed off. But everyone walked out safe. That's a good night."* Trim only for balloon length. |
| **Moodz's midpoint line** | Legacy script 5.2 | *"Your smile's three inches wider than usual. You don't have to sell safety to us."* Precisely in character. Trim the front. |
| **Scarline's page-2 line** | Legacy script 2.3 | *"Dark isn't the problem. What people do in it is."* Exactly her register — one clear sentence, delivered once. |
| **TwoTone's two-paths observation** | Legacy script 3.1 | The converging-currents idea is the bible's; the phrasing needs shortening. |
| **Location and prop selection** | Legacy `page_panel_plan.json` | The four festival locations and ten props chosen are the right ones. |
| **Issue ID `MZ-2026-08-01`** | Legacy metadata | Continuity with the published record. New internal ID `issue-001` addresses the rebuild. |

---

## Keep with revision

| Element | Revision needed |
|---|---|
| Ash's line | Restore the bible wording: *"Hope can read warnings."* (C-03) |
| Page-4 lore beat | Keep the beat; make the reaction ambiguous and move the true activation to page 8 (C-01) |
| Lil Devil's gate strike | Keep the directed-force beat; add the earlier uncontrolled action that causes the discovery (C-02) |
| NeonBlue's opening over-volunteering | Keep; cut "three main zones, eight rides" (C-04) |
| Final-page question | Keep the question; remove "thirteen-year-old" (C-04) |
| Page-6 corridor discovery | Keep; the trapped group must be visible and specific (C-07) |

---

## Reusable production assets

| Asset | Location | Count | Authority | Notes |
|---|---|---|---|---|
| **True-alpha character layers** | `imported_canon/character_layers/` | 139 across 8 characters | approved-reference | The single most valuable asset. Composite-ready. NeonBlue has 17. **No Lil Devil.** |
| Approved character art | `imported_canon/approved_characters/` | 417 files, 12 characters | authoritative | Opaque. Needs background removal before staging, but is the identity ground truth. |
| Approved expression art | `imported_canon/approved_expressions/` | 372 files | authoritative | 321 duplicates detected against the character set by hash. |
| Festival location plates | `imported_canon/approved_locations/festival-*/` | 4 × 1280×720 | authoritative | Correct locations, insufficient count and no calibration. |
| Issue 001 props | `imported_canon/approved_props/` | 10 relevant | authoritative | One primary view each. |
| Location and prop bibles | `.../*/bible.md` | 1 per asset | authoritative | Descriptive text usable for background prompting. |
| Plate calibration format | `imported_canon/plate_calibrations/` | 4 (non-festival) | approved-reference | **The format is the asset.** Festival plates need their own calibrations built to this shape. |

---

## Reusable method

The `00_SYSTEM/integration_upgrade` track solved character integration for
Issue 02 and its findings transfer directly:

| Technique | Status in source | Value here |
|---|---|---|
| True-alpha layer extraction with baked-shadow stripping | Built | Gives composite-ready characters from approved art |
| Ground-plane placement from measured horizon | Built, 5 plates | Method transfers; festival plates need calibrating |
| Contact shadows, ground-adaptive opacity | Built | Directly reusable |
| Reflections per declared surface | Built | Wet festival ground makes this valuable |
| Relight / key-fill per position, plate-sampled depth haze | Built | Directly reusable |
| Geometry occlusion via traced occluders | Built | Lets characters stand *behind* festival furniture |
| Depth-sorted multi-character staging with gaze-aware blocking | Built | Directly addresses the row-staging defect |
| Deterministic close-up head-crop builder | Built | Gives close-ups without new generation |
| **img2img edge unification** | **Rejected with evidence** | Do not retry. Measured identity drift; hallucinates at cfg 1.0. |

Adopting the rejection is as valuable as adopting the techniques — it saves
re-running a proven-bad experiment.

---

## Reusable style reference

`visual_references/mango-pier/` — 20 panels, 8 pages, cover.

**Take:** colour treatment, line weight, flat-fill-plus-cel-shading rendering,
character finish, palette discipline, general mood, typography direction.

**Do not take:** front-facing row staging, eye-level-everything camera, blob
crowd extras, baked-in logo bars, baked-in name labels, baked-in frames.

---

## Not salvageable

| Element | Why |
|---|---|
| All 24 legacy panel images | 19 are draft composites; 5 are non-panels. Nothing is finished art. |
| The 8 assembled legacy pages | Built from the above, with `DRAFT COMPOSITE` headers visible. |
| Legacy cover | Draft tier. |
| Legacy QA report | Its `PASS` verdict is evidence of gate failure, not of quality. Retained as evidence only. |
| Legacy `.workflow-status.json` approvals | Record approvals of draft-tier work as `release`. Retained as evidence. |
| `page_panel_plan.json` panel list | Contradicts the script; never reconciled. |
| Legacy export PDFs and CBZ | Contain the above. |

---

## Salvage arithmetic

| Disposition | Panels | Share |
|---|---|---|
| KEEP | 0 | 0% |
| KEEP_WITH_MINOR_REPAIR | 0 | 0% |
| RECOMPOSE | 7 | 29% |
| RENDER_NEW_CHARACTERS | 7 | 29% |
| RENDER_NEW_BACKGROUND | 0 | 0% |
| REBUILD | 4 | 17% |
| REMOVE | 6 | 25% |

No panel survives as artwork. What survives is the **writing, the asset library
and the method** — which is the majority of the value, and the part that is
hardest to recreate.
