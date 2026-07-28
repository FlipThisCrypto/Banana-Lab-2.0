# Moodz — Known Failures

`MZ-CHAR-001` · slug `moodz` · written 2026-07-28 · **status: draft, not owner-approved**

Real defects, observed in this repository during the 2026-07-28 panel production
run, or measured from the approved art during this audit. Nothing here is
hypothetical. Where something is a risk rather than an observed defect, it says
so.

Codes from `docs/quality/DEFECT_TAXONOMY.md`.

---

## KF-MZ-01 — Mirroring moves the blue accent and fringe to the wrong eye

| | |
|---|---|
| **Code** | `IDENT-CANON-VIOLATION` |
| **Severity** | **BLOCKER** |
| **Status** | Fixed — the compositor now refuses. First observed EXP-004. |
| **Evidence** | `docs/audits/PANEL_PRODUCTION_LOOP_REPORT.md` EXP-004 defect table; `app/services/compositor.py` NO_FLIP; `workflows/comfyui/experiments/exp005-composite-v2/exp005_report.json` warning |

**This is the serious one.** It is a canon violation that the compositor
introduced by itself, from a staging choice that looked innocuous.

Moodz's identity is asymmetric. The black emo fringe sweeps over one eye and the
blue accent runs down one side. Horizontally mirroring the layer — a routine
thing to do when you want a character facing the other way — moves both to the
wrong side. The result is still recognisably a monkey in a studded jacket, which
is exactly why it slipped through: it does not look broken, it looks fine, and
it is wrong.

Measured basis for the rule (this audit): the horizontal centroid of
blue-accent pixels, as a fraction of silhouette width with 0.0 at the
viewer-left edge:

| Layer group | Blue centroid |
|---|---|
| All 17 front-facing layers | 0.25 – 0.45 (left of centre, without exception) |
| `moodz_30_backview.png` | 0.54 (centred — consistent with a rear view) |

**Mitigation now in code:**

```
NO_FLIP["MZ-CHAR-001"] = "black fringe over one eye, blue accent on the left"
```

The compositor **refuses** the flip, forces `flip` to false, and emits:

```
CANON: refused to mirror MZ-CHAR-001 - black fringe over one eye, blue accent on the left
```

