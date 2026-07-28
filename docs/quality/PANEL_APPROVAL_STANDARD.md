# Panel Approval Standard

How a single panel is scored, what has to be true before it can be approved, and
who is allowed to approve it.

## Scope

| Document | Answers |
|---|---|
| `QUALITY_STANDARD.md` | What to look at, at every level from character to issue |
| `DEFECT_TAXONOMY.md` | What to call a defect once it is found, and how bad it is |
| `APPROVAL_WORKFLOW.md` | Who approves an issue, where the record lives, how it is withdrawn |
| **This document** | How one panel is scored and what state it is in right now |

This document adds a scoring instrument and a per-panel state machine. It does
not restate the checklists, redefine any severity, or create a second approval
record. The issue-level gates in `APPROVAL_WORKFLOW.md` remain the only place an
issue is approved.

---

## The score cannot approve anything

`ADR-005` rejects numeric quality scoring as an approval gate, in these words:

> A score is a machine saying yes in a different font.

That decision stands. The rubric below is reconciled with it as follows.

1. **The score is assigned by a human reviewer**, working from the artwork and
   the review package. Nothing in this repository computes it.
2. **The score is necessary, never sufficient.** A passing score is one of three
   independent conditions. It authorises nothing on its own.
3. **A machine may use the score to reject.** It may never use it to approve.
   This is the same rule as everywhere else in the system.

If the rubric is ever automated, the automation may only produce
`CHANGES_REQUIRED`. It may not produce `APPROVED`, and it may not produce a
score that a human then rubber-stamps.

---

## The rubric

100 points across nine dimensions.

| # | Dimension | Points | What the points are for |
|---|---|---:|---|
| 1 | Character identity | 20 | Every character is unmistakably themselves, against approved reference |
| 2 | Anatomy | 20 | Correct structure — limbs, hands, feet, faces, joints |
| 3 | Natural placement | 15 | The character occupies the scene rather than sitting in front of it |
| 4 | Perspective and scale | 10 | Figures agree with the plate's camera and with the declared `scale_note` |
| 5 | Expression and acting | 10 | The performance matches `expression_id`, `eye_line`, `hand_activity` and the beat |
| 6 | Composition | 10 | The frame directs the eye, the balloon zone is clear, nothing is baked in |
| 7 | Lighting and integration | 5 | Key direction, key colour, spill, rim and shadows agree with the script |
| 8 | Story clarity | 5 | `narrative_purpose` and `visual_beat` are visible without the balloons |
| 9 | Continuity | 5 | Location, props, wardrobe and time of day match their bibles and neighbours |
| | **Total** | **100** | |

Identity and anatomy carry 40 points between them because they are the two
things the previous system got wrong on the page that shipped.

### How points come off

Deduct against the checklists in `QUALITY_STANDARD.md`. Every deduction names a
defect code from `DEFECT_TAXONOMY.md`, or says plainly that no code exists.
A deduction with no reason recorded is not a deduction — restore the points or
write the reason.

Round nothing. Nine dimensions of whole numbers is precise enough.

---

## The approval condition

A panel may be approved only when **all three** of the following hold.

| # | Condition |
|---|---|
| A | Score is **95 or above** |
| B | **No open BLOCKER, CRITICAL or MAJOR defect.** A defect that has been formally accepted under `APPROVAL_WORKFLOW.md` §3, with a recorded reason, is not open |
| C | All four hard gates pass |

### The four hard gates

Each gate is binary. Points are irrelevant to it.

| Gate | Passes only when |
|---|---|
| **Identity** | Every character is recognisably themselves; every `required_identifying_features` entry is legible at final size; no `forbidden_changes` violated; no mirrored asymmetric feature |
| **Anatomy** | Correct limb, digit and feature count and structure on every character; no merged, duplicated or malformed parts |
| **Natural placement** | Every character makes the declared ground contact, has a contact shadow, sits at the correct height for its position on the ground plane, and has no cut-out edge or matte halo |
| **Story intent** | The panel's `narrative_purpose` and `visual_beat` are legible from the image alone, with the balloons removed |

### The score never overrides a blocker

**A panel that scores 99 and has one extra hand fails.**

