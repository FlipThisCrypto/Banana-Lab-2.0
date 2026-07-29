# Likeness Tuning Report

**Goal:** make "consistent character likeness" a measured number, then drive it
to a consistent pass across the whole approved layer library.

**Run date:** 2026-07-28 to 2026-07-29. Baseline: both the repo copies and the
factory originals matched the migration manifest hash-for-hash at the start of
this work, so every number below is against a verified, reproducible input
state.

**How to read this report.** It is written as a record of what was measured, in
the order it was measured, including the parts that were wrong. The metric was
found to be broken **seven** times. Five of those were caught by negative
controls rather than by inspection, and four were caught only *after* the
library had scored 100%.

Two habits produced everything useful here, and they are the only part of this
document worth generalising:

1. **Never accept a pass rate without the matching rejection rate** on
   deliberately broken input, measured on the same run.
2. **An unmeasured thing is not a passing thing.** Three separate faults were
   silent holes — a colour the palette never tracked, a gate that disagreed with
   its own rule, a contamination status nobody had determined — and each one
   read as success until it was asked directly.

---

## Why a metric first

Likeness in this pipeline is not generated — it is composited from approved art.
In principle that makes it perfect by construction. In practice three things
erode it between the approved layer and the finished panel, and each needs a
different fix:

| Erosion | Cause |
|---|---|
| Contamination | Card-background bleed surviving inside the silhouette |
| Palette drift | Relight moving canon colours |
| Illegibility | A feature surviving the maths but too small to read at print size |

Without a number, "looks like him" is an argument. With one, it is a gate.

---

## The metric

`app/services/likeness.py`. Score 0–100, composed of three independently
gated components:

| Component | Weight | Gate | What it measures |
|---|---:|---:|---|
| Palette fidelity | 55% | ≥ 92 | Chroma-plane dE against the canon palette, under three rules (below) |
| Contamination | 25% | ≥ 99 | Card-bleed pixels inside the silhouette |
| Feature legibility | 20% | ≥ 85 | Rendered height against the size below which small features stop reading |

**A pass requires the overall score ≥ 95 AND every component gate.** A high
average must never hide a failed component — the same rule as the panel approval
standard, where a 99 with an extra hand still fails.

Palette fidelity is not one number but **three rules, all of which must hold**.
Each exists because a real identity failure got past the others:

| Rule | Limit | Catches | Was found missing by |
|---|---:|---|---|
| `SWATCH_TOLERANCE` — worst single canon swatch | 12.0 | A recoloured feature: NeonBlue's crown is under 4% of him, so destroying it barely moves any average | Fault 2 |
| `MEAN_DRIFT_TOLERANCE` — area-weighted mean across swatches | 3.0 | A free tint: every swatch moves a little, none past 12 | Fix 5 |
| `PIXEL_DRIFT_TOLERANCE` — mean over **every opaque pixel** | 2.5 | Damage to a colour the palette never tracked at all | Fix 6 |

`palette_score ≥ 92` is derived to be *exactly equivalent* to all three limits
holding, so the gate and the rules cannot drift apart — which they did once,
silently, and cost a full debugging cycle.

Distance is measured in the **a\*b\* plane only**. Lightness is what a light is
supposed to change; penalising it makes a correctly-lit character look like a
likeness failure.

The canon palette is **measured from the approved art**, not read from a bible.
Declared hex values drift from the artwork; the artwork does not. Cel art is
flat fills, so quantising and counting recovers the real palette directly.

### Sanity check

Measuring a layer against itself, with no relight:

| Layer | Score | Palette dE |
|---|---:|---:|
| `neonblue_16_worried` | 99.9 | 0.03 |
| `moodz_00_clean_base` | 99.9 | 0.04 |

The metric returns ~100 for an identical image, which is the minimum it must do
to be trusted.

---

## Finding 1 — the relight was tinting identity colours

The exp005 relight (`key 0.22 / fill 0.10 / spill 0.14`) scored:

| Character | Score | Palette dE | Result |
|---|---:|---:|---|
| NeonBlue | 90.7 | 6.1 | **FAIL** |
| Moodz | 93.2 | 4.4 | **FAIL** |
| Static | 92.5 | 4.9 | **FAIL** |
| Scarline | 93.9 | 4.0 | **FAIL** |
| Ash | 88.5 | 7.5 | **FAIL** |
| TwoTone | 92.2 | 5.1 | **FAIL** |

All six failed. The drift was concentrated on the **whites and pale greys**:

```
NeonBlue  #F0F0F0 -> #C6E3E9   dE 12.2
Moodz     #FCFCFC -> #C8ECF3   dE 14.8
```

Those swatches carry face fills, eye whites, under-eye bags, eye rings and
stitched chest panels — identity-bearing features on both characters. The cyan
scene light was turning them teal.

This confirmed, with numbers, what the adversarial QA pass had reported by
inspection.

---

## Fix attempt 1 — shield near-neutral pixels

Reduce the tint on bright, low-chroma pixels, on the reasoning that in cel art
the whites are graphic elements rather than physical surfaces.

| Character | Before | After |
|---|---:|---:|
| NeonBlue | 90.7 | **97.7** |
| Moodz | 93.2 | **98.2** |
| Static | 92.5 | **98.3** |
| Scarline | 93.9 | **97.4** |
| Ash | 88.5 | **97.3** |
| TwoTone | 92.2 | **97.8** |

