# Defect Taxonomy

Every defect gets a code, a severity and a location. Codes are stable — they are
how defects are counted across issues and how recurring failure modes get
noticed.

Recorded in `issues/<issue>/12_qa/defects.csv`.

## Record format

| Field | Meaning |
|---|---|
| `defect_id` | `DEF-<issue>-<sequence>` |
| `code` | From the tables below |
| `severity` | BLOCKER / CRITICAL / MAJOR / MINOR / COSMETIC |
| `panel_id` | Where it is, or `PAGE-NN` / `ISSUE` |
| `description` | What is wrong, specifically |
| `evidence` | Path to the image or crop showing it |
| `found_by` | Person or check |
| `status` | open / fixed / accepted / rejected |
| `resolution` | What was done, or why it was accepted |

---

## ASSET — the file is not what it claims to be

| Code | Defect | Default severity |
|---|---|---|
| `ASSET-NOT-A-PANEL` | The image is not comic artwork — a pattern, a model sheet, a texture | BLOCKER |
| `ASSET-DRAFT-TIER` | Placeholder or draft composite in an approved slot | BLOCKER |
| `ASSET-WRONG-PANEL` | Correct artwork, wrong panel ID | BLOCKER |
| `ASSET-AMBIGUOUS-SOURCE` | More than one image exists for one panel ID with no single authority | BLOCKER |
| `ASSET-UNAPPROVED` | A `generated_candidates` asset used in a composite | BLOCKER |
| `ASSET-MISSING` | Referenced asset does not exist | CRITICAL |

*All six were present in the legacy Issue 001.*

---

## IDENT — the character is wrong

| Code | Defect | Default severity |
|---|---|---|
| `IDENT-OFF-MODEL` | Not recognisably the character | BLOCKER |
| `IDENT-WRONG-SPECIES` | Wrong creature entirely | BLOCKER |
| `IDENT-CANON-VIOLATION` | A `forbidden_changes` rule broken | BLOCKER |
| `IDENT-MISSING-FEATURE` | A `required_identifying_features` entry absent or illegible | CRITICAL |
| `IDENT-PALETTE-DRIFT` | Colours outside the character's palette | MAJOR |
| `IDENT-WARDROBE-DRIFT` | Clothing changed without script support | MAJOR |
| `IDENT-PROPORTION-DRIFT` | Body proportions off-bible | MAJOR |

---

## ANAT — anatomy

| Code | Defect | Default severity |
|---|---|---|
| `ANAT-LIMB-COUNT` | Wrong number of limbs, fingers or digits | BLOCKER |
| `ANAT-HANDS` | Malformed hands or an unbelievable grip | CRITICAL |
| `ANAT-JOINT` | Impossible joint direction | CRITICAL |
| `ANAT-FACE` | Facial features misplaced or malformed | CRITICAL |
| `ANAT-MERGE` | Body parts merged with each other or the background | CRITICAL |
| `ANAT-FEET` | Feet malformed or inconsistent with declared ground contact | MAJOR |

---

## INTEG — the character does not occupy the scene

The defect class this system exists to catch.

| Code | Defect | Default severity |
|---|---|---|
| `INTEG-NO-GROUND-CONTACT` | The character floats; no contact with the declared surface | CRITICAL |
| `INTEG-NO-CONTACT-SHADOW` | No shadow where the character meets the ground | CRITICAL |
| `INTEG-SCALE` | Scale inconsistent with the plate's named reference | CRITICAL |
| `INTEG-PERSPECTIVE` | Character's perspective disagrees with the plate's camera | CRITICAL |
| `INTEG-LIGHT-DIRECTION` | Light on the character disagrees with the declared key | CRITICAL |
| `INTEG-CUTOUT-EDGE` | Hard cut-out edge; the character reads as pasted | CRITICAL |
| `INTEG-MATTE-HALO` | Light or dark fringe from imperfect background removal | MAJOR |
| `INTEG-LIGHT-COLOR` | Light colour on the character disagrees with the scene | MAJOR |
| `INTEG-NO-CAST-SHADOW` | Cast shadow absent where the light demands one | MAJOR |
| `INTEG-NO-COLOR-SPILL` | No environmental colour on the character where declared | MAJOR |
| `INTEG-OCCLUSION` | Declared occlusion missing or wrong | MAJOR |
| `INTEG-DEPTH-SOFTNESS` | Focal softness inconsistent with depth plane | MINOR |

---

## STAGE — blocking and performance

