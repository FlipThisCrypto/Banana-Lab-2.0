# Issue 001 — Visual Problems

What is wrong with the existing artwork, with evidence. Per-panel judgements are
in `panel-salvage-matrix.csv`.

---

## 1. The headline finding

**Issue 001 has no finished artwork.** All 24 panel images are one of:

- a **draft composite** — a background plate, darkened, with opaque character
  reference cards pasted in a row near the bottom inside coloured boxes, and a
  caption strip below (19 panels), or
- a **raw generation artefact** — an image that is not a comic panel at all
  (5 panels).

The draft composites announce themselves. Each carries a baked-in header reading
`MZ-2026-08-01_P0N_PANELNN · DRAFT COMPOSITE`, and that header **is visible on
the assembled, published pages**. `metadata.json` records
`"ArtTier": "draft_composite"`.

This was not hidden. It was labelled, approved, QA-passed and published.

---

## 2. The five non-panels

| Panel | What the image actually is |
|---|---|
| `P01_PANEL02` | On the published page: **five off-model pink figures** with long tails and blue tube tops. Not MonkeyZoo characters of any kind. Carries Lil Devil's dialogue. |
| `P02_PANEL01` | A single enormous blurred pink blob resembling a face, filling frame. |
| `P02_PANEL02` | A tiled wallpaper pattern of small monkey blobs on blue. |
| `P02_PANEL03` | A tiled pattern of grey monkey blobs. |
| `P05_PANEL01` | A dense pile of blue and white monkey heads. |

**Page 2 of the published issue contains zero valid artwork** — all three of its
panels are from this list. Page 1's second panel is the off-model pink figures.

---

## 3. Background reuse

Measured with `scripts/inventory/analyze_legacy_panels.py`:

```
24 panels -> 9 distinct background plates

  reuse x 8: P01_PANEL01, P03_PANEL01, P03_PANEL02, P03_PANEL03,
             P05_PANEL03, P08_PANEL01, P08_PANEL02, P08_PANEL03
  reuse x 5: P04_PANEL01, P04_PANEL02, P04_PANEL03, P07_PANEL01, P07_PANEL02
  reuse x 4: P05_PANEL02, P06_PANEL02, P06_PANEL03, P07_PANEL03
  reuse x 2: P01_PANEL03, P06_PANEL01
  reuse x 1: (each of the five non-panels)
```

Four real plates carry 19 panels. The festival-grounds plate appears **eight
times, pixel-identical, with no camera move** — including on page 1 and page 8,
so the closing "festival continues in reduced form" looks exactly like the
opening arrival. The story beat is contradicted by the art.

Root cause: only four festival location plates exist in approved canon, and the
pipeline had no way to derive new camera angles from them.

---

## 4. Character integration

This is the defect the brief names, and it is total.

| Requirement | Legacy state |
|---|---|
| Correct scale | Every character is the same size regardless of depth |
| Perspective match | None — cards are axis-aligned rectangles |
| Ground contact | None — cards float in a horizontal band |
| Contact shadow | None |
| Cast shadow | None |
| Light direction match | None — cards keep their own flat studio lighting |
| Colour spill from environment | None |
| Edge treatment | Hard rectangular card border, plus a coloured box frame |
| Occlusion | None |
| Atmospheric perspective | None |
| Eye lines | Cards face front regardless of who is speaking |

The characters are not composited into the scene. They are **displayed beside
it**, like a cast list. Several cards even retain a `#99-5` catalogue number and
a `MonkeyZoo` watermark from the reference sheet they were cut from.

This is exactly the failure mode the brief describes as "generated separately
rather than occupying the same physical space" — in its most extreme form.

---

## 5. Panel uniformity

- 22 of 24 panels share one aspect ratio (1280×960).
- Pages 3, 4, 5, 6, 7, 8 are all the same three-equal-rows grid.
- The script called page 4 a **full-bleed splash** for the issue's central lore
  beat. The art delivered three equal standard panels. The most important image
  in the issue got the same box as a transition.
- No close-ups anywhere. Every character read is at the same distance, because
  the card-paste method has no notion of shot size.
- No insets, no borderless panels, no bleeds, no size variation for emphasis.

---

## 6. Story content missing from the art

