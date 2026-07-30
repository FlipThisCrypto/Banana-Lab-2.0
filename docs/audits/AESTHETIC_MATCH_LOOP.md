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

## Iterations 3-10

| # | change | measured effect |
|---|---|---|
| 3 | Contact and cast shadows made readable | contact ellipse 491x49 -> 516x99 at higher opacity; cast lean 479 px -> 191 px. Figures stopped floating. |
| 4 | `app/services/lettering.py` - balloons, captions, outlined SFX | `lettering_pct` 0.0 -> 3.29, **PASS** |
| 5 | Balloon geometry | tail was a hairline reading as a wire; then an enormous wedge scaling with speaker distance. Now a short stub clamped to 1.15 balloon heights. |
| 6 | Page boards into the published band | `ground_L` 71.5 -> 62.1, **PASS**. Hue and story arc preserved exactly. |
| 7 | Plate prompts: light as subject, three colours, few objects, funfair anchor, eye level | `share_in_large_shapes` **PASS**; `n_hue_families` went the WRONG way, 5.95 -> 6.92 |
| 8 | `plate_finish.posterise` - limited palette, linework preserved bit-exact | `n_hue_families` 6.92 -> 5.82 |
| 9 | `plate_finish.focal_vignette` - lightness **and** chroma | first version moved lightness only and `peak_over_field` FELL 40.4 -> 36.6; that property is chroma contrast, not brightness |
| 10 | Full integration run and measurement | **5/8**, guardrail held |

### Scorecard across the loop

| property | published | tolerance | iter 1 | iter 7 | iter 10 | |
|---|---:|---|---:|---:|---:|---|
| rule_L | 2.23 | ≤ 10 | 4.80 | 4.80 | 4.80 | PASS |
| rule_chroma | 1.26 | ≤ 6 | 2.41 | 2.41 | 2.41 | PASS |
| ground_L | 35.0 | 20–66 | 71.51 | 62.08 | 62.08 | PASS |
| lettering_pct | 5.16 | ≥ 2.0 | 0.10 | 3.12 | 3.29 | PASS |
| share_in_large_shapes | 0.56 | ≥ 0.26 | 0.19 | 0.35 | 0.30 | PASS |
| hairline_ink_density | 2.65 | 0.4–11.0 | 16.97 | 12.25 | 13.26 | FAIL |
| peak_over_field | 54.60 | 42.6–66.6 | 40.96 | 39.37 | 38.01 | FAIL |
| n_hue_families | 4.00 | ≤ 5.5 | 7.85 | 6.92 | 5.82 | FAIL |
| C_p95 guardrail | 66.05 | ≥ 50 | 54.54 | 57.99 | 51.95 | held |

**2/8 → 5/8.**

### The lesson of iterations 7 to 9

Three properties resisted four separate rounds of prompt adjectives - "large
flat areas of colour", "simple bold shapes", "only three colours", "very few
objects" - and each time the model partly complied and partly did not.
`n_hue_families` moved 6.4 → 5.9 → 6.9, i.e. nowhere. **Prompting is not a
control surface for pixel statistics.** Posterising fixed it in one pass.

That is not gaming the instrument, and the difference matters. A σ=2 px blur
would move three properties inside the published band while destroying the
linework, so `posterise()` detects ink and returns it **bit-exact**, and
`test_the_finishing_pass_does_not_blur` asserts edge contrast survives.

### Why hairline_ink_density cannot be fixed this way

It measures inches of thin ink stroke per square inch. The finishing pass
preserves linework by design, so it cannot lower this number, and the only
post-processes that would - blur, downscale - are the ones the scorecard's own
author identified as cheats. 16.97 → 13.26 came from generating simpler plates,
and closing the rest needs plates with genuinely fewer objects. That is a
generation problem, not a finishing one.

## Round two: iterations 11-30

### The process changed first

Each iteration had been costing ~10 minutes of GPU because every change
regenerated all 11 plates. Most remaining levers are FINISHING parameters that
touch no model, so `scripts/validation/aesthetic_loop.py` sweeps them over the
cached raw plates and appends every result to
`docs/audits/aesthetic-loop-ledger.json`. Iterations became comparable instead
of remembered.

The harness had its own flaw, found by being bitten: the ledger was flushed once
at the end, and the first long sweep was reaped mid-run and lost nine measured
configurations. It now writes after every config. An experiment ledger that can
lose experiments is not a ledger.

### Iterations 11-20: swept, one lever at a time

