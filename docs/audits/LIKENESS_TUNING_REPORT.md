# Likeness Tuning Report

**Goal:** make "consistent character likeness" a measured number, then drive it
to a consistent pass across the whole approved layer library.

**Run date:** 2026-07-28. Baseline: both the repo copies and the factory
originals matched the migration manifest hash-for-hash at the start of this
work, so every number below is against a verified, reproducible input state.

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
| Palette fidelity | 55% | ≥ 92 | Area-weighted CIE76 dE between each canon swatch and its nearest rendered colour |
| Contamination | 25% | ≥ 99 | Card-bleed pixels inside the silhouette |
| Feature legibility | 20% | ≥ 85 | Rendered height against the size below which small features stop reading |

**A pass requires the overall score ≥ 95 AND every component gate.** A high
average must never hide a failed component — the same rule as the panel approval
standard, where a 99 with an extra hand still fails.

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

## Current position

| Stage | Pass rate | Layers clean across all 3 scenes |
|---|---:|---:|
| Original relight, original layers | 56.4% | 63 / 139 |
| After bleed repair | 82.3% | 97 / 139 |
| After hue-safe relight | *sweep in progress* | — |

---

## What is NOT yet proven

- The hue-safe relight has been measured on 6 characters and visually checked on
  one panel. The full 417-measurement sweep across four `protect_neutrals`
  values was still running when this was written.
- 49 layers remain UNDETERMINED for bleed, mostly Clever's 30 (the layers are
  cropped to a different size from their source sheets and cannot be aligned).
  These need human review or a re-cut from source.
- The metric measures palette, contamination and size. It does **not** measure
  whether the face is drawn correctly — that remains a human judgement, and the
  approved-art pipeline is what makes it safe to assume.
- Legibility is inferred from rendered height against a threshold, not from an
  actual 1:1 print-size proof.