Several panels carry their story entirely in the caption, with nothing in the
image:

| Panel | Stated in text | Present in image |
|---|---|---|
| `P03_PANEL02` | Screens flash fractured cyan shapes | No cyan fracture |
| `P06_PANEL01` | Five thousand people at the main stage | No crowd |
| `P06_PANEL02` | A group trapped behind an emergency shutter | No trapped group |
| `P07_PANEL03` | Trapped festival-goers step out safely | Nobody exits |
| `P08_PANEL02` | A cyan Echo segment flickers | No Echo segment |

The season hook — the whole reason the issue exists in a six-issue arc — **is
not on the page**.

---

## 7. Style incoherence

Each draft composite contains two incompatible styles: a painterly, atmospheric,
semi-realistic neon background, and flat vector cartoon characters with thick
uniform outlines. The plates do not match the Mango Pier house style either.

This will recur unless controlled: the only checkpoints installed are
`RealVisXL_V4.0` (photoreal) and `animagine-xl-4.0` (anime), with **no style
LoRA**. Left alone, the generator produces backgrounds that fight the cast.

---

## 8. Measured against the real target

The owner designated the published Fiend Studios editions as the style target
on 2026-07-28. Against those, the gap is wider than the draft-tier problem
alone. Full standard: `canon/style/HOUSE_STYLE.md`.

| House style requirement | Legacy Issue 001 |
|---|---|
| Irregular panel grid, different on every page | One three-equal-rows grid on six of eight pages |
| Panels on a coloured page ground with borders and gutters | Panels butted onto a plain page |
| Characters integrated with cast shadows and colour spill | Opaque cards floating in a row |
| Illustrated backgrounds with visible practical light sources | Four plates reused 19 times |
| Large stylised SFX integrated into the scene | Small flat text labels |
| Colour-coded balloons for an ensemble cast | Uniform white balloons |
| Full-page splash reserved for genuine peaks | Splash specified in the script, never produced |
| Fiend Studios collectible stamp on the cover | Absent |
| Extreme shot-size range including macro and empty breath panels | One shot size throughout |

### Defects in the secondary reference

Mango Pier is a useful cast-consistency reference but is **not** the target, and
carries defects the published editions do not have:

- **Baked-in furniture in the panel art**: a "MonkeyZoo" logo bar rendered
  inside `P05_PANEL01`, `P07_PANEL01`, `P07_PANEL02`; character name labels
  ("Moodz", "Emo", "NeonBlue") baked into `P07_PANEL01`; white frames rendered
  into several panels.
- **Row staging**: front-facing lineups at equal scale dominate the issue.
- **Blob extras**: background crowds as featureless coloured shapes.
- **Flat camera**: almost everything at eye level.

Banana Lab 2.0 requires panel art to be **frameless and textless**. Borders,
page ground, balloons, captions, SFX and the stamp are added downstream. That
separation is exactly what makes the published editions' irregular layouts
possible without regenerating artwork.

---

## 9. Severity roll-up

| Severity | Count | Nature |
|---|---|---|
| BLOCKER | 6 | Five non-panels plus the off-model page-1 figures |
| CRITICAL | 11 | Draft-tier art for load-bearing story beats; missing story content |
| MAJOR | 7 | Plate repetition; layout intent lost; supporting cast underserved |

**No panel is approvable.** Under the Banana Lab 2.0 quality standard, an issue
with unresolved BLOCKER, CRITICAL or MAJOR defects cannot be marked
production-ready — so the correct status for the legacy issue is *not released*,
regardless of what the legacy workflow file records.

---

## 10. Why the previous QA passed

`source_material/legacy_reference/issue-001-2026-08/qa_report.md` reads
`VERDICT: PASS`, with `Evidence blockers: None`.

Its entire panel-level check was, 24 times:

```
- MZ-2026-08-01_P01_PANEL01: present; PNG; 1280x960; no file error
```

The gate tested **file existence, format and dimensions**. Nothing else. A
tiled wallpaper pattern passes that test perfectly. So do five off-model pink
aliens.

This is the specific failure Banana Lab 2.0's quality standard exists to
prevent, and the reason `docs/quality/QUALITY_STANDARD.md` opens by stating that
a machine gate may only *reject*, never *approve*.
