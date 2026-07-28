# NeonBlue — Identity Checklist

`MZ-CHAR-005` · slug `neonblue` · written 2026-07-28 · **status: draft, not owner-approved**

Run this against every panel containing NeonBlue, at final print size, before
the panel leaves QA. It is the character-specific instance of the Character QA
section of `docs/quality/QUALITY_STANDARD.md`. Defect codes come from
`docs/quality/DEFECT_TAXONOMY.md`.

A failed BLOCKER or CRITICAL line means the panel does not ship. There is no
score, no average and no "close enough".

---

## 0. Before you check anything

| Question | Required answer | If not |
|---|---|---|
| Was the character produced by `approved_layer_composite`? | Yes | `PROC-NO-PROVENANCE`. Text-to-image NeonBlue is off-model by construction — see `generation-profile.yaml` → `generation_method.rationale` |
| Which layer file? | A named file from `source_material/imported_canon/character_layers/neonblue/` | `ASSET-AMBIGUOUS-SOURCE` |
| Is there a placement report with `centre_x`, `foot_y`, `scale_multiplier`? | Yes | `PROC-NO-PROVENANCE` |
| Did the compositor emit any warning? | Read them all. A `CANON:` warning is a stop. | `IDENT-CANON-VIOLATION` |

---

## 1. Required identifying features

All four are `must not change` in the bible. All four must be **legible at final
print size**, not merely present in the source layer.

| # | Feature | Fails as | Severity |
|---|---|---|---|
| 1 | White/cyan spike crown — starburst silhouette intact, not clipped by the panel edge or a balloon | `IDENT-MISSING-FEATURE` | CRITICAL |
| 2 | Cyan root glow at the hairline, measured `#29D6DD` | `IDENT-MISSING-FEATURE` | CRITICAL |
| 3 | Heavy grey under-eye bags | `IDENT-MISSING-FEATURE` | CRITICAL |
| 4 | Left-ear silver plug earring — on the character's left, i.e. **viewer-right** when he faces camera | `IDENT-CANON-VIOLATION` if on the wrong side; `IDENT-MISSING-FEATURE` if absent | BLOCKER / CRITICAL |

**Note on feature 4.** `bible.yaml` contradicts itself: `accessories` lists the
earring as `optional`, `features_that_must_never_change` lists it as `defining`.
This checklist takes the stricter reading. Occlusion by hair (as in
`neonblue_27_defeated.png`) is acceptable; relocation is not.

---

## 2. Forbidden changes

| Check | Fails as | Severity |
|---|---|---|
| No glasses have been added | `IDENT-CANON-VIOLATION` | BLOCKER |
| The character has not been mirrored | `IDENT-CANON-VIOLATION` | BLOCKER |
| No required identifying feature has been restyled, recoloured or moved | `IDENT-CANON-VIOLATION` | BLOCKER |

The mirror check is enforced in code — `NO_FLIP["MZ-CHAR-005"]` in
`app/services/compositor.py` refuses the flip and logs a `CANON` warning. Verify
the guard fired rather than assuming it did; a hand-edited composite bypasses it.

---

## 3. Palette

Hex values below were measured from the approved alpha layers during this audit.
The bible records colour **names only** — no hex. Treat these as the reference
until the owner ratifies a swatch sheet.

| Swatch | Hex | Where |
|---|---|---|
| Pale grey | `#E0E0E0` | face, muzzle, belly panel, hair body |
| Near white | `#F5F5F5` | hair highlight, eye whites |
| Jet black | `#000000` | outlines, vest, punk pants |
| Chocolate brown | `#534739` | fur, ears, arms, tail |
| Electric cyan | `#29D6DD` | hair streaks, root glow |
| Mid grey | `#909090` | studs, sneaker panels, under-eye bags |

| Check | Fails as | Severity |
|---|---|---|
| No colour outside this palette on the character | `IDENT-PALETTE-DRIFT` | MAJOR |
| No trace of the green card background `#61DE8E` anywhere on or around him | `INTEG-MATTE-HALO` | MAJOR |
| Relight has not desaturated the flat fills | `INTEG-LIGHT-COLOR` | MAJOR |

The green is not a stylistic risk — it is physically present in the RGB channels
of every layer file underneath `alpha == 0`. See `known-failures.md`.

---

## 4. Wardrobe

Bible text: black vest/tank, white-studded black punk pants, black studded
cuffs, grey-and-black skate sneakers.

**Known text/art disagreement:** in the alpha layers inspected the upper garment
reads as a chocolate-brown jacket over a pale grey stitched chest panel, not a
black vest. This is unresolved. Check the panel against **the approved art**,
not against the bible sentence, and do not "fix" the art toward the text.