| Code | Defect | Default severity |
|---|---|---|
| `STAGE-LINEUP` | Characters in a row, front-facing, at equal scale | MAJOR |
| `STAGE-EQUAL-SCALE` | Multiple characters at identical scale with no depth reason | MAJOR |
| `STAGE-EYELINE` | Eye line disagrees with the script or with who is speaking | MAJOR |
| `STAGE-EXPRESSION-MISMATCH` | Expression does not fit the dialogue or the beat | MAJOR |
| `STAGE-POSE-MISMATCH` | Pose disagrees with the script | MAJOR |
| `STAGE-DEAD-CENTRE` | Subject centred with no compositional reason | MINOR |

---

## PANEL — the panel as an image

| Code | Defect | Default severity |
|---|---|---|
| `PANEL-STORY-ABSENT` | The story content is in the caption but not the image | CRITICAL |
| `PANEL-FRAME-BAKED` | A panel border rendered into the artwork | MAJOR |
| `PANEL-TEXT-BAKED` | Text, logo, label or watermark rendered into the artwork | MAJOR |
| `PANEL-GARBLED-OBJECT` | An object in the scene is incoherent | MAJOR |
| `PANEL-BROKEN-GEOMETRY` | Architecture or perspective breaks down | MAJOR |
| `PANEL-BLOB-EXTRAS` | Background people rendered as featureless shapes | MAJOR |
| `PANEL-ARTIFACT` | Generation artifact in the background | MINOR |
| `PANEL-BUBBLE-COLLISION` | Balloon covers a face or a hand | MAJOR |
| `PANEL-READABILITY` | Does not read at final print size | MAJOR |

---

## PAGE — layout and lettering

| Code | Defect | Default severity |
|---|---|---|
| `PAGE-READING-ORDER` | Panel order ambiguous or wrong | CRITICAL |
| `PAGE-DIALOGUE-DRIFT` | Lettered dialogue differs from the approved script | CRITICAL |
| `PAGE-GRID-REPEAT` | Same grid as an adjacent page | MAJOR |
| `PAGE-UNIFORM` | Equal rows of equal panels | MAJOR |
| `PAGE-WEIGHT-MISMATCH` | Panel size does not track narrative weight | MAJOR |
| `PAGE-BUBBLE-ORDER` | Balloons read in the wrong order | MAJOR |
| `PAGE-TAIL` | Balloon tail ambiguous | MAJOR |
| `PAGE-FONT` | Inconsistent lettering style | MINOR |
| `PAGE-GUTTER` | Uneven gutters or violated margins | MINOR |
| `PAGE-FRAME-COLOR` | Page frame colour disagrees with the layout spec | MINOR |

---

## ISSUE — whole-book

| Code | Defect | Default severity |
|---|---|---|
| `ISSUE-CANON-BREACH` | A content restriction in the issue bible violated | BLOCKER |
| `ISSUE-FORMAT` | Page or panel counts outside the format standard | CRITICAL |
| `ISSUE-ARC-INCOMPLETE` | The featured character's arc does not land | CRITICAL |
| `ISSUE-CONTINUITY` | Contradicts the continuity map or an earlier issue | CRITICAL |
| `ISSUE-MISSING-ASSET` | A required deliverable absent | CRITICAL |
| `ISSUE-NO-STAMP` | Fiend Studios collectible stamp missing from the cover | MAJOR |
| `ISSUE-EXPORT` | Export dimensions or colour space wrong | MAJOR |
| `ISSUE-PROVENANCE` | An asset cannot be traced to an approved source | MAJOR |

---

## Process defects

Not defects in the artwork, but in how it was made. Recorded because they
predict artwork defects.

| Code | Defect | Default severity |
|---|---|---|
| `PROC-GATE-SKIPPED` | A stage advanced without its evidence | CRITICAL |
| `PROC-AUTO-APPROVED` | An approval recorded without a human | BLOCKER |
| `PROC-SCRIPT-DRIFT` | Art produced does not match the approved script | CRITICAL |
| `PROC-NO-PROVENANCE` | An asset with no recorded source | MAJOR |
| `PROC-SOURCE-MUTATED` | Imported source material modified in place | BLOCKER |

The legacy Issue 001 record shows `PROC-GATE-SKIPPED`, `PROC-SCRIPT-DRIFT` and
`PROC-NO-PROVENANCE`. Its QA `PASS` on draft-tier art with five non-panels is
the clearest example in the archive of why process defects matter.