Mean palette dE fell from ~5.3 to ~1.4. All six passed.

**But six characters is not the library.** Sweeping all 139 layers across three
scene lights (cool corridor, warm festival, red emergency) told a different
story:

```
measurements : 417  (139 layers x 3 scenes)
PASS         : 235 / 417  (56.4%)
layers clean across all scenes : 63 / 139
```

Two failure causes:

| Failures | Cause |
|---:|---|
| 114 | card-bleed contamination |
| 68 | palette drift |

The six characters I had tuned on were simply the ones whose layers happened to
be clean.

---

## Fix 2 — repair the card bleed

The bleed is background that background-removal missed: an enclosed region — the
gap between an arm and a torso, inside a curled tail — where the card colour
survives at full opacity inside the silhouette.

### Identifying it without guessing

Two earlier approaches failed, both confirmed wrong by eye:

| Approach | Failure |
|---|---|
| Colour families ("orange-ish pixels are suspect") | Flagged a pink tongue |
| Outline heuristic ("holes lack an enclosing black outline") | Cleared a real hole that happened to be bordered by the character's own outline, AND flagged a tongue inside a black mouth |

The working method is definitional. **The card colours are whatever the layer's
own opaque source sheet shows where the layer is transparent** — background
removal made those pixels transparent, so what is under them is by definition
background. Any colour holding a meaningful share of that region, and saturated
enough not to be cel-art black/white/grey, is a card colour for that sheet.

A tongue is not the card colour. A hole is, exactly.

Validated against three cases inspected by eye:

| Layer | Truth | Detected |
|---|---|---|
| `moodz_00_clean_base` | matte hole (orange wedge) | 1 blob, 1616 px |
| `neonblue_23_waving` | matte hole (green wedge) | 1 blob, 7307 px |
| `clever_08_shocked` | art (pink tongue) | correctly not flagged |

### Guards

A saturation floor on the card colour is essential. Without it, a sheet whose
border happens to be black causes every outline pixel in the layer to be
flagged — **measured at 106,753 false positives on `clever_08_shocked`**.

Layers whose source is missing, or a different size and so unalignable, are
reported UNDETERMINED and left for human review rather than guessed at.

### Repair

```
scanned 139 layers
  CLEAN        30
  REPAIRED     60   (118,883 px made transparent)
  UNDETERMINED 49
```

Repaired layers are written to `characters/working/repaired_layers/`. **The
imported originals are never modified** — a revision is a new file (ADR-002).

An edge sweep removes the anti-aliased blend pixels ringing each hole; without
it a coloured hairline survived along the repaired edge.

Verified visually: the orange, green and magenta wedges are gone and the
surrounding art is untouched.

### Result

```
PASS : 343 / 417  (82.3%)     up from 235 / 417
layers clean across all scenes : 97 / 139   up from 63
contamination failures : 0    down from 114
```

Contamination eliminated entirely.

---

## Fix 3 — light changes value, not hue

The remaining 74 failures were all **saturated** canon colours:

```
zombie   #A8C09C  dE 14    pale green skin
clever   #B44236  dE 20    red shirt
clever   #C0C09C  dE 15    pale olive
```

The neutral shield did nothing for these — it only protected low-chroma pixels.
But Scarline's scarlet streak and Zombie's pale green are required identifying
features every bit as much as NeonBlue's under-eye bags.

The principle the first fix half-discovered, stated properly:

> **In cel art, light changes value. It must barely change hue.** The flat fills
> are graphic identity, not physical surfaces.

So `relight()` now computes the fully-tinted result, keeps only its **luminance**,
restores the **original hue**, and blends back a controlled amount of tint. The
character still takes the scene's light and still belongs in the scene — it just
stops changing colour.

`protect_neutrals` now controls that blend: 0.0 is a free tint (the old
behaviour), 1.0 is pure luminance with hue exactly preserved.

Visual check confirms the metric is tracking something real, not a metric
artifact: at free tint both faces read teal; hue-safe, NeonBlue's face holds its
white and Moodz's fur holds its brown, while both still sit in the corridor's
cyan light.

---

## The metric was wrong, three ways at once. Negative controls caught it.

After the fixes above, the library scored **417 / 417 (100%)**.

That number was worthless, and finding out why was the most valuable work in
this run.

### Why 100% was not believable

A metric that passes everything is indistinguishable from no metric. So before
reporting the result, the metric was run against deliberately broken inputs that
it *must* reject.

**Three of six negative controls passed:**

| Control | Expected | Got |
|---|---|---|
| Hue-swapped character (R↔G) | FAIL | **PASS**, 99.1 |
| Fully desaturated | FAIL | **PASS**, 98.2 |
| Free tint, no hue protection | FAIL | **PASS**, 99.5 |
| Crushed to 25% lightness | FAIL | FAIL |
| Clean art + 6000 px card bleed | FAIL | FAIL |
| Rendered at 1/5 size | FAIL | FAIL |

The free-tint case is the damning one: that is the exact failure mode this
module exists to catch, and the metric waved it through at 99.5.

### Fault 1 — nearest-neighbour matching

The palette check found, for each canon swatch, the *nearest rendered colour*.
Across tens of thousands of pixels something always lands near any given
swatch. A character could be almost entirely the wrong colour and still score
perfectly.

