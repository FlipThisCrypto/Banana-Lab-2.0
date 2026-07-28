# Moodz — Identity Checklist

`MZ-CHAR-001` · slug `moodz` · written 2026-07-28 · **status: draft, not owner-approved**

Run this against every panel containing Moodz, at final print size, before the
panel leaves QA. It is the character-specific instance of the Character QA
section of `docs/quality/QUALITY_STANDARD.md`. Defect codes come from
`docs/quality/DEFECT_TAXONOMY.md`.

Moodz's identity is **asymmetric**. That makes one check on this list more
important than all the others, and it is the check the pipeline has already
failed once.

---

## 0. Before you check anything

| Question | Required answer | If not |
|---|---|---|
| Was the character produced by `approved_layer_composite`? | Yes | `PROC-NO-PROVENANCE`. Text-to-image Moodz is off-model by construction — see `generation-profile.yaml` → `generation_method.rationale` |
| Which layer file? | A named file from `source_material/imported_canon/character_layers/moodz/` | `ASSET-AMBIGUOUS-SOURCE` |
| Is there a placement report with `centre_x`, `foot_y`, `scale_multiplier`? | Yes | `PROC-NO-PROVENANCE` |
| **Was `flip` requested anywhere in the staging spec?** | **No.** If yes, confirm the compositor refused it and logged `CANON:` | `IDENT-CANON-VIOLATION`, BLOCKER |

---

## 1. THE MIRROR CHECK

**Do this first. It is the only one that has already gone wrong in production.**

| Check | Fails as | Severity |
|---|---|---|
| The blue hair accent is on the **viewer-left** side of the head | `IDENT-CANON-VIOLATION` | **BLOCKER** |
| The black fringe covers the **viewer-left** eye | `IDENT-CANON-VIOLATION` | **BLOCKER** |
| The compositor emitted no `CANON:` warning, or emitted one and the flip did not happen | `IDENT-CANON-VIOLATION` | **BLOCKER** |

Measured basis (this audit): the horizontal centroid of blue-accent pixels sits
at **0.25–0.45** of the silhouette width in all seventeen front-facing alpha
layers, where 0.0 is the viewer-left edge. It sits at 0.54 — centred — only in
`moodz_30_backview.png`, which is consistent with a rear view. There is no
front-facing layer in which the accent is on the right.

Enforcement in code:

```
NO_FLIP["MZ-CHAR-001"] = "black fringe over one eye, blue accent on the left"
```

`app/services/compositor.py` refuses the flip and warns. Verify the guard fired
rather than assuming it did; a hand-edited composite bypasses it entirely.

---

## 2. Required identifying features

All four are `must not change` in the bible. All four must be **legible at final
print size**, not merely present in the source layer.

| # | Feature | Fails as | Severity |
|---|---|---|---|
| 1 | Black emo fringe sweeping over one eye — the viewer-left eye | `IDENT-MISSING-FEATURE` | CRITICAL |
| 2 | Blue hair accent — streak, headband or beanie, measured `#224B9B` | `IDENT-MISSING-FEATURE` | CRITICAL |
| 3 | Grey eye rings | `IDENT-MISSING-FEATURE` | CRITICAL |
| 4 | Stitched pale chest panel | `IDENT-MISSING-FEATURE` | CRITICAL |

**Feature 1 has a known exception inside the approved art itself.**
`moodz_15_laughing.png` was inspected during this audit: it uses the blue beanie
variation with a **straight, symmetric fringe that does not cover either eye**.
The beanie is explicitly permitted by the bible; the missing asymmetric fringe
is not. Using that layer means shipping a panel that fails check 1. Record it,
do not quietly pass it. See `known-failures.md` KF-MZ-06.

**Features 3 and 4 are the smallest details on the character.** At the one
tested scale Moodz rendered 245 px tall in a 960×1024 working space. Check them
on the delivered panel, not on the source layer.

---

## 3. Forbidden changes

| Check | Fails as | Severity |
|---|---|---|
| No glasses have been added | `IDENT-CANON-VIOLATION` | BLOCKER |
| The character has not been mirrored (§1) | `IDENT-CANON-VIOLATION` | BLOCKER |
| No required identifying feature has been restyled, recoloured or moved | `IDENT-CANON-VIOLATION` | BLOCKER |

---

## 4. Palette

Hex values below were measured from the approved alpha layers during this audit.
The bible records colour **names only** — no hex.

| Swatch | Hex | Where |
|---|---|---|
| Black | `#000000` | outlines, jacket, pants, hair/fringe (44% of opaque pixels) |
| Pale grey | `#E0E0E0` | face, muzzle, stitched chest panel |
| Chocolate brown | `#534739` | fur, ears, tail — and the jacket on six layers, see §5 |
| Blue accent | `#224B9B` | hair streak / headband / beanie |
| Mid grey | `#8F8F8F` | eye rings, studs, platform boot soles |

| Check | Fails as | Severity |
|---|---|---|
| No colour outside this palette on the character | `IDENT-PALETTE-DRIFT` | MAJOR |
| No trace of the orange card background `#EB8E4F` on or around him | `INTEG-MATTE-HALO` | MAJOR |
| Relight has not desaturated the flat fills | `INTEG-LIGHT-COLOR` | MAJOR |

The orange halo risk is materially higher for Moodz than for NeonBlue —
`moodz_00_clean_base.png` measures 1 740 opaque pixels within ΔRGB 60 of the
card orange, against 23 for `neonblue_27_defeated.png`. Check the tail and the
outer silhouette specifically.

---

