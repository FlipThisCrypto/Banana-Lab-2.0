# Issue 001 — Approval Checklist

The gates this issue must pass, in order. Each gate is a **human** decision.
Machine validation can fail a gate; it can never pass one.

Approval is recorded in `13_approved/approval-record.yaml`. Nothing else in the
system may write that file.

---

## Gate 1 — Research *(no approval required)*

- [x] Every source located and classified
- [x] Legacy issue compared against the season bible
- [x] Every legacy panel classified in the salvage matrix
- [x] Canon conflicts enumerated with recommended resolutions
- [x] Rebuild recommendation written with an honest status

Complete. Evidence: `01_research/`.

---

## Gate 2 — Issue Bible **(owner approval required)**

- [x] `issue-bible.yaml` validates against `config/schemas/issue.schema.yaml`
- [x] Every named character has a stated function
- [x] Theme, logline and synopsis agree with the season bible
- [x] Title meaning documented as narrative, lighting and plot
- [x] Continuity map lists what is inherited, established and left open
- [x] Character arc map assigns every beat to a page
- [x] Location and prop requirements enumerated with gaps named
- [x] **Owner ruling on C-01** — Echo reveal timing (season bible; 2026-08-13)
- [x] **Owner ruling on C-02** — Lil Devil's guest function (season bible; 2026-08-13)
- [x] Owner approves the issue bible

**Status: approved 2026-08-13.** C-01 and C-02 confirmed as the bible already applied them.

---

## Gate 3 — Script **(owner approval required)**

- [ ] Every panel has a stated narrative purpose
- [ ] No filler panels
- [ ] Panel count matches the bible (27)
- [ ] Dialogue at or under 15 words per balloon, max 2 balloons per panel
- [ ] No invented canon specifics
- [ ] Ash speaks once; Scarline twice
- [ ] Every supporting character has their assigned beat
- [ ] Echo fires only after the choice
- [ ] `panel-script.yaml` validates against the panel schema
- [ ] Panel IDs unique
- [x] Owner approves the script (2026-08-13)

---

## Gate 4 — Storyboards *(no approval required)*

- [ ] Every page thumbnailed
- [ ] Panel count per page varies (not a uniform grid)
- [ ] Reading order unambiguous on every page
- [ ] Panel size reflects narrative weight
- [ ] At least one large anchor panel
- [ ] At least one quiet negative-space panel near the climax
- [ ] Page-turn beats identified

---

## Gate 5 — Layouts **(owner approval required)**

- [x] `layout-spec.yaml` complete for all 22 story pages
- [x] Reading order validated and documented
- [x] Lettering safe zones defined for every panel, sized against the locked font
- [x] No two consecutive pages share a grid
- [x] Gutters, margins and bleed specified
- [x] Pages 7 and 18 use a wider between-row gutter
- [x] Hard orientation/aspect bands enforced (script wins)
- [x] Page 11 locked to recto in the 28-page book
- [x] Balloon zones do not cover faces or hands
- [x] Owner approves layouts (2026-08-13, after Gate 5 geometry fixes)

**No final artwork may be approved before this gate passes.**

---

## Gate 6 — Backgrounds *(no approval required, QA gated)*

- [ ] All four festival plates calibrated (horizon, scale reference, light, ground)
- [ ] Twelve distinct camera setups produced
- [ ] Every plate frameless — no panel borders, no logos, no text
- [ ] Every plate has a staging guide naming where characters stand
- [ ] Palette holds to the location bible
- [ ] Lighting matches the page's position in the light progression

---

## Gate 7 — Character Staging *(no approval required)*

- [ ] Expression coverage assessed against the script
- [ ] Pose coverage assessed against the script
- [ ] Missing assets listed with a production route each
- [ ] Lil Devil alpha layer set produced
- [ ] Per-panel staging plan for every panel with a character in it
- [ ] Every staging plan names ground contact, scale reference, eye line and light direction

---

## Gate 8 — Controlled generation test **(owner approval required)**

Before any bulk generation.

- [ ] Test panel P5-02 produced end to end
- [ ] Both characters recognisable against approved reference
- [ ] Feet meet the floor with correct perspective
- [ ] Contact shadow present and correctly shaped
- [ ] Key light direction matches the corridor practicals
- [ ] No matte halo on character edges
- [ ] Relative scale consistent with a named object in the plate
- [ ] Reads as MonkeyZoo house style beside a Mango Pier panel
- [ ] Owner approves the method

**If this fails, diagnose and correct before generating anything else.**

---

## Gate 9 — Panel QA *(per panel)*

Full standard: `docs/quality/QUALITY_STANDARD.md`. Every panel passes character
QA and panel QA, with no unresolved BLOCKER, CRITICAL or MAJOR defect.

---

## Gate 10 — Page QA *(per page)*

Reading order, rhythm, balance, gutters, bubble order and tails, font
consistency, dialogue accuracy against the script, page-turn effect, camera
variety, character continuity, colour progression.

---

## Gate 11 — Issue QA

- [ ] Story complete and readable without prior knowledge
- [ ] NeonBlue's arc lands
- [ ] Continuity map satisfied
- [ ] Exactly one Echo segment lit
- [ ] Patch unresolved
- [ ] No FusionZoo dating
- [ ] Page count 8, panel count 27
- [ ] Every asset traceable to approved source
- [ ] No unapproved asset used
- [ ] No broken references
- [ ] Print and web export dimensions correct

---

## Gate 12 — Final approval **(owner approval required)**

- [ ] All defects resolved or explicitly accepted with a recorded reason
- [ ] No BLOCKER, CRITICAL or MAJOR defect outstanding
- [ ] Owner signs off

Only after this gate may the issue be described as production-ready.

---

## Current position

**Gate 2, awaiting owner.** Gates 3 through 5 are drafted ahead of approval so
the owner can see where the work is going, but none of them is approved and the
approval record does not exist.