**Fix:** where the render is pixel-aligned with the approved layer — which it is
for every composite this pipeline produces, since the render *is* the
transformed layer — compare the pixels that **were** each canon swatch with what
they **became**. That correspondence is exact and cannot be satisfied by a
coincidence elsewhere in the image.

Free tint and crushed-lightness then failed correctly. Hue-swap and desaturate
still passed.

### Fault 2 — area weighting buried the identity colours

NeonBlue is mostly neutral: white fur, black clothing. Swapping R and G does
nothing to a grey pixel, so an area-weighted mean barely moved.

But the parts that *do* carry hue are exactly the required identifying
features — his cyan crown, Moodz's blue accent, Scarline's scarlet streak. They
are small-area and high-importance, and area weighting is precisely the wrong
weighting for them.

**Fix:** the palette score is now driven by the **worst** swatch as much as the
mean, and any single swatch over tolerance caps the component at 80, which fails
the gate outright.

### Fault 3 — the identity colours were not in the palette at all

Even after that, recolouring **14,923 px of NeonBlue's cyan crown to orange**
still scored 100.

Diagnosis:

```
cyan-crown pixels : 14,108 = 3.98% of the character
spread across     : 1,087 quantised RGB bins
largest single bin: 0.121% of the character
```

The palette was built by binning RGB at `//6`. Any colour with a gradient or
anti-aliasing fragments across dozens of bins, none of which clears the 1.2%
share threshold — so the crown was never a tracked swatch, and changing it was
literally not measured.

Worse: **8 of the 10 tracked swatches had zero chroma.** The metric was barely
measuring colour at all.

**Fix:** cluster in Lab rather than binning RGB. Gradients merge into one
perceptual cluster; distinct hues stay apart. The crown now appears as a tracked
swatch at 1.40% share with chroma 180.

### Controls after all three fixes

| Control | Expected | Score | Result |
|---|---|---:|---|
| Hue-swapped (R↔G) | FAIL | 45.0 | FAIL |
| Fully desaturated | FAIL | 67.1 | FAIL |
| Free tint, no hue protection | FAIL | 87.9 | FAIL |
| Crushed to 25% lightness | FAIL | 73.1 | FAIL |
| Clean + 6000 px card bleed | FAIL | 80.6 | FAIL |
| **Cyan crown recoloured orange** | FAIL | 45.0 | FAIL |
| Unmodified layer | PASS | 100.0 | PASS |
| Correct hue-safe relight | PASS | 97.1 | PASS |

**0 incorrect verdicts.**

### The lesson

Every number in this report before this section was produced by a metric that
could not tell a correct character from a hue-swapped one. The fixes to the
*pipeline* were real and remain valid — the card bleed was genuine, the relight
drift was genuine, both were confirmed by eye. But the *scores* attached to them
were not measuring what they claimed.

A metric is not trustworthy because it is precise, or because it agrees with
your expectations. It is trustworthy when it rejects things it should reject.
Negative controls are not optional, and they belong in the regression suite —
which is where they now live.

---

## Fix 4 — "preserve hue" was being done in the wrong colour space

With a trustworthy metric, the honest sweep came back at **47.0% (196/417)**.
Every one of the 221 failures was the same thing: saturated **red**, drifting
dE 14–15 under the cool-corridor cyan key.

```
86.8  clever/clever_00_clean_base.png   cool-corridor   #B94235 (15)
86.9  clever/clever_06_angry.png        cool-corridor   #B84133 (15)
86.9  clever/clever_18_sleepy.png       cool-corridor   #B64134 (14)
```

Rather than guess, I measured a flat `#B94235` patch across protection levels:

| `protect_neutrals` | cool | warm | red |
|---|---:|---:|---:|
| 0.85 | 11.3 | 6.8 | 9.7 |
| 0.90 | 10.9 | 7.1 | 10.2 |
| 1.00 | **10.2** | 7.8 | 11.2 |

That table is the whole finding. At `protect = 1.00` the documented contract is
*hue exactly preserved* — the drift should be ~0. It was 10.2. **More protection
barely helped, because protection was not the lever.**

Fix 3 kept "only the luminance" by scaling the RGB triplet uniformly. That
preserves the *RGB ratios*, which is not the same as preserving hue. Scaling
`(180,60,48)` by ×1.52 moves its Lab chroma from `(47.9, 34.0)` to
`(64.4, 46.4)` — a 34% chroma inflation invented purely by the arithmetic.

`relight()` now recombines in Lab directly: take **L\*** from the lit result,
take **a\*/b\*** from the original, convert back. Hue and chroma are preserved
by construction rather than by approximation. Same patch, same lights:

| `protect_neutrals` | cool | warm | red |
|---|---:|---:|---:|
| 0.85 | **2.6** | 0.3 | 0.1 |
| 1.00 | **0.2** | 0.2 | 0.3 |

### The same error was hiding in the test

`test_hue_safe_relight_holds_canon_colours` began failing. It was right to fail
and wrong about why: its `_hue_shift` helper *also* normalised luminance by
scaling RGB. It reported dE 21.6 for a relight whose true chroma drift was 2.3
— it was measuring its own normalisation. The helper now uses `delta_e_chroma`,
the same L\*-independent instrument the metric uses.

Two pieces of code, written at different times, made the identical mistake. The
test could never have caught the bug because it shared the bug.

### And a third instance, caught by a new test