The three conditions are joined by AND, not weighed against each other. There is
no total high enough to buy off `ANAT-LIMB-COUNT`, and no combination of
deductions that turns a blocker into a rounding error. If that trade were
available, the rubric would become the thing it was written to replace: a number
that says the artwork is fine because most of it is.

The same applies in reverse. A panel with no defects at all and a score of 92
is not approved either. It is `CHANGES_REQUIRED` with a short list.

---

## Approval states

One state per panel version.

| State | Meaning | Who may set it |
|---|---|---|
| `UNREVIEWED` | The panel exists. No human has assessed it. The default for anything the pipeline emits | Pipeline or human |
| `REVIEW_REQUIRED` | A complete review package exists and the panel is queued for a reviewer | Pipeline or human |
| `CHANGES_REQUIRED` | Reviewed and rejected. Defects are recorded with codes | **Human, or a machine gate** |
| `APPROVED` | Scored, gated, signed. Releasable | **Human only** |
| `SUPERSEDED` | A later version of this panel was approved, or the panel was cut. The file is kept | Human |

Permitted transitions:

```
UNREVIEWED ──> REVIEW_REQUIRED ──> CHANGES_REQUIRED ──┐
                     │                                │
                     └──────────> APPROVED            │
                                     │                │
                                     v                v
                                 SUPERSEDED    (new version: UNREVIEWED)
```

Rules:

1. **Only a human may assign `APPROVED`.** No script in this repository writes
   it. This is `ADR-005` applied at panel granularity.
2. A machine gate may move a panel to `CHANGES_REQUIRED` at any time, including
   after approval. Machines reject; they do not approve.
3. `APPROVED` names a specific file. A regenerated or re-composited panel is a
   new version starting at `UNREVIEWED`, and the old version becomes
   `SUPERSEDED` — it is not overwritten.
4. Absence of a state means `UNREVIEWED`. There is no default-approve path.
5. Panel approval is a **prerequisite** for the issue-level Final approval gate
   in `APPROVAL_WORKFLOW.md`, not a substitute for it. Approving every panel
   does not approve the issue.

### Mapping to what the code writes today

`app/adapters/comfy_client.py` `write_job_manifest()` writes
`"review_status": "candidate"`, `"reviewed_by": ""`, `"review_note": ""` into
every job manifest. `candidate` means `UNREVIEWED`. Nothing in the codebase ever
writes any other value into that field, which is the correct behaviour.

### Where the record goes

| Record | Path | Exists today |
|---|---|---|
| Per-panel score and state | `issues/<issue>/12_qa/panel-reviews/<panel_id>.yaml` | **No — not yet created** |
| Defect log | `issues/<issue>/12_qa/defects.csv` | **No — not yet created for issue-001** |
| Issue-level approvals | `issues/<issue>/13_approved/approval-record.yaml` | Per `APPROVAL_WORKFLOW.md` |

The panel review record carries: `panel_id`, the version's file path, its
`sha256`, the nine dimension scores, the total, the four gate results, the state,
the reviewer's name and the date.

**Hash the delivered file, not a regeneration.** Experiment 006 established that
this environment is bit-deterministic at the pixel level but not at the file
level: an identical graph and seed produced `pixel_sha256` matches with
`mean_abs_pixel_diff 0.0`, while the file hashes differed because ComfyUI embeds
the prompt graph — including the `SaveImage` filename prefix — in a PNG text
chunk. Approval hashes the artefact on disk. Reproduction checks compare
`pixel_sha256`.

---

## The review package

What the pipeline produced for `ISSUE001-P16-02`, at
`issues/issue-001-neonblue-the-last-light-of-summer/12_qa/review-packages/ISSUE001-P16-02/`:

