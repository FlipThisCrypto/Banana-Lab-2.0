# Aesthetic Match Loop — Issue 001 against TheFusionSquad

**Target:** a reader should immediately believe Issue 001 came from the same
studio and pipeline as `TheFusionSquad.pdf`. Not similar colours — same craft.

**Owner constraints:** preserve script, dialogue, continuity, theme. Do not
redesign characters. Do **not** optimise for panel count or page layout.

**Instrument:** `scripts/validation/aesthetic_scorecard.py` — 8 properties, each
admitted only after it was shown to separate published pages from this
pipeline's output, plus a `C_p95` guardrail that must not be optimised against.
Measured medians come from all 20 published pages of both editions.

---

## What the published editions actually do

Read directly, not inferred:

| device | evidence |
|---|---|
| The background POINTS AT the character | Page 7: one green field, brightest directly behind the figure, radial streaks converging on it. Built to make the figure read. |
| Character occupies 25–70% of panel | Page 5's medium panels put a figure at 35–60% of panel height |
| 3–4 hue families per panel | measured `n_hue_families` median 4.0 |
| Large flat colour cells | measured `share_in_large_shapes` median 0.558 |
| Hard-edged cel fills inside black linework | no airbrush anywhere |
| Panels float inset on a coloured board | measured inset 3.27% / 4.35%, thin near-black rule |
| Visible ground contact | figures stand on a ground line with a contact shadow |
| Dramatic single-source lighting | deep corner shadow, bright centre |

**Correction to an earlier claim of mine.** I described the references as "muted
and desaturated". They are not. Published `C_p95` is 66.1 against this
pipeline's 60.1 — the output was already *below* published peak chroma. The gap
was never saturation. It was **busy-ness and the absence of a focal point.**

---

## Iteration 1 — page furniture

Two defects, both bugs in this pipeline, found by measuring rather than looking.

- `assemble_page()` had the board and the rule **inverted**: the page was painted
  white and `frame_color` — the board colour — was used as a 10 px panel rule.
  Measured rule L\* 71.9 / chroma 57.5 against published 2.2 / 1.3.
  `page_ground.panel_border_color` was declared in the spec and sat unused.
- A **solo** character was pushed to the deepest rung: `rung = order[0] /
  max(1, slots-1)` evaluates to 0.0 when `slots == 1`, applying a 2.63× height
  penalty and selecting `depth_plane="background"` — blur 1.1 plus haze 0.18.

Result: **0/8 → 2/8**, guardrail held. `rule_L` 71.5 → 4.8, `rule_chroma`
53.6 → 2.4. The busy-ness properties barely moved and `n_hue_families` got
*worse*, 6.45 → 7.85.

**Finding: prompt-only simplification does not work.** Asking SDXL for "large
flat areas of colour, simple bold shapes, minimal fine detail" did not overcome
the location anchor's own content — rows of stalls, bunting, a festival crowd.

---

## Iteration 2 — composition, proportion, and executing the script's direction

**1. Focal backgrounds instead of wallpaper.** `FOCAL_BACKGROUND` asks for a
vignette brightest at centre, large simple flat shapes, a limited palette, a
clear ground plane in the lower third, one dominant light, and empty middle
space for a figure. `FOCAL_NEGATIVE` rejects aerial, isometric and top-down
views, detailed crowds, wimmelbild and repeated small objects.

**2. Character proportion 25–70% of panel height.** `CHARACTER_SHARE` per shot,
with the scale multiplier solved so the rendered figure hits it. The ground
plane still decides *where* feet land and how depth ranks the cast; this decides
*how big*. Previously figures were 2–7% of the page.

**3. The pipeline now executes `character_blocking`.** The script had already
directed every shot — `position`, `depth_plane`, `scale_note`, `ground_contact`,
`eye_line`, `hand_activity` — and nothing was reading it. Depth order now comes
from the script's own words ("Front of the cluster", "Half a step behind",
"Rearmost, trailing"), x position from its stated side, relative scale from
"20 percent smaller", and a figure the script crops at the waist is no longer
given a contact shadow on a ground line it never touches.

**4. Pose selection from the script, not `clean_base`.** `pick_layer` previously
scored pose names against panel prose and gave `clean_base` a bonus, so six
identical standing postures appeared in a row on P01-02. It now matches the
per-character direction. Measured on P01-02:

```
MZ-CHAR-005 neonblue -> neonblue_19_determined  "both feet mid-stride, weight forward"
MZ-CHAR-001 moodz    -> moodz_10_walking        "both feet walking, hands in pockets"
MZ-CHAR-003 static   -> static_16_worried       "hesitating half a step, hand near his ear"
MZ-CHAR-002 twotone  -> twotone_10_walking      "both feet walking, scanning the layout"
MZ-CHAR-004 ash      -> ash_18_sleepy           "slowest pace, down at the ground"
```

### Overshoot, and the correction

The first focal-background attempt produced the right *kind* of image — simple,
dark, vignetted, clear ground plane, generous space for a figure — and lost the
house style completely: a soft airbrushed field with no linework at all.
"Atmospheric depth" and "soft bokeh" beat the cel-shading style contract.

The published art is simple **and** hard-edged. `FOCAL_BACKGROUND` now demands
"hard edged flat colour, no gradients, no airbrush", and `FOCAL_NEGATIVE`
rejects airbrush, painterly, watercolour, soft focus, photographic bokeh and
"no linework".

---

## Not yet addressed

- **Lettering.** `lettering_pct` measures 0.1 against a published 5.16. Balloons,
  captions and sound-effect display type are a later pipeline stage and are the
  single largest remaining scorecard gap.
- **Ground contact.** Contact and cast shadows are computed but are not visibly
  reading on the page. Needs investigation, not assumption.
- **Foreground depth.** `Placement.occluder` exists and is unused, so panels have
  midground and background but no true foreground element.
- **The cover** has no cast and no title treatment. Lil Devil has zero approved
  layers, and the stamp, logo and title are lettering-stage work.

## On "98% aesthetic likeness"

Not measurable, and it is not reported. The eight properties have no common
units, so any percentage would be a choice of weights presented as a
measurement. The precision implied sits below the instrument's noise —
`hairline_ink_density` moves up to +162% from render DPI alone. And a σ=2 px
blur, invisible at reading distance, moves a page inside the published band on
three properties at once while fixing nothing.

The defensible target: **8 of 8 scorecard properties inside published range with
the `C_p95` guardrail held.** The likeness gate remains the hard constraint — no
aesthetic change may buy a lower likeness score.