I added `test_lab_recombination_holds_chroma_by_construction` on the principle
that a newly load-bearing function needs its own guard. It failed immediately —
and the failure was real, not a fixture problem.

**Darkening a saturated colour in Lab routinely leaves the sRGB gamut.** Cyan
`(52,229,232)` taken to 60% L\* wants a negative red channel. Clipping the
channel to zero swings a\* from −40.9 to −28.9: a hue shift, reintroduced at the
very last step, on exactly the colour that identifies NeonBlue.

`lab_to_srgb_in_gamut()` now scales a\*/b\* toward the neutral axis until the
colour fits, holding the hue angle exactly and surrendering only chroma the
display genuinely cannot show.

Two further traps, both caught by the same test:

- The search accepted results within ±0.5 of the cube and then clipped. That
  tolerance *was* the hue error — accepting R = −0.4 and clipping to 0 shifts
  the hue by exactly as much as clipping would have. Now strict.
- `lab_to_srgb` clipped negative linear values internally, so every colour
  looked in-gamut and the mapping was a silent no-op. It now uses signed gamma
  and returns a true, unclamped inverse.

Measured result: hue error **0.00°** on all three test colours after mapping;
the cyan keeps 71.8% of its chroma, which is the honest physical limit.

### Cost

The search was 13.7 s/megapixel, or ~57 minutes for one sweep — too slow to
iterate against. Two changes, no loss of precision:

- Search only pixels that are actually out of gamut (fast path returns
  immediately when none are).
- Solve each *distinct* offending Lab value once. One layer had 3,397 distinct
  offending values across 704,258 offending pixels. The quantisation decides
  only which scale factor to use; the factor is applied to full-precision Lab.

Relight on a real 1.04 MP layer: **8.23 s → 2.48 s**.

A third change found the rest: cut-out layers carry arbitrary colour *under*
alpha = 0, left behind by the matte. It never renders, but the colour maths
still paid for it — and that junk colour is wildly out of gamut once darkened.
Measured across the library: **63% of pixels are fully transparent, 67.6% go out
of gamut, but only 4.1% are both visible and out of gamut.** Neutralising the
invisible ones took relight to **1.66 s**, a 5× total speedup.

That it is free is *proved*, not assumed: colouring the transparent region a
garish green and relighting gave a **bit-identical** result on visible pixels
across 8 layers (max difference 0). Held by
`test_colour_under_full_transparency_cannot_reach_the_output`.

Sweep result: **47.0% → 82.0%**, minimum score 86.8 → 91.6.

---

## Fix 5 — the gate and the rule had drifted apart

The remaining 75 failures had a strange property: **every swatch was inside
tolerance, and the layer failed anyway.**

```
clever / red-emergency    worst dE 9.2   mean dE 1.4   every swatch ok   FAIL
```

The per-swatch rule said dE ≤ 12 is preserved. The score formula divided a
blend of mean and worst by `SWATCH_TOLERANCE` and multiplied by 1/3, and the
gate was `palette_score ≥ 92` — which worked out to requiring a blended dE of
≤ 2.88. Two different tolerances for the same question, and the reported reason
("palette drift") named a swatch that did not exist. I went looking for that
swatch before realising the message was false.

So I measured what actually separates a legitimate relight from a broken one:

| | worst dE | mean dE (area-weighted) |
|---|---:|---:|
| Legitimate relights (3 chars × 3 scenes) | 1.6 – 9.2 | **0.7 – 1.5** |
| Free tint, cool key | 10.3 | **5.9** |
| Free tint, red key | 17.6 | **9.7** |
| Fully desaturated | **40.3** | 2.7 |
| Crown recoloured orange | **86.9** | 2.4 |

Neither column does the job alone:

- **worst** catches desaturation and recolouring, which barely move the mean —
  NeonBlue's crown is under 4% of him.
- **mean** catches a free tint, which moves everything a little and nothing past
  12.

So the palette component now has two explicit rules, `SWATCH_TOLERANCE = 12.0`
and `MEAN_DRIFT_TOLERANCE = 3.0` (2× the worst legitimate mean, half the mildest
free tint), and the score is derived so that `palette_score ≥ 92` is *exactly*
equivalent to both rules being satisfied. The gate can no longer disagree with
the rule — `test_palette_gate_and_the_de_tolerances_cannot_disagree` sweeps a
range of tints and asserts the equivalence at every point.

The failure note now says which rule bit, in dE.

---

## "100%" — checked, this time, before believing it

The sweep then returned **417/417**. That is the same number that was worthless
last time, so it does not get believed on its own.

The controls that caught the earlier faults had only ever been run on **one
layer in one scene**. So `scripts/validation/control_sweep.py` now runs four
controls (free tint, desaturation, hue swap, accent recolour) against **every
layer in every scene**.

The first run failed immediately — Ash passed while fully desaturated. But the
cause was not the metric: **Ash is a near-greyscale character.** Mean chroma
2.3; his palette is `#D3D3D3`, `#020202`, `#F2F2F2`, `#8C8C8C`. Desaturating an
already-grey character genuinely does not change him, and the metric is right to
say so. Counting that as an escape would have been measuring the control.

So each control is now checked for whether it actually *did* anything, using a
mean chroma-plane distance computed **directly on pixels** — deliberately not
using the metric under test, or the check would be circular. Controls that move
the art by less than dE 3.0 are reported as inapplicable rather than scored.