| File | Dimensions | What it shows | What it does not settle |
|---|---|---|---|
| `placement_report.json` | 714 bytes | Per-character `centre_x`, `foot_y`, rendered px, depth plane, scale multiplier, top-left; plus compositor warnings | `warnings: []` means nothing was flagged. It is not evidence that the `NO_FLIP` or `NON_STANDING_POSES` guards fired |
| `readability_final_size.png` | 429×459 | The panel resampled to 0.28× — a screen reading size | Not print size. `QUALITY_STANDARD.md` asks for final *print* size |
| `composition_grayscale.png` | 960×1024, mode L | Tonal read with colour removed | Made at generation size, not at the delivered 1534×1642 |
| `crop_face_neonblue.png` | 420×315 | NeonBlue's face at 1:1 from the panel | No approved reference sheet beside it |
| `crop_face_moodz.png` | 420×263 | Moodz's face at 1:1 from the panel | No approved reference sheet beside it |
| `crop_contact_neonblue.png` | 420×180 | NeonBlue's feet on the floor plane | — |
| `crop_contact_moodz.png` | 420×180 | Moodz's feet on the floor plane | — |
| `evidence_contact_shadow.jpg` | 1140×346 | Side-by-side shadows OFF / shadows ON at the contact region | **JPEG.** Lossy evidence for a defect class judged on soft edges |
| `closeup_neonblue_from_panel.png` | 900×571 | NeonBlue enlarged from the panel | Derived by crop. Not an independently generated close-up panel |

### Gaps in the package

Required for a reviewer to complete this standard, and currently absent:

1. **The delivered composite itself.** It lives at
   `09_composites/ISSUE001-P16-02_composite_v1.png`, outside the package.
2. **The approved reference sheet** for each character in frame. Without it,
   identity and palette are judged from memory.
3. **The job manifest and plate calibration** for the panel — prompt, negative,
   seed, model, sampler, steps, cfg, ground plane, light contract.
4. **The panel script excerpt**, so the reviewer is not switching between a
   3,600-line YAML file and the artwork.
5. **A print-size readability render.**
6. **The defect log**, which does not exist for this issue.

### The package is not reproducible

Nothing in this repository builds it. A search for `crop_contact`,
`readability_final`, `composition_grayscale` and `placement_report` across all
Python and Markdown returns no hits outside the output directory itself. The
package was assembled by hand during the production run. Until a tool builds it,
the next panel's package will differ from this one, and the standard will be
applied to different evidence each time.

---

## Worked example — ISSUE001-P16-02

Draft scoring, prepared for a human reviewer. **This is not an approval and no
approval record has been written.**

| | |
|---|---|
| Panel | `ISSUE001-P16-02` |
| File | `issues/issue-001-neonblue-the-last-light-of-summer/09_composites/ISSUE001-P16-02_composite_v1.png` |
| Delivered size | 1534×1642 — matches `final_panel_px` in the exp002 manifest |
| Characters | MZ-CHAR-005 NeonBlue, MZ-CHAR-001 Moodz |
| Method | Approved true-alpha layers composited onto a generated plate. No diffusion touched the figures |
| State entering review | `REVIEW_REQUIRED` |

### What the script asks for

From `03_script/panel-script.yaml`:

- `narrative_purpose`: Moodz removes the obligation rather than issuing an instruction
- `visual_beat`: Moodz closer now, still not touching him
- `location`: `LOC-festival-service-corridor`
- NeonBlue — frame left, **side-on to camera, back near the wall**; `eye_line` at Moodz; **one hand still against the wall**; `expression_id` `EXP-005-sad`
- Moodz — frame right, a clear step further from camera, facing NeonBlue; `eye_line` level at NeonBlue; hands at his sides; `expression_id` `EXP-001-neutral`; `scale_note` **8 percent smaller than NeonBlue**
- `lighting.key_direction`: overhead red practical, between and slightly behind them; `key_color` deep red-orange; red rim on the inner shoulder of each figure
- `lighting.contact_shadow`: hard, on grating — **shadow shape must follow the grating pattern**

### What was delivered

From `placement_report.json`, the composite, and the crops:

| Observation | Evidence |
|---|---|
| Both characters standing, both feet flat on the floor plane | `crop_contact_neonblue.png`, `crop_contact_moodz.png` |
| Contact shadow present under both; it darkens the floor grid beneath it | `evidence_contact_shadow.jpg` — grid lines dim in the ON frame |
| Shadow measured, not eyeballed: 13252 px changed, bbox x[226–434] y[864–994], max delta 146.3 | `PANEL_PRODUCTION_LOOP_REPORT.md` §3 |
| Scale falls off with depth | NeonBlue 314 px at `foot_y` 930; Moodz 245 px at `foot_y` 820 |
| No mirroring; Moodz's blue accent on the canon side | `NO_FLIP` guard in `compositor.py`; exp005 report logs the refusal |
| Layer used for NeonBlue: `neonblue_16_worried.png` | `placement_report.json` |
| Layer used for Moodz: `moodz_00_clean_base.png` | `placement_report.json` |
| Both figures face camera. Neither looks at the other | `readability_final_size.png` |
| NeonBlue stands on open floor, no hand on the wall | `readability_final_size.png` |
| Plate reads cyan-keyed; the red in frame comes from wall door panels, not an overhead practical | `readability_final_size.png` |
| Contact shadow outline is a soft ellipse | `compositor.py` `contact_shadow()` — ellipse plus Gaussian blur |