That warning is present in `exp005_report.json`. There is a regression test for
it (`tests/production_validation/test_comfyui_pipeline.py`, per the run report's
test table: *"Canon: no mirroring — asserts the guard fires and `flip` is forced
false"*).

**Residual gap.** The QA review package's own
`12_qa/review-packages/ISSUE001-P16-02/placement_report.json` carries
`"warnings": []` while `exp005_report.json`, with byte-identical placements,
carries the CANON warning. The warning that proves the guard worked is not in
the artefact a reviewer reads. Fix the review-package writer so compositor
warnings survive into QA.

---

## KF-MZ-02 — Relight above ~0.25 key strength desaturates cel-shaded art

| | |
|---|---|
| **Code** | `INTEG-LIGHT-COLOR` |
| **Severity** | MAJOR |
| **Status** | Mitigated by convention, not by code |
| **Evidence** | `docs/audits/PANEL_PRODUCTION_LOOP_REPORT.md` EXP-004 defect table and EXP-005 variables |

EXP-004 ran the compositor's relight at key strength 0.50 with fill 0.20. Both
characters came out desaturated. Cel-shaded art carries its shading as flat
hard-edged fills; multiplying a lighting term over those fills washes the flats
toward the light colour and destroys the very thing that makes the art read as
house style.

EXP-005 dropped key to **0.22** and fill to **0.10** and the desaturation went
away. The report's own conclusion is *key strength ≤ 0.25 for cel-shaded art*.

Moodz is the more exposed of the two characters here. 44% of his opaque pixels
are `#000000` and his identity rides on a **grey**-on-**pale grey** eye ring and
a **pale grey** stitched chest panel. There is very little chroma to lose before
those details stop separating.

This is a convention, not an enforced limit. The `LightContract` default in
`app/services/compositor.py` is still `key_strength: 0.55` and
`fill_strength: 0.18` — i.e. **the default configuration reproduces the
defect**. A caller that constructs a `LightContract` without overriding these
will hit it.

Applies equally to NeonBlue.

---

## KF-MZ-03 — Eye lines cannot be directed

| | |
|---|---|
| **Code** | `STAGE-EYELINE` |
| **Severity** | MAJOR |
| **Status** | **UNSOLVED.** No mitigation exists. |
| **Evidence** | Layer inventory + inspection; `docs/audits/PANEL_PRODUCTION_LOOP_REPORT.md` §4 and Limitation 5 |

The composable layer set is 18 files. Seventeen are front-facing; the
eighteenth, `moodz_30_backview.png`, is a back view. There is **no three-quarter,
profile or over-shoulder layer with an alpha channel**.

Consequence: Moodz looks at the camera or away from it, and nothing in between.
Two characters "looking at each other" is not achievable from this library. This
blocks true conversation staging — the exact panel type the one validated panel
claims to be.

Three-quarter (`02_threeqtr`), profile (`03_profile`), over-shoulder
(`04_overshoulder`) and portrait (`05_portrait`) references **do exist** — in
`source_material/imported_canon/approved_characters/moodz/` at 912×1216 — but
every one of the 31 PNGs in that directory is flat **RGB with no alpha**. They
cannot be composited without a matte pass that has not been built.

The report's proposed route is ControlNet openpose over approved art. The
`controlnet-union-sdxl-1.0-promax` model is installed. It has never been run for
this purpose. Do not treat the proposal as a plan until it has.

---

## KF-MZ-04 — Orange card background survives in the RGB channels

| | |
|---|---|
| **Code** | `INTEG-MATTE-HALO` |
| **Severity** | MAJOR |
| **Status** | Measured, partially mitigated. Present in the source files today. |
| **Evidence** | Measured during this audit; visible on inspection of `moodz_00_clean_base.png` |

Every Moodz alpha layer keeps the original orange card background in its RGB
channels underneath `alpha == 0`. Measured corner pixels of
`moodz_00_clean_base.png`: `(236, 142, 78, 0)`, `(234, 142, 79, 0)`,
`(235, 142, 81, 0)` — orange at zero alpha, i.e. `≈ #EB8E4F`.

Unlike NeonBlue, Moodz's mattes leak into **opaque** pixels:

| Layer | Semi-transparent px (0 < α < 255) | Opaque px within ΔRGB 60 of the card colour |
|---|---:|---:|
| `moodz_00_clean_base.png` | 25 600 | **1 740** |
| `moodz_10_walking.png` | 27 031 | **2 230** |
| `neonblue_16_worried.png` (for comparison) | 27 809 | 97 |
| `neonblue_27_defeated.png` (for comparison) | 27 663 | 23 |

That is roughly two orders of magnitude more residual card colour than NeonBlue.
Visual inspection of `moodz_00_clean_base.png` confirms it: there is a warm
fringe along the black outline and an orange patch behind the tail that is
opaque, not soft-edge.

**Partial mitigation:** `erode_alpha()` in `app/services/compositor.py` pulls the
matte in by one pixel by default, and its docstring records matte haloes as a
recurring defect in the previous project's own notes. A one-pixel erode does not
remove 1 740 opaque pixels.

Check the tail and the outer silhouette on every Moodz panel.

---

## KF-MZ-05 — `moodz_25_crouching.png` is not crouching

| | |
|---|---|
| **Code** | `ASSET-WRONG-PANEL` (asset mislabelled) |
| **Severity** | MAJOR |
| **Status** | Open — discovered by inspection during this audit |
| **Evidence** | Visual inspection; alpha bounding box; `app/services/compositor.py` NON_STANDING_POSES |

`moodz_25_crouching.png` shows Moodz **standing upright**, feet apart, weight on
both soles. It is not a crouch.

Supporting measurement: its alpha bounding box is `(112, 212, 769, 1038)` —
identical to `moodz_00_clean_base.png`'s `(112, 212, 769, 1038)`. Same
silhouette envelope as the standing clean base. (The files themselves are
distinct: all 18 Moodz layers are md5-unique. The artwork differs — the
mislabelled layer has a black jacket and black hands where the clean base has
brown — but the posture is the same.)

Two consequences:

1. **The slug-based guard misfires.** `NON_STANDING_POSES["crouching"]` will warn
   that this layer needs a non-zero `contact_offset`. It does not. A reviewer who
   trusts the warning will introduce an error correcting a non-error.
2. **Moodz has no crouching art.** Any panel scripted for a crouch has no asset.

The guard keys on the filename, not the image. That design is fine — it is cheap
and it caught a real defect for NeonBlue — but it inherits whatever the filenames
claim. This is the first confirmed case where a filename lies.

Related: the layer named `defeated` was verified as genuinely seated **for
NeonBlue** and is listed as non-standing in the compositor. `moodz_27_defeated.png`
was **not** visually verified in this audit. Do not assume it matches NeonBlue's.

---

## KF-MZ-06 — `moodz_15_laughing.png` does not carry the asymmetric fringe

| | |
|---|---|
| **Code** | `IDENT-MISSING-FEATURE` |
| **Severity** | CRITICAL if the layer is used |
| **Status** | Open — needs an owner ruling |
| **Evidence** | Visual inspection during this audit |

The bible lists *black emo fringe over one eye* under
`features_that_must_never_change`, strength `defining`.

`moodz_15_laughing.png` uses the blue **beanie** variation with a straight,
symmetric fringe across the forehead. Neither eye is covered. The beanie itself
is in canon — the bible explicitly permits *"blue hair accent/headband/beanie
variation"* — but the defining asymmetric fringe is absent.

So the approved layer library contains a layer that fails the character's own
identity checklist. Either the fringe rule has an unwritten beanie exception, or
this layer is off-model. That is an owner call, not a QA call.

Practical note: the beanie layers are also measurably taller —
`moodz_15_laughing` has a silhouette height of 940 px against 826 px for
`moodz_00_clean_base`, a 14% swing on the same canvas with the same foot line.
Cutting between them inside a scene will read as Moodz growing.

---

## KF-MZ-07 — Jacket colour is inconsistent across the approved layer set

| | |
|---|---|
| **Code** | `IDENT-WARDROBE-DRIFT` / `ISSUE-CONTINUITY` |
| **Severity** | MAJOR |
| **Status** | Open — needs an owner ruling |
| **Evidence** | Measured during this audit; three visual spot-checks |

The bible specifies an *open black studded leather jacket*. Measured brown-pixel
coverage in the torso region splits the eighteen layers into two groups:

| Group | Layers | Torso brown px |
|---|---|---|
| **Brown** jacket | `00_clean_base`, `10_walking`, `16_worried`, `18_sleepy`, `19_determined`, `24_thinking` | 5 249 – 8 550 |
| **Black** jacket | `15_laughing`, `17_disgusted`, `20_confused`, `21_running`, `22_jumping`, `23_waving`, `25_crouching`, `26_reaching`, `28_celebrating`, `29_lookingup`, `30_backview` | 0 – 1 307 |
| Intermediate | `27_defeated` | 2 175 |

Visual spot-checks agree with the measurement: `00_clean_base` has a brown
jacket and brown mitten hands; `25_crouching` and `15_laughing` have a black
jacket with grey lapel detail and black hands.

`moodz_00_clean_base.png` — the file `CHARACTER_IMAGE_INDEX.md` names as the
primary production reference, and the file used in the one panel produced this
run — is in the **brown** group, i.e. the group that contradicts the bible.

**Do not resolve this by repainting the art.** Flag it. Meanwhile, treat the two
groups as mutually exclusive within a scene.

---

## KF-MZ-08 — Character bible reference paths do not resolve

| | |
|---|---|
| **Code** | `ASSET-MISSING` |
| **Severity** | CRITICAL for any tool that reads the bible |
| **Status** | Open |
| **Evidence** | `source_material/imported_bibles/character-bibles/MZ-CHAR-001/` directory listing |

`bible.yaml` declares `primary_reference_image: references/primary/primary-reference.webp`
plus nine supporting images under `references/alternate/` and `references/group/`.

**No `references/` directory exists** — not under MZ-CHAR-001, and not under any
of the twelve character bibles in this repository. MZ-CHAR-001 contains exactly
four files: `bible.md`, `bible.yaml`, `continuity-log.md`, `development-notes.md`.

Resolve from `source_material/imported_canon/approved_characters/moodz/` and
`source_material/imported_canon/character_layers/moodz/` instead.

Minor, related: `moodz.webp` and
`4cc8de245f2f6e1e777cdd9ea1d650a893d7c4d7ba27d8e78cc327551cfc62bc_512.webp` in
the approved directory are byte-identical (md5 `b5703f78…`). Redundant rather
than conflicting, but cite `moodz.webp`.

---

## Not a Moodz failure, but it will look like one

`ISSUE001-P16-02` was composited at **960×1024** and delivered at **1534×1642**.
1534/960 = 1.598 and 1642/1024 = 1.604 — the delivery resize is about 0.35%
anisotropic. It is a stretch, not a scale. Too small to see, large enough to
matter if it compounds across a pipeline. Recorded, not fixed.

---

## Failure modes that have NOT been tested for this character

Absence of a recorded failure here is not evidence of success.

| Area | Status |
|---|---|
| Any camera angle other than eye-level front | Never attempted |
| Foreground occlusion | Never attempted |
| Prop interaction | Never attempted |
| Action / movement staging (`running`, `jumping`, `walking` layers) | Never attempted |
| Seated staging | No alpha asset exists (`moodz_12_sitting.png` is flat RGB) |
| Numeric verification of Moodz's own contact shadow | Never done — the recorded measurement covers NeonBlue's contact region only |
| `inpaint_repair` against a real defect | Workflow built, never executed |
| IP-Adapter reference path | Model installed, never used for this character |
| ControlNet pose path | Model installed, never used for this character |
| Any composite working space other than 960×1024 | Never attempted |
| Three successful runs of any panel type | Never achieved — the maximum is one |
