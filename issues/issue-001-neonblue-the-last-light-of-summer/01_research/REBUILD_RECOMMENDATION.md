# Issue 001 — Rebuild Recommendation

## Recommendation

**Rebuild the artwork completely. Restore the writing to its bible.**

No panel is salvageable as art, so there is no partial-repair path to argue
about. The writing is sound and drifted from the season bible in six specific,
correctable ways. The asset library and the integration method needed to make
the art already exist and are proven on this cast.

This is a production problem, not a creative one.

---

## Why complete art rebuild is the only honest option

1. **There is no art to repair.** 19 of 24 panels are self-labelled draft
   composites; 5 are not comic panels at all. Repairing a placeholder means
   making the panel, so "repair" and "rebuild" are the same work.
2. **Character integration cannot be retrofitted.** The cards are opaque
   rectangles with baked studio lighting. There is no layer to relight, no
   matte to refine, no ground contact to correct. The character has to be
   staged from the alpha library.
3. **The plates cannot carry 20 panels.** Four unchanged plates produced eight
   pixel-identical reuses. New camera angles on the established locations are
   required regardless of what happens to the characters.

## Why the writing should be restored, not rewritten

The legacy script hits every structural beat the season bible specifies. Its
problems are drift — the Echo reveal moved, the guest lost his function, two
contributors dropped out of the climax — not a broken story. Rewriting would
throw away good work and risk new canon violations. The rebuild restores the
bible's version and edits dialogue for balloon length.

---

## The production strategy

The determining technical fact: **there is no MonkeyZoo style LoRA, and the two
installed checkpoints are photoreal and anime.** Text-to-image cannot be trusted
with character identity here. Everything follows from that.

```
Approved character art  ──►  true-alpha layers  ──┐
                                                  ├──►  staged composite  ──►  panel
Approved location plate ──►  new camera angles  ──┘
```

### Characters — from approved art, never from text-to-image

1. Prefer an existing true-alpha layer from the 139-file library.
2. Where none fits, derive a new layer from approved character art:
   background removal, then ControlNet Union pose guidance and IP-Adapter
   reference conditioning against the approved image.
3. Every new layer enters `generated_candidates/`, never `approved/`, and needs
   human review before use.
4. Close-ups come from the deterministic head-crop method, not new generation.

Identity comes from art the owner already approved. The generator is used to
change pose and expression, never to invent a character.

### Backgrounds — new angles on established locations

The four festival plates define what the locations look like. New plates extend
the camera, not the place: derive depth from the approved plate, prompt against
the location `bible.md`, and hold the palette to the location's swatches.

Twelve plates for twenty panels, with deliberate reuse where a scene should read
as one continuous place.

### Compositing — the integration contract

Every panel carries a staging record: ground contact, depth plane, scale against
a named reference object in the plate, eye line, light direction, contact
shadow, cast shadow, colour spill, edge treatment, occlusion. QA checks the
panel against that record. A panel with no staging record cannot be approved,
because there is nothing to check it against.

---

## Sequence

| Step | Output | Blocked by |
|---|---|---|
| 1 | Issue bible restored to the season bible | — |
| 2 | 20-panel script, balloon-length dialogue | 1 |
| 3 | Page thumbnails, non-uniform layout spec | 2 |
| 4 | **Owner ruling on C-01 and C-02** | 2 |
| 5 | Festival plate calibrations (4 plates) | — |
| 6 | New camera-angle plates (target 12) | 3, 5 |
| 7 | Lil Devil alpha layer set | — |
| 8 | Expression and pose coverage gap-fill | 3 |
| 9 | Trapped-group extras (3 figures) | 3 |
| 10 | Panel-by-panel staging plans | 6, 7, 8, 9 |
| 11 | Composite, letter, effects | 10 |
| 12 | QA, approval, export | 11 |

Steps 5 and 7 are unblocked and independent — they are the right place to start
once the layouts are approved.

---

## Controlled-test gate before bulk generation

No bulk generation until a single-panel test proves the chain end to end. The
test panel is **page 5, panel 2** — NeonBlue and Moodz in the service corridor.
It exercises everything that matters: two characters at different depths, a
strong directional light source, a hard ground plane, a quiet performance beat
that needs readable expressions, and an existing plate.

It passes when:

1. Both characters are recognisably themselves against approved reference.
2. Feet meet the floor with correct perspective and a contact shadow.
3. Key light direction matches the corridor's practical lights.
4. Character edges carry no matte halo.
5. Relative scale is consistent with a named object in the plate.
6. It reads as the MonkeyZoo house style beside a Mango Pier panel.

If it fails, the failure is diagnosed and the method corrected before any other
panel is generated.

---

## What must not happen

- Bulk-generating 20 panels before the controlled test passes.
- Letting text-to-image invent a character because a pose is missing.
- Writing generated output into `characters/approved/` or any `imported_canon`
  path.
- Marking a panel approved because the character resembles the reference — the
  character must also *belong in the scene*.
- Repeating the legacy QA pattern of passing a panel because the file exists at
  the right dimensions.
- Re-attempting img2img edge unification. It was tested and rejected with
  measured evidence.

---

## Expected outcome

An 8-page, 20-panel issue that:

- follows the season bible's structure and restores its Echo logic,
- uses roughly twelve distinct camera setups instead of four repeated plates,
- varies panel size and shape according to narrative weight,
- stages characters into scenes with real ground contact, shadow and light,
- keeps every character identity traceable to owner-approved art,
- and passes a quality gate that a wallpaper pattern could not.

### Measured against the published editions

The owner designated the three published Fiend Studios editions as the style
target on 2026-07-28, which raises the bar above "a competent comic". The
rebuild must also deliver:

| Requirement | Where it is produced |
|---|---|
| Irregular panel grid, different on every page | Layout spec |
| Panels on a coloured page ground with per-page frame colour | Page assembly |
| Colour-coded balloons per speaker | Lettering |
| Large stylised SFX integrated into the scene | Effects |
| Cyan glow spilling onto faces, surfaces and floors | Compositing relight |
| At least one full-page splash at a genuine peak | Layout spec |
| At least one empty "breath" panel | Layout spec |
| Fiend Studios collectible stamp on the cover | Cover assembly |

None of these requires new generation capability. They require the layout,
lettering and assembly stages to exist as separate steps operating on frameless,
textless panel art — which is exactly how the pipeline is structured.

**Open question for the owner:** the published editions are One, Two and Three.
Issue 001 of the Emo Monkeys season needs an edition number for its stamp.

---

## Honest status

The rebuild is **planned and unblocked through layout**. Art production is
gated on two owner decisions (C-01, C-02) and on the controlled test. Nothing
in this recommendation has been executed as artwork — this run establishes the
foundation and the plan, and says so plainly rather than claiming progress that
does not exist.