Two arithmetic checks a reviewer can repeat:

```
Moodz height / NeonBlue height = 245 / 314 = 0.780
  Delivered: Moodz is 22.0% smaller.  Script scale_note: 8 percent smaller.

Delivered / composited canvas = 1534 / 960 = 1.598 ,  1642 / 1024 = 1.604
  The panel meets its layout dimensions by a ~1.6x LANCZOS resample of a
  960x1024 composite, not by native render. No upscale models are installed.
```

### Defects

Draft entries. Not yet written to `12_qa/defects.csv`, which does not exist.

| Code | Severity | Where | What |
|---|---|---|---|
| `ASSET-UNAPPROVED` | BLOCKER | Panel | The plate is an unapproved experiment output used in a composite. It is a test plate, not the approved `LOC-festival-service-corridor` location |
| `INTEG-SCALE` | CRITICAL | Both figures | Delivered depth separation is 22.0%, against a declared 8%. Recorded at the taxonomy default; a reviewer may downgrade if the corridor door-frame reference checks out and the script's number is the wrong one |
| `STAGE-EYELINE` | MAJOR | Both figures | Both face camera. The script requires mutual gaze. Root cause: the layer library holds only front-facing turnarounds |
| `STAGE-POSE-MISMATCH` | MAJOR | NeonBlue | Front-on, not side-on; standing on open floor, not back near the wall; no hand against the wall |
| `STAGE-EXPRESSION-MISMATCH` | MAJOR | NeonBlue | `neonblue_16_worried` substituted for `EXP-005-sad`. `expression-coverage.csv` records `EXP-005-sad` as `approved_layer_exists: no` |
| `STAGE-EXPRESSION-MISMATCH` | MAJOR | Moodz | `moodz_00_clean_base` substituted for `EXP-001-neutral`. `expression-coverage.csv` records `EXP-001-neutral` as `approved_layer_exists: no` |
| `INTEG-LIGHT-COLOR` | MAJOR | Both figures | Key colour set to the plate's cyan, not the script's deep red-orange. Deliberate in exp005 to match the plate — but the plate is the wrong plate |
| `IDENT-PALETTE-DRIFT` | MAJOR | Both figures | Residual desaturation after relight. Recorded at default severity; proposed downgrade to MINOR because hue is correct and only saturation is reduced. **Cannot be settled — the review package holds no approved reference sheet** |
| *(no code exists)* | — | Both figures | Contact shadow is present and correctly multiplied over the floor, but its outline is a soft ellipse. The script requires the shadow shape to follow the grating pattern. `DEFECT_TAXONOMY.md` has `INTEG-NO-CONTACT-SHADOW` for absence and nothing for wrong shape |

### Score

| # | Dimension | Available | Awarded | Deduction reasoning |
|---|---|---:|---:|---|
| 1 | Character identity | 20 | **17** | −3. Both unmistakable: NeonBlue's white/cyan spike crown and under-eye bags, Moodz's fringe and blue accent on the canon side. No mirroring. Deducted for residual desaturation against the canon palette |
| 2 | Anatomy | 20 | **20** | −0. The figures are approved alpha layers composited unaltered. No generative model touched a hand, a face or a limb. Nothing to deduct |
| 3 | Natural placement | 15 | **11** | −4. Ground contact, contact shadow and ground-plane height all verified. Deducted for the shadow outline ignoring the grating and for NeonBlue standing on open floor with no wall contact |
| 4 | Perspective and scale | 10 | **6** | −4. Camera is eye-level as scripted and one-point perspective is consistent, but the figure-to-figure scale relationship is 22.0% against a declared 8% |
| 5 | Expression and acting | 10 | **3** | −7. Neither scripted expression has an approved layer; both were substituted. No eye contact in a two-hander built on eye contact. Retained 3 because Moodz's hands-at-sides is correct and carries the "not touching him" beat |
| 6 | Composition | 10 | **7** | −3. Balloon zone upper-centre is clear of both faces; no baked frame, text or logo. Deducted because the vanishing point is dead centre in a near-symmetrical corridor, so the architecture takes the eye before the characters do, and because line weight at final size is a ~1.6× resample rather than native |
| 7 | Lighting and integration | 5 | **2** | −3. Contact and cast shadows exist and were measured. Key colour disagrees with the script, no red rim on either inner shoulder, no red overhead practical in frame |
| 8 | Story clarity | 5 | **1** | −4. With the balloons removed, a reader sees two characters standing apart facing the camera. "Moodz removes the obligation" is not visible. Retained 1 for the correct non-touching distance |
| 9 | Continuity | 5 | **0** | −5. Wrong location plate; the floor is a tiled grid, not the scripted grating; no red overhead practical. Continuity against neighbouring panels cannot be assessed because no neighbouring panel has been produced |