### The full run failed: 18 escapes out of 1,089

Run across all 139 layers, the metric **accepted 18 deliberately damaged
inputs**. The 417/417 was not real.

```
 96.0  applied dE 6.0  hue-swapped        neonblue/neonblue_21_running.png
100.0  applied dE 3.4  accent-recoloured  neonblue/neonblue_21_running.png
100.0  applied dE 3.1  accent-recoloured  neonblue/neonblue_26_reaching.png
 96.6  applied dE 3.4  desaturated        neonblue/neonblue_28_celebrating.png
 96.6  applied dE 3.1  hue-swapped        twotone/twotone_28_celebrating.png
```

A score of **exactly 100.0** on a materially recoloured image is not a near
miss — it means the metric saw *nothing at all*. Checking why:

```
neonblue_21_running:  11201 high-chroma pixels, 3.60% of the figure
palette: #DDDDDD(33%) #020202(31%) #524639(11%) #F4F4F4(8%) #8C8C8D(4%) ...
high-chroma pixels with NO tracked swatch within dE 14:  11201  (100%)
```

His palette comes back **entirely neutral**. The cyan crown is not in it. For
comparison, `neonblue_16_worried` *does* track it — `#34E5E8(1.4%)`,
`#55DDE0(1.2%)` — and only 18% of its high-chroma pixels are untracked.

This is fault 3 again in a new guise. In some poses the crown fragments across
enough Lab clusters that every one of them falls below the 1.2% share
threshold, so the identity colour vanishes from the palette and damage to it is
invisible.

### Fix 6 — a rule that cannot have a coverage hole

Rather than chase the share threshold again, the palette now has a safety net
under it: **mean chroma dE over every opaque pixel**, tracked or not. The
aligned path already has exact pixel correspondence, so this costs nothing.

| | pixel drift dE |
|---|---:|
| Legitimate relights (8 chars × 3 scenes, n=66) | max **1.64** (mean 1.13, p95 1.54) |
| Damaging controls (n=165) | min **3.02** (median 6.37) |

`PIXEL_DRIFT_TOLERANCE = 2.5` sits between, with 52% headroom over the worst
legitimate case. All 18 escapes are now rejected:

```
neonblue_21_running   hue-swapped        applied 6.0  ->  89.7  rejected
neonblue_21_running   accent-recoloured  applied 3.4  ->  94.2  rejected
neonblue_26_reaching  accent-recoloured  applied 3.1  ->  94.9  rejected
twotone_28_celebrating hue-swapped       applied 3.1  ->  94.3  rejected
```

The palette rules are what make a failure *explainable* ("your cyan moved");
this rule is what makes rejection *certain*. Both are kept.

Note the margins: `neonblue_26_reaching` is rejected at 94.9 against a gate of
95.0. That is a 0.1 margin on a perturbation of dE 3.1. **Damage below roughly
3 dE is not reliably caught** — stated as a limit, not papered over.

Reproducing this in a test took three attempts, and the failures were
instructive. Scattering one flat colour spatially does *not* reproduce the hole
(it stays a single Lab cluster and gets tracked normally); and an accent dull
enough to escape tracking is usually too dull to move the mean. The real art
escapes both because it fragments far more finely than a naive fixture does.

### Full control sweep, after Fix 6

```
layers                 : 139
applicable measures    : 1089  (of 1668 attempted)
skipped, no real damage: 579   (control moved the art by < dE 3.0)
controls REJECTED      : 1089 / 1089
controls ESCAPED       : 0
broken-input scores    : max 94.9  median 82.1  (gate is 95.0)
```

The worst broken input now scores 94.9 against a gate of 95.0. That is a
**0.1 margin** on the hardest case, not a comfortable one, and it is the honest
edge of what this gate resolves.

### The separation is real

| | score |
|---|---:|
| Worst legitimate measurement | **96.4** |
| Best deliberately-broken measurement | **91.4** |
| Gate | 95.0 |

A 5-point gap, with no legitimate measurement within 1.0 of the gate (0 of 417).
That is a genuine separation, not a threshold tuned until the answer came out
right.

### Per-character

| character | measurements | min | median |
|---|---:|---:|---:|
| clever | 90 | 96.4 | 97.8 |
| ash | 54 | 97.3 | 98.2 |
| neonblue | 51 | 97.4 | 98.3 |
| zombie | **3** | 97.7 | 98.5 |
| scarline | 51 | 97.8 | 98.3 |
| twotone | 57 | 97.8 | 98.5 |
| moodz | 54 | 98.0 | 98.5 |
| static | 57 | 98.1 | 98.6 |

Zombie has **3** measurements — one layer. That is a coverage gap, not a result.

---

## Current position

| Stage | Pass rate | Layers clean across all 3 scenes |
|---|---:|---:|
| Original relight, original layers | 56.4% | 63 / 139 |
| After bleed repair | 82.3% | 97 / 139 |
| *(with the untrustworthy metric)* | *100%* | *139 / 139 — **invalid**, see above* |
| *(with a broken sweep harness)* | *1.9%* | *0 / 139 — **harness bug**, not art* |
| Honest metric, RGB-ratio relight | 47.0% | 53 / 139 |
| **+ Lab recombination (Fix 4)** | **82.0%** | **95 / 139** |
| **+ consistent dE gate (Fix 5)** | **100.0%** — *18 controls escaped* | 139 / 139 |
| **+ pixel-drift rule (Fix 6)** | **100.0%** | **139 / 139** |
| **+ unknown contamination fails (Fix 7)** | **64.7%** | **90 / 139** |