## 5. Wardrobe

Bible text: open black studded leather jacket, black studded pants, black
studded wrist cuffs, grey platform boots.

**Known art/art disagreement — this is a continuity check, not just an identity
check.** Measured torso-region brown coverage splits the eighteen layers:

| Group | Layers | Torso brown px |
|---|---|---|
| Brown jacket | `00_clean_base`, `10_walking`, `16_worried`, `18_sleepy`, `19_determined`, `24_thinking` | 5 200 – 8 600 |
| Black jacket | `15_laughing`, `17_disgusted`, `20_confused`, `21_running`, `22_jumping`, `23_waving`, `25_crouching`, `26_reaching`, `28_celebrating`, `29_lookingup`, `30_backview` | 0 – 1 400 |
| Intermediate | `27_defeated` | 2 175 |

| Check | Fails as | Severity |
|---|---|---|
| Garments match the source layer, unmodified | `IDENT-WARDROBE-DRIFT` | MAJOR |
| **All Moodz layers used within one scene come from the same jacket group** | `ISSUE-CONTINUITY` | MAJOR |
| Studs, cuffs and boot detail survive the final downscale | `PANEL-READABILITY` | MAJOR |

`moodz_00_clean_base.png` — the named primary production reference and the layer
used in the one panel produced this run — is in the **brown** group, i.e. the
group that disagrees with the bible. Do not repaint the art. Flag it.

---

## 6. Anatomy and proportion

House style: chibi, roughly 1:2 head-to-body, huge white oval eyes with small
dark pupils, mitten hands, simplified feet, visible stitch seams
(`canon/style/HOUSE_STYLE.md` §1).

| Check | Fails as | Severity |
|---|---|---|
| Proportions unchanged from the source layer | `IDENT-PROPORTION-DRIFT` | MAJOR |
| Limb count correct, no merged or duplicated parts | `ANAT-LIMB-COUNT` / `ANAT-MERGE` | BLOCKER / CRITICAL |
| Hands and feet intact after erode and downscale | `ANAT-HANDS` / `ANAT-FEET` | CRITICAL / MAJOR |

In a pure layer composite these should be structurally impossible to fail — the
art is not being regenerated. They stay on the list because inpaint repair and
any future ControlNet path would reintroduce the risk, and neither has been
executed yet.

---

## 7. Pose and ground contact

| Check | Fails as | Severity |
|---|---|---|
| The layer's pose matches the panel's staging description | `STAGE-POSE-MISMATCH` | MAJOR |
| Ground contact matches the pose's **real** contact point, not its filename | `INTEG-NO-GROUND-CONTACT` | CRITICAL |
| `contact_offset` is non-zero for any pose whose contact point is not the soles | `INTEG-NO-GROUND-CONTACT` | CRITICAL |

**Trust the image, not the slug.** `moodz_25_crouching.png` was inspected during
this audit and is **standing**, despite its filename and despite `crouching`
being in the compositor's `NON_STANDING_POSES`. The guard will warn on it
incorrectly. See `known-failures.md` KF-MZ-05.

Moodz has **no usable seated layer**: `moodz_12_sitting.png` exists only as flat
RGB with no alpha.

---

## 8. Integration with the plate

| Check | Fails as | Severity |
|---|---|---|
| Scale agrees with the plate's named ground-plane reference | `INTEG-SCALE` | CRITICAL |
| Perspective agrees with the plate camera | `INTEG-PERSPECTIVE` | CRITICAL |
| Contact shadow present at the contact point | `INTEG-NO-CONTACT-SHADOW` | CRITICAL |
| Cast shadow direction agrees with the declared key | `INTEG-NO-CAST-SHADOW` | CRITICAL |
| Light colour on the character agrees with the plate's practical sources | `INTEG-LIGHT-COLOR` | MAJOR |
| Edge is clean — no halo, no hard cut-out read | `INTEG-MATTE-HALO` / `INTEG-CUTOUT-EDGE` | MAJOR / CRITICAL |

Shadows on a dark plate must be verified **numerically**, not by eye. The one
validated panel used a pixel-difference measurement: 13 252 pixels changed,
bbox `x[226-434] y[864-994]`, max delta 146.3. Note that this measurement covers
the **NeonBlue** contact region (expected near `y=930, x≈330`). No equivalent
numeric verification of Moodz's own contact shadow at `foot_y 820, centre_x 660`
is recorded anywhere. Evidence file:
`issues/issue-001-neonblue-the-last-light-of-summer/12_qa/review-packages/ISSUE001-P16-02/evidence_contact_shadow.jpg`.

---

## 9. Performance

| Check | Fails as | Severity |
|---|---|---|
| Expression matches the beat, not just the character | `STAGE-EXPRESSION-MISMATCH` | MAJOR |
| Eye direction matches the declared eye line | `STAGE-EYELINE` | MAJOR |

**The eye-line check cannot currently be passed by construction.** Seventeen of
the eighteen alpha layers are front-facing; the eighteenth is a back view. Eye
direction cannot be directed. Any panel whose script requires Moodz to look at
another character should be recorded as a known open defect rather than signed
off. See `known-failures.md` KF-MZ-03.

---

## 10. Cleanliness

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
| Layer used | `moodz_00_clean_base.png` |
| Panel types validated | 1 of 10 required |
| Runs of that type | 1 of 3 required |

Sections 6 (inpaint/ControlNet risk), 8 (occlusion, and Moodz's own shadow
measurement), and 9 (eye line) have never been exercised against a passing case.
Do not read this document as evidence that they work.
