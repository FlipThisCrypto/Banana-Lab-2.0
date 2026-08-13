# Banana Lab 2.0 Quality Standard

## The rule this document exists for

**A machine gate may only reject. It may never approve.**

The previous system's QA report for Issue 001 read `VERDICT: PASS`, with
`Evidence blockers: None`. Its entire per-panel check was, twenty-four times:

```
- MZ-2026-08-01_P01_PANEL01: present; PNG; 1280x960; no file error
```

It tested file existence, format and dimensions. A tiled wallpaper pattern
passes that test. So do five off-model pink figures. Both shipped.

Everything below follows from that. Automated checks find defects. A human
decides whether an issue is good.

**Automated PASS does not authorize production.** After the measurable gates,
a human visual review must also pass. That review judges whether the panel
*works visually* as a comic, not whether it matches one reference crop or
clears a scorecard. Standard: `VISUAL_QUALITY_REVIEW.md`.

---

## Severity

| Severity | Meaning | Blocks release |
|---|---|---|
| `BLOCKER` | The asset is not what it claims to be, or a hard canon rule is broken | Yes |
| `CRITICAL` | A load-bearing story or identity element is wrong or absent | Yes |
| `MAJOR` | Craft failure a reader will notice | Yes |
| `MINOR` | Craft failure a careful reader might notice | No, but recorded |
| `COSMETIC` | Preference or polish | No |

**No issue may be marked production-ready with an unresolved BLOCKER, CRITICAL
or MAJOR defect.** A defect may be *accepted* rather than fixed, but acceptance
is a human decision with a recorded reason.

Taxonomy: `DEFECT_TAXONOMY.md`. Process: `APPROVAL_WORKFLOW.md`.

---

## Character QA

Per character, per panel.

### Identity
- [ ] Recognisably this character against approved reference
- [ ] Face structure, eye design, mouth, ears correct
- [ ] Fur or skin colour within the character's palette
- [ ] Hair shape and colour correct
- [ ] Clothing correct, unchanged, undamaged unless scripted
- [ ] Accessories present
- [ ] Every `required_identifying_features` entry legible at final print size
- [ ] No `forbidden_changes` violated

### Anatomy
- [ ] Body proportions match the character bible
- [ ] Hands correct — count, structure, and what they are holding
- [ ] Feet correct and consistent with the declared ground contact
- [ ] Limb count and joint direction correct
- [ ] No duplicated or merged body parts

### Performance
- [ ] Pose matches the panel's `pose_id` or staging description
- [ ] Expression matches the panel's `expression_id`
- [ ] Expression fits the dialogue and the beat, not just the character
- [ ] Eye direction matches the declared `eye_line`

### Integration
- [ ] Scale consistent with the declared `scale_note` and a named plate reference
- [ ] Perspective matches the plate's camera
- [ ] Ground contact matches `ground_contact` exactly
- [ ] Contact shadow present, correctly shaped for the surface
- [ ] Cast shadow direction agrees with the declared key light
- [ ] Light direction on the character matches `lighting.key_direction`
- [ ] Light colour matches `lighting.key_color`
- [ ] Environmental colour spill present where declared
- [ ] Edge quality clean — no matte halo, no hard cut-out edge
- [ ] Occlusion correct where declared
- [ ] Focal softness consistent with depth plane

### Cleanliness
- [ ] No duplicate artifacts
- [ ] No unwanted objects
- [ ] **No text of any kind** — no labels, catalogue numbers, watermarks, logos

---

## Panel QA

### Story
- [ ] The panel's `narrative_purpose` is achieved by the image
- [ ] The `visual_beat` is visible, not merely captioned
- [ ] A reader who could not read the balloons would still get the beat

### Craft
- [ ] Composition directs the eye to the subject
- [ ] Camera shot and angle match the script
- [ ] Staging is natural — no lineup, no equal-scale row
- [ ] Perspective consistent across all elements
- [ ] Lighting consistent across all elements
- [ ] Depth reads as three planes where `depth_plan` says so
- [ ] Cropping deliberate
- [ ] Readable at final print size

### Continuity
- [ ] Props match their prop bible
- [ ] Location matches its location bible
- [ ] Wardrobe consistent with neighbouring panels
- [ ] Time of day consistent with the light progression

### Defects
- [ ] No repeated elements from a neighbouring panel unless deliberate
- [ ] No garbled objects or broken geometry
- [ ] No background artifacts
- [ ] Balloon zone is clear of faces and hands

### Frameless rule
- [ ] **No panel border rendered into the artwork**
- [ ] **No caption, balloon or SFX rendered into the artwork**
- [ ] **No logo or page furniture rendered into the artwork**

---

## Page QA

- [ ] Reading order unambiguous without arrows or numbers
- [ ] Panel count within the format standard for the page
- [ ] Panel sizes track narrative weight
- [ ] Grid differs from the previous and following page
- [ ] Balance — no page is all-large or all-small
- [ ] Gutters even, margins respected, bleed correct where used
- [ ] Balloon reading order matches the script
- [ ] Balloon tails point unambiguously to their speaker
- [ ] Font and balloon style consistent
- [ ] Dialogue matches `panel-script.yaml` exactly
- [ ] Page-turn beat lands
- [ ] Camera angles not repeated across adjacent panels
- [ ] Character continuity across the page
- [ ] Colour progression matches the issue's light plan
- [ ] Page frame colour correct per the layout spec

---

## Issue QA

- [ ] Story complete and readable with no prior knowledge
- [ ] Featured character's arc lands
- [ ] Every supporting character serves their declared function
- [ ] Continuity map satisfied
- [ ] Every canon restriction in the issue bible respected
- [ ] Dialogue matches the approved script throughout
- [ ] **Page count and panel counts satisfy `canon/rules/FORMAT_STANDARD.md`**
- [ ] Title, credits and cover present
- [ ] Fiend Studios collectible stamp on the cover
- [ ] Export dimensions correct for print and web
- [ ] Print safety — nothing important inside the margin
- [ ] Web readability at target size
- [ ] PDF integrity
- [ ] No missing assets
- [ ] **No unapproved asset used anywhere**
- [ ] No broken references
- [ ] Every asset traceable to approved source via the manifest

---

## What automation checks

`python -m app.cli.main validate` runs the mechanical subset:

| Check | Catches |
|---|---|
| Schema validation | Missing or malformed required fields |
| Panel script validation | Duplicate panel IDs; a character in frame with no staging record |
| Format standard | Page and panel counts, issue average, rhythm rules |
| Manifest integrity | Imported source drifting from its recorded hash |
| Repository hygiene | Secrets, oversized files, machine-specific paths |
| Layout geometry | Overlapping panels, panels escaping the live area, repeated grids, broken reading order |

**None of these look at a picture.** Everything in the character, panel, page
and issue lists above is a human judgement, made against the artwork.

---

## The integration test

The single question that separates this standard from the previous one:

> Does the character look like they are **in** the scene, or **in front of** it?

A panel can pass every identity check and still fail here. The character must
share the scene's ground plane, perspective, light direction, light colour and
atmosphere. If the character could be slid sideways and still look correct, the
panel fails.

This is why `character_blocking` is required per character and why
`ground_contact`, `eye_line` and `scale_note` are mandatory fields. They exist
so QA has something specific to check against, rather than an impression.