The two 100% rows differ only in whether broken input could sneak through. The
first let 18 damaged images pass; the second lets none through that the control
suite can construct. The library number did not move at all between them
(min 96.4 both times) — **the fix cost legitimate art nothing and closed the
hole**, which is the shape a real fix has.

Three rows in this table read 100%. The first was worthless (broken metric), the
second was worthless (18 escapes), the third is the first one I am willing to
put weight on — and only because 1,089 applicable attempts to break it, across
every layer and every scene, now all fail.

That is the lesson of this run, three times over: **a pass rate means nothing
without a matched rejection rate on deliberately broken input.** Every single
time the pass rate went up on its own, it was wrong.

---

## Fix 7 — "not known to be dirty" was reading as "known to be clean"

The 100% deserved one more question: *what does the metric do with a layer whose
contamination it could not measure?*

The bleed detector reports UNDETERMINED for layers it cannot align against their
source sheet. That verdict reached the metric as `contamination_px = 0` —
indistinguishable from a **measured** zero. Reconciling the detector and repair
passes:

| detector | repair | layers | what is actually known |
|---|---|---:|---|
| BLEED | REPAIRED | 40 | bleed found and repaired — known |
| UNDETERMINED | REPAIRED | 19 | repaired — known |
| UNDETERMINED | CLEAN | 16 | repair pass aligned it — known |
| CLEAN | CLEAN | 14 | known clean |
| CLEAN | REPAIRED | 1 | known |
| **UNDETERMINED** | **UNDETERMINED** | **49** | **unknown — scored as clean anyway** |

**49 of 139 layers (35%) were passing on an assumption nobody had checked**, and
they are concentrated: 30 Clever, 17 Scarline, 1 Ash, 1 Static.

This is the same class of error as every other fault in this report — a number
that looks complete because the hole in it is silent. It also runs straight into
ADR-005: a machine gate may only reject, never approve. Treating "unmeasured" as
"passed" is the gate approving something.

`contamination_px` now accepts `None` for *unknown*, distinct from `0` for
*measured clean*, and an unmeasured component cannot contribute a pass — the
same rule the module already applied to unaligned renders. The layer is reported
UNMEASURABLE with instructions, rather than quietly cleared.

This **lowers** the headline number, which is the point. Re-measured:

```
measurements : 417  (139 layers x 3 scenes)
PASS         : 270 / 417  (64.7%)
layers clean : 90 / 139
failures     : 147  - all of them "contamination status unknown"
```

147 is exactly 49 layers x 3 scenes. Nothing else changed, and that is the
important part:

| | before Fix 7 | after Fix 7 |
|---|---:|---:|
| Measurements failing a **colour** gate | 0 / 417 | **0 / 417** |
| palette_score min / median / max | 93.5 / 98.1 / 99.5 | **93.5 / 98.1 / 99.5** |
| Overall pass | 100% | 64.7% |

So the honest statement of where the colour work landed is **not** "64.7%". It
is two separate facts:

- **Colour identity: 417 / 417.** Every layer, under every scene light, holds
  its palette within all three dE rules, adversarially verified.
- **Overall likeness gate: 270 / 417**, because 49 layers cannot be certified
  free of card bleed at all.

The 49 layers are not newly broken; they were never known to be sound. They are
30 Clever, 17 Scarline, 1 Ash, 1 Static, and they need human review or a re-cut
from source. That is a **materials** problem, not a metric problem.

---

## The loop cannot close on `protect_neutrals`, and that is the real finding

`protect_neutrals` was still 0.85 by inheritance — chosen back when relight
preserved hue by scaling RGB ratios, which it no longer does. So it was
re-swept against the corrected relight, reporting library pass **and** control
escapes at each level, on the rule that a level which passes everything is a
failed experiment:

| `protect` | library pass | min | median | control escapes | best broken |
|---:|---:|---:|---:|---:|---:|
| 0.70 | 61/66 | 94.7 | 96.4 | 0 | 93.8 |
| 0.80 | 66/66 | 96.4 | 97.5 | 0 | 93.8 |
| 0.85 | 66/66 | 96.6 | 98.0 | 0 | 93.8 |
| 0.90 | 66/66 | 96.7 | 98.6 | 0 | 93.8 |
| 0.95 | 66/66 | 96.7 | 99.2 | 0 | 93.8 |
| **1.00** | 66/66 | **96.8** | **99.8** | 0 | 93.8 |

Read naively, that says **use 1.00**. It is monotone: the more the character is
protected, the better it scores. But look at what 1.00 actually does to the art,
measured as the character's mean chroma response to a strong red key:

| `protect` | chroma response to the scene light |
|---:|---:|
| 0.70 | 2.92 |
| 0.85 | 1.55 |
| **1.00** | **0.26** |

At 1.00 the character **does not respond to the light at all**. It is a cut-out
pasted onto a plate — which is exactly the failure the compositor was built to
prevent, and exactly what the previous system did with its row of opaque
reference cards.