```
17 + 20 = 37
37 + 11 = 48
48 +  6 = 54
54 +  3 = 57
57 +  7 = 64
64 +  2 = 66
66 +  1 = 67
67 +  0 = 67
                                        TOTAL  67 / 100
```

### Gates

| Gate | Result | Why |
|---|---|---|
| Identity | **PASS** | Both characters recognisable; identifying features legible at 1:1; no canon feature mirrored |
| Anatomy | **PASS** | Approved layers composited unaltered |
| Natural placement | **PASS** | Declared ground contact made, contact shadow present, height correct for position on the plane, no cut-out edge or halo |
| Story intent | **FAIL** | The `visual_beat` is not legible without the dialogue |

### Verdict

| Condition | Required | Actual | Met |
|---|---|---|---|
| A — Score | ≥ 95 | 67 | **No** |
| B — Defects | No open BLOCKER / CRITICAL / MAJOR | 1 BLOCKER, 1 CRITICAL, 6 MAJOR | **No** |
| C — Gates | All four pass | Story intent fails | **No** |

**State: `CHANGES_REQUIRED`.**

All three conditions fail independently, which is worth stating because it is
the point of the instrument. Suppose every deduction above were argued away and
the panel scored 99. It would still be `CHANGES_REQUIRED`, because the plate is
an unapproved asset and that is a BLOCKER. The score is not a bank balance the
blocker can be paid out of.

### What has to change

In dependency order:

1. Produce and approve a `LOC-festival-service-corridor` plate. This clears the
   BLOCKER and very likely the `INTEG-LIGHT-COLOR` MAJOR with it, since the key
   colour was matched to the wrong plate.
2. Generate `EXP-005-sad` and `EXP-001-neutral` layers, or revise the script to
   the expressions that exist.
3. Solve eye-line direction. `PANEL_PRODUCTION_LOOP_REPORT.md` §4 records this
   as unsolved and it blocks every two-character conversation in the issue.
4. Re-check the 8% figure in the script's `scale_note` against the corridor door
   frame, and correct whichever is wrong.
5. Render at 1534×1642 natively, or record an accepted reason for the resample.
6. Add the approved reference sheets to the review package so the palette
   question can be settled rather than deferred.

---

## Limits of this standard

Stated plainly, in the same spirit as the report this instrument came from.

1. **It has been applied once, to one panel, by one reviewer.** No calibration
   between reviewers has been attempted. Two people scoring the same panel today
   would not produce the same total.
2. **Nine dimensions of subjective judgement do not become objective by summing
   to 100.** The gates carry the weight. The score is a structured way of writing
   down where a panel is weak, not a measurement.
3. **`DEFECT_TAXONOMY.md` has no code for a contact shadow of the wrong shape.**
   The worked example ran into this immediately. Codes should be added by the
   documented process, not invented at review time.
4. **The review package is not built by any tool** and is missing the reference
   sheets, the composite, the manifest and a print-size render.
5. **The 95 threshold is not empirically derived.** It comes from the brief. It
   is a floor to be defended, not a finding.
6. **One of ten required panel types has been validated.** Nothing in this
   document changes the overall status recorded in
   `PANEL_PRODUCTION_LOOP_REPORT.md`: `PANEL PIPELINE PARTIALLY WORKING`.