| config | scored | hairline | peak | n_hue | C_p95 |
|---|---:|---:|---:|---:|---:|
| it10-baseline | 5/8 | 13.56 | 35.87 | 5.74 | 52.52 |
| it11-palette6 | 6/8 | 12.21 | 35.35 | 4.75 | 52.29 |
| it12-palette4 | 6/8 | 13.02 | 34.21 | 3.78 | 51.50 |
| it13-chroma70 | 5/8 | 13.57 | 42.36 | 5.58 | 55.50 |
| it14-chroma100 | 6/8 | 13.57 | 49.14 | 5.58 | 58.59 |
| it15-vig60 | 5/8 | 14.24 | 40.91 | 5.58 | 53.70 |
| it16-palette6-chroma70 | 6/8 | 12.19 | 42.55 | 4.63 | 55.58 |
| it17-palette5-chroma85-vig55 | 7/8 | 12.81 | 43.49 | 4.62 | 56.08 |
| it18-ink28 | 6/8 | 13.20 | 42.15 | 3.93 | 56.26 |
| it19-ink40 | 6/8 | 13.12 | 42.07 | 4.59 | 55.20 |
| it20-centre-low | 7/8 | 12.44 | 44.39 | 4.51 | 57.98 |

**Mechanisms confirmed.** `chroma_gain` is the lever for `peak_over_field`
(0.40/0.70/0.85/1.00 → 35.9/42.4/43.5/49.1). `palette_size` is the lever for
`n_hue_families` (10/6/5/4 → 5.74/4.75/4.62/3.78).

**A hypothesis rejected and kept.** `ink_l` does *not* drive
`hairline_ink_density`: 28/34/40 gives 13.20/12.19/13.12, no trend. Recorded as
a negative result rather than quietly dropped. Vignette strength 0.60 made
hairline *worse*, 14.24.

### Iterations 21-22: simpler plates

The location anchors were a shopping list — stalls, awnings, bulbs, bunting,
rides, a ferris wheel, grass, a crowd: eight object classes, all of which the
model dutifully drew across the whole frame. Cut to three. And the script's own
`background_description` — owner material, preserved verbatim — now carries a
rendering instruction to mass crowds and rows as silhouette shapes rather than
individual objects, which directs execution without changing content.

Result: 7/8 with real plates. hairline barely moved, 12.44 → 12.36.

### Iterations 23-27: the ink-thickening trap

`hairline_ink_density` counts strokes narrower than 1.5 pt. Since `HOUSE_STYLE.md`
and the style contract both call for *"thick uniform black outlines"* and SDXL
was not delivering them, thickening the ink looked like the stylistically correct
fix. It worked, numerically: radius 0/1/2/3/4 gives hairline
40.6/13.5/4.2/2.3/1.4 against a published 2.65.

**And it was wrong.** Two measurements caught it, and then looking confirmed it:

- `share_in_large_shapes` moved 0.012 → 0.801 at the same time, because the
  linework merges into blobs.
- page lightness fell to mean L\* 15.7–17.8 against a **published 37.0**.
- at radius 3, the railings in P02-03 have merged into solid black.

The scorecard read 7/8 while the art moved *away* from the reference. That is
exactly the failure its author predicted. `thicken_ink()` stays in the module,
out of the pipeline, with the evidence in its docstring.

### Iterations 28-30: the bug the trap exposed

Chasing the lightness collapse found a real bug in `focal_vignette`. The `cos`
field is negative over most of the frame's **area** — area grows with radius — so
the field averaged well below zero and the "vignette" was a **global darken**. It
was making every plate roughly 11 L\* darker than the art it started from, and
the high chroma gains chosen in iterations 13–17 were compensating for a defect
rather than improving anything.

Centring the field to zero mean fixed it, and once fixed a much *gentler*
configuration cleared the same tolerances with lightness preserved:

| | mean L\* | hairline | share | peak | n_hue | C_p95 |
|---|---:|---:|---:|---:|---:|---:|
| raw plate | 27.5 | 7.83 | 0.537 | 39.8 | 6.00 | 65.9 |
| before the fix (pal6 vig.55 gain.85 dilate2) | **15.8** | 1.95 | 0.698 | 53.8 | 4.00 | 72.3 |
| after (pal6 vig.35 gain.60, no dilation) | **29.1** | 6.06 | 0.562 | 47.5 | 5.00 | 70.4 |

Settled defaults: palette 6, chroma gain 0.60, vignette 0.35 centred at 0.58
height, no ink dilation.

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