**The likeness metric has a degenerate optimum.** It measures identity
preservation, and identity preservation is trivially maximised by doing nothing.
The counter-pressure — *the character must belong in the scene* — is not
measured anywhere, so no sweep of this parameter can terminate honestly.

This is a limit of the loop, not of the parameter. Optimising a one-sided metric
gets you a one-sided answer. `protect_neutrals` stays at **0.85** for now, which
is the value the visual checks in Fix 3 were made against — an inherited value,
honestly labelled as such, not a measured optimum.

Closing this needs a second measure on the opposing axis, scored so an interior
optimum exists.

---

## The opposing axis — scene integration

### Four designs, four failures, one failure

Four independent designs were commissioned for "does this character belong in
this plate's light?", through deliberately different lenses — colorimetric
agreement, local-context agreement, shading-direction agreement, and illuminant
recovery — and each was then attacked by an independent reviewer told to default
to *does not survive*.

**All four were broken.** More usefully, they broke the same way three times
over:

1. **The plate was never load-bearing.** In one, deleting the plate changed the
   score by 0.000000. In another the plate reduced to a sign bit. A measure of
   "does this belong *here*" that gives the same answer with the *here* removed
   is not measuring integration.
2. **They measured chroma and only chroma.** So all four were beaten by an
   object with a colour filter and no light.
3. **They were scale-free in `key_strength`.** An invisible light scored
   perfectly, because dividing by the contract's own prediction cancels the
   contract's own strength.

### The composite, and re-verifying it rather than trusting it

The surviving design is a composite — chroma response measured along the axis
recovered from the **plate's own pixels**, with an absolute visibility floor
under the denominator, gated by whether a *lighting* operation happened at all.

It arrived with a long list of measured claims. Those claims were re-run here
rather than accepted, and that mattered:

| Claim | Independent result |
|---|---|
| Monotone decreasing in `protect_neutrals` | **Holds** — 98.2 → 0.6 across 0.0 → 1.0 |
| Plate is load-bearing | **Holds** — neutral plate returns *unscoreable*; a warm-cast plate returns 0.0 |
| Not scale-free in `key_strength` | **Holds** — 34.6 / 35.9 / 38.3 / 47.2 / 37.1 across a 80× range, with an overshoot penalty at the top |
| Not a reparametrisation of the dial | **Holds** — R² on `(1 − protect)` alone is 0.796, residual sd 15.3 points |
| "The decal scores 0.0" | **FALSE — 46.6, against an honest relight's 47.2** |

The decal is the adversary that killed one of the four originals, and the
composite claimed to have fixed it. It had not. Its own control was too weak: a
colour filter with essentially no lightness change (mean |dL\*| ≈ 0.15). A real
sticker darkens.

### The fix — a partial correlation

The mechanism failed for a reason worth writing down. The measure compared the
candidate's lightness-change field against the declared light's by **raw
correlation**. But `relight()` and a flat multiply are *both multiplicative*, so
both produce a dL\* field proportional to the figure's own albedo — and that
shared component dominates. Measured correlation between an honest relight and a
flat decal matched to its mean colour: **r = 0.8398**.

The term was measuring the character's albedo, not the light's direction.

It is now a **partial** correlation, controlling for the figure's luminance, so
only the part a light's direction contributes is compared:

| | before | after |
|---|---|---|
| Flat decal, 9 character × protect cells | rejected in **0** | rejected in **9** |
| Honest relight (protect 0.00 / 0.50 / 0.85) | 98.2 / 87.5 / 47.2 | **98.2 / 87.5 / 47.2** |
| Lit from 270° against a 90° contract | 5.3 | **0.0** |

Closing the hole while costing the honest signal *exactly nothing* is the same
shape as Fix 6 above, and is the strongest evidence available that a fix is real
rather than a threshold moved.

### Status: reported, not gated

Likeness has **1,089** adversarial controls behind it. This has roughly 400. So
`composite_panel()` records `integration_score` for every placement and warns
below 25 — a character that barely responds to the panel's light reads as pasted
on — but **likeness remains the only hard constraint.** Promoting this to a gate
needs the same treatment likeness got.

On the exp009 panel both numbers now appear in the record: likeness 85.3 / 85.9,
integration 79.3 / 64.4, with the measure noting that the contract can only move
a real surface 2.40 dE along the plate's illuminant axis — under its own
visibility floor.

### What this does not settle

The one real calibrated plate available is cool-lit, and the measure correctly
refuses to score a contract whose light opposes the plate's own. So the warm and
red keys used throughout this work are **off-diagonal cells that return 0.0 by
design** against this plate, and could not be validated here. That is a coverage
limit of the evidence, not a property of the measure, and it will not be
resolved until there are plates lit for those scenes.

`protect_neutrals` therefore stays at **0.85**. There is now a second axis to
choose it against, but not yet enough validated scenes to choose it on.

---

## Wiring it into the pipeline — and what that immediately found

A metric nothing calls is documentation, not a gate. Until now `likeness.py` was
only ever invoked by validation scripts: `composite_panel()` could stage a panel
with no record of whether its characters still looked like themselves, and once
a character is composited onto the plate it cannot be separated from the
background, so the number is no longer recoverable.

`composite_panel()` now measures every placement while the reference is still
aligned — after flip and depth blur (legitimate staging), before relight and
haze (both of which move colour) — and records it:

```json
"likeness_score": 85.3, "likeness_passed": false,
"likeness_palette_de": 2.36, "likeness_pixel_drift_de": 2.30,
"likeness_notes": ["rendered at 149px tall; below 320px ..."]
```

`CompositeReport.likeness_passed` is true only if every staged character
cleared, and a failure raises a `LIKENESS:` warning rather than producing a
quiet panel.

### It failed on the first real panel — for a reason worth having

exp009 re-stages two approved characters on a real calibrated plate:

| character | layer | height | score | palette dE | pixel dE | verdict |
|---|---|---:|---:|---:|---:|---|
| MZ-CHAR-005 | neonblue_16_worried | 149 px | 85.3 | 2.36 | 2.30 | FAIL |
| MZ-CHAR-001 | moodz_00_clean_base | 136 px | 85.9 | 1.50 | 1.47 | FAIL |

**Colour is clean.** Both are well inside every dE tolerance — the relight work
above is holding on a real panel. They fail on **size**.

And the size failure is not a staging slip. On the school-pa-zone calibration
scaled to this plate:

| foot_y | character height | legible (≥320)? |
|---:|---:|---|
| 700 | 110 px | no |
| 830 (frame bottom) | 167 px | no |
| **1185** | **320 px** | yes — but the frame is only 832 tall |

**No ground-plane-correct staging on this plate can produce an
identity-legible character.** All four approved plate calibrations pick a
reference object of roughly 0.4–1.0 m and treat it as one whole chibi character
height, which is self-consistent — these plates are simply framed as *wide
shots* for chibi-proportioned characters.

That is an art-direction question, not a metric bug, and not mine to settle. So
the gate was **not** weakened. Instead `Placement.identity_critical` (default
**True**) allows a per-placement, recorded waiver of the size floor for a figure
the script does not ask the reader to recognise. It waives **size only** —
colour identity stays gated — and it writes `LEGIBILITY EXEMPT` with the
measured height into the panel record, so an approval step sees exactly what was
waived. Without that, the pressure would be to disable the gate wholesale, which
is worse.

**This needs an owner ruling** (see below).

---

## What is NOT yet proven

- **The metric protects colour identity. For a near-achromatic character it has
  little to measure.** Ash averages chroma 2.3 — a hue swap moves him less than
  the tolerance, correctly, because his identity is carried by shape and value
  rather than colour. Those two axes are *not* covered by this metric for any
  character. This is the largest honest limitation of the current gate.
- 49 layers remain UNDETERMINED for bleed (30 Clever, 17 Scarline, 1 Ash, 1
  Static) - cropped to a different size from their source sheets and so
  unalignable. Since Fix 7 they FAIL rather than silently pass, but that is a
  refusal to guess, not a resolution: they still need human review or a re-cut
  from source before any of them can be used in a panel.
- The metric measures palette, contamination and size. It does **not** measure
  whether the face is drawn correctly — that remains a human judgement, and the
  approved-art pipeline is what makes it safe to assume.
- Legibility is inferred from rendered height against a threshold, not from an
  actual 1:1 print-size proof.
- Zombie is represented by a single layer (3 measurements). Lil Devil has none
  at all. The 100% covers the library that exists, not the cast.
- Everything here is measured on **relight of approved layers**, which is the
  compositing path. It says nothing yet about generated backgrounds or about
  panels assembled end to end.
- `protect_neutrals` has now been re-swept against the corrected relight, and
  the sweep **cannot pick a value** - likeness is monotone toward 1.00, where
  the character stops responding to the scene light entirely. It stays at 0.85
  as an inherited value, not a measured optimum. See the section above.
- The worst broken input scores 94.9 against a gate of 95.0. Damage that moves
  the whole figure by less than about 3 dE is not reliably caught.
- The 320 px legibility floor is a ramp, not a cliff: 320 px scores 100 and the
  85 gate bites below roughly 272 px. That is the existing calibrated design,
  but it means "320 px floor" overstates how hard the rule is.

---

## Owner rulings needed

**R-01 — Panel framing vs. character legibility.** All four approved plate
calibrations frame chibi characters as wide shots. On school-pa-zone a character
standing at the very bottom of an 832 px frame is 167 px; the 320 px legibility
floor would need `foot_y = 1185`. Three options, and this is an art-direction
call:

1. **Tighter plates.** Generate panel plates framed for the shot the script
   asks for, rather than staging every panel on a location-wide establishing
   plate. Most faithful to the format standard; most new plate work.
2. **Declare figures non-identity-bearing.** Use `identity_critical=False` for
   background presence, and accept that panels on these plates are long shots
   where the reader is not asked to recognise anyone. Cheapest; changes how the
   issue reads.
3. **Break the ground plane.** Composite characters larger than perspective
   allows. Not recommended — it reintroduces exactly the "row of equal-sized
   cards" failure the compositor was built to prevent.

Until this is ruled, panels staged on these plates will fail the likeness gate
on size, which is the gate behaving correctly.

**R-02 — `calib_height_in_characters` is undeclared on all four calibrations**,
so each defaults to 1.0: the reference object is treated as one whole chibi
character. The notes support that reading (objects of ~0.4–1.0 m described as
"chibi character scale"), and the school-pa-zone note calling its 0.9 m sill
"chibi head height" is most likely loose phrasing rather than a different unit.
Worth an explicit confirmation, because if any of them meant *head* height, that
plate's characters are roughly 2.5x too small and R-01 partly dissolves.