| Check | Fails as | Severity |
|---|---|---|
| Garments match the source layer, unmodified | `IDENT-WARDROBE-DRIFT` | MAJOR |
| Studs, cuffs and sneaker detail survive the final downscale | `PANEL-READABILITY` | MAJOR |

---

## 5. Anatomy and proportion

House style: chibi, roughly 1:2 head-to-body, huge white oval eyes with small
dark pupils, mitten hands, simplified feet (`canon/style/HOUSE_STYLE.md` §1).

| Check | Fails as | Severity |
|---|---|---|
| Proportions unchanged from the source layer | `IDENT-PROPORTION-DRIFT` | MAJOR |
| Limb count correct, no merged or duplicated parts | `ANAT-LIMB-COUNT` / `ANAT-MERGE` | BLOCKER / CRITICAL |
| Hands and feet intact after erode and downscale | `ANAT-HANDS` / `ANAT-FEET` | CRITICAL / MAJOR |

In a pure layer composite these should be structurally impossible to fail —
the art is not being regenerated. They stay on the list because inpaint repair
and any future ControlNet path would reintroduce the risk, and neither has been
executed yet.

---

## 6. Pose and ground contact

| Check | Fails as | Severity |
|---|---|---|
| The layer's pose matches the panel's staging description | `STAGE-POSE-MISMATCH` | MAJOR |
| Ground contact matches the pose's real contact point | `INTEG-NO-GROUND-CONTACT` | CRITICAL |
| `contact_offset` is non-zero for any pose in `NON_STANDING_POSES` | `INTEG-NO-GROUND-CONTACT` | CRITICAL |

Non-standing NeonBlue layers: `running` (one foot, mid-stride), `jumping`
(airborne), `crouching`, `defeated` (**seated — contact is the hips**).

`neonblue_27_defeated.png` was visually confirmed during this audit as a seated
pose. It is the failure recorded in `known-failures.md`. NeonBlue has **no
`sitting` layer**; `defeated` is the only seated art available to him.

---

## 7. Integration with the plate

| Check | Fails as | Severity |
|---|---|---|
| Scale agrees with the plate's named ground-plane reference | `INTEG-SCALE` | CRITICAL |
| Perspective agrees with the plate camera | `INTEG-PERSPECTIVE` | CRITICAL |
| Contact shadow present at the contact point | `INTEG-NO-CONTACT-SHADOW` | CRITICAL |
| Cast shadow direction agrees with the declared key | `INTEG-NO-CAST-SHADOW` | CRITICAL |
| Light colour on the character agrees with the plate's practical sources | `INTEG-LIGHT-COLOR` | MAJOR |
| Edge is clean — no halo, no hard cut-out read | `INTEG-MATTE-HALO` / `INTEG-CUTOUT-EDGE` | MAJOR / CRITICAL |

Shadows on a dark plate must be verified **numerically**, not by eye. The one
validated panel used a pixel-difference measurement: 13252 pixels changed,
bbox `x[226-434] y[864-994]`, max delta 146.3, against an expected contact
region near `y=930, x≈330`. Evidence:
`issues/issue-001-neonblue-the-last-light-of-summer/12_qa/review-packages/ISSUE001-P16-02/evidence_contact_shadow.jpg`.

---

## 8. Performance

| Check | Fails as | Severity |
|---|---|---|
| Expression matches the beat, not just the character | `STAGE-EXPRESSION-MISMATCH` | MAJOR |
| Eye direction matches the declared eye line | `STAGE-EYELINE` | MAJOR |

**The eye-line check cannot currently be passed by construction.** Sixteen of
the seventeen alpha layers are front-facing; the seventeenth is a back view.
Eye direction cannot be directed. Any panel whose script requires NeonBlue to
look at another character should be recorded as a known open defect rather than
signed off. See `known-failures.md`.

---

## 9. Cleanliness

| Check | Fails as | Severity |
|---|---|---|
| No text, label, catalogue number or watermark anywhere on the character | `PANEL-TEXT-BAKED` | BLOCKER |
| No panel border or balloon rendered into the art | `PANEL-FRAME-BAKED` | BLOCKER |
| No stray artifacts introduced by compositing | `PANEL-ARTIFACT` | MAJOR |

---

## What this checklist has actually been run against

| Item | Value |
|---|---|
| Panels | 1 — `ISSUE001-P16-02` |
| Panel status | candidate, **not approved** |
| Layer used | `neonblue_16_worried.png` |
| Panel types validated | 1 of 10 required |
| Runs of that type | 1 of 3 required |

Sections 5 (inpaint/ControlNet risk), 7 (occlusion), and 8 (eye line) have never
been exercised against a passing case. Do not read this document as evidence
that they work.
