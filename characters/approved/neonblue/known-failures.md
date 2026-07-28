# NeonBlue — Known Failures

`MZ-CHAR-005` · slug `neonblue` · written 2026-07-28 · **status: draft, not owner-approved**

Real defects, observed in this repository during the 2026-07-28 panel production
run, or measured from the approved art during this audit. Nothing here is
hypothetical. Where something is a risk rather than an observed defect, it says
so.

Codes from `docs/quality/DEFECT_TAXONOMY.md`.

---

## KF-NB-01 — Seated pose placed as standing

| | |
|---|---|
| **Code** | `STAGE-POSE-MISMATCH` + `INTEG-NO-GROUND-CONTACT` |
| **Severity** | CRITICAL |
| **Status** | Guarded (warns), first observed EXP-004 |
| **Evidence** | `workflows/comfyui/experiments/exp004-composite-v1/exp004_report.json` — `{"layer": "neonblue_27_defeated.png", "foot_y": 960, "scale_multiplier": 1.0}` |

`neonblue_27_defeated.png` is a **seated** pose. Visually confirmed in this
audit: NeonBlue is sitting on the ground, legs forward, weight on his hips, feet
out in front of him. Its contact point is the hips, not the soles.

In EXP-004 it was placed with a standing `foot_y`. The compositor aligns the
bottom of the trimmed layer to `foot_y + contact_offset`, so with
`contact_offset = 0.0` the bottom of the *seated* silhouette — his shoes,
sticking out forward — became the floor line. He read as sitting on the floor
plane rather than on it, at the wrong depth and the wrong height.

**Mitigation now in code.** `NON_STANDING_POSES` in `app/services/compositor.py`
lists `defeated` as `"slumped/seated - contact is the hips"` and warns when
`contact_offset` is `0.0`.

**The guard warns; it does not refuse.** Unlike `NO_FLIP`, a warning here can be
ignored by a caller that does not read the report. A correct `contact_offset`
for this layer has never been derived or recorded. Until it is, treat
`neonblue_27_defeated.png` as unusable.

Related gap: NeonBlue has **no `sitting` layer** at all. `defeated` is his only
seated art. Any panel requiring him seated is currently blocked.

---

## KF-NB-02 — Relight above ~0.25 key strength desaturates cel-shaded art

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

This is a convention, not an enforced limit. The `LightContract` default in
`app/services/compositor.py` is still `key_strength: 0.55` and
`fill_strength: 0.18` — i.e. **the default configuration reproduces the
defect**. A caller that constructs a `LightContract` without overriding these
will hit it.

Applies equally to Moodz.

---

## KF-NB-03 — Eye lines cannot be directed

| | |
|---|---|
| **Code** | `STAGE-EYELINE` |
| **Severity** | MAJOR |
| **Status** | **UNSOLVED.** No mitigation exists. |
| **Evidence** | Layer inventory + inspection; `docs/audits/PANEL_PRODUCTION_LOOP_REPORT.md` §4 and Limitation 5 |

The composable layer set is 17 files. Sixteen are front-facing; the seventeenth,
`neonblue_30_backview.png`, was confirmed in this audit to be a genuine back
view with no face. There is **no three-quarter, profile or over-shoulder layer
with an alpha channel**.

Consequence: NeonBlue looks at the camera or away from it, and nothing in
between. Two characters "looking at each other" is not achievable from this
library. This blocks true conversation staging — the exact panel type the one
validated panel claims to be.

Three-quarter (`02_threeqtr`), profile (`03_profile`), over-shoulder
(`04_overshoulder`) and portrait (`05_portrait`) references **do exist** —
in `source_material/imported_canon/approved_characters/neonblue/` at 912×1216 —
but every one of the 31 PNGs in that directory is flat **RGB with no alpha**.
They cannot be composited without a matte pass that has not been built.

The report's proposed route is ControlNet openpose over approved art. The
`controlnet-union-sdxl-1.0-promax` model is installed. It has never been run for
this purpose. Do not treat the proposal as a plan until it has.

---

## KF-NB-04 — Card background survives in the RGB channels

| | |
|---|---|
| **Code** | `INTEG-MATTE-HALO` (risk) |
| **Severity** | MAJOR if it manifests |
| **Status** | Measured property of the source files. Partially mitigated. Not observed in the one produced panel. |
| **Evidence** | Measured during this audit |

Every NeonBlue alpha layer keeps the original green card background in its RGB
channels underneath `alpha == 0`. Measured corner pixels of
`neonblue_27_defeated.png`: `(102, 223, 143, 0)`, `(97, 222, 144, 0)`,
`(98, 221, 141, 0)` — green at zero alpha, i.e. `≈ #61DE8E`.

Measured edge statistics:

| Layer | Semi-transparent pixels (0 < α < 255) | Opaque pixels within ΔRGB 60 of the card green |
|---|---:|---:|
| `neonblue_16_worried.png` | 27 809 | 97 |
| `neonblue_27_defeated.png` | 27 663 | 23 |

The bleed into opaque pixels is small for NeonBlue (tens of pixels). The
~27 000-pixel soft matte edge is the real exposure: any operation that
premultiplies wrongly, resamples RGB independently of alpha, or flattens without
compositing will pull green into the silhouette edge.

**Partial mitigation:** `erode_alpha()` in `app/services/compositor.py` pulls
the matte in by one pixel by default, and its docstring records matte haloes as
a recurring defect in the previous project's own notes.

Not observed in `ISSUE001-P16-02`. Listed because it is a measured property of
every source file, not because it has fired.

---

## KF-NB-05 — Character bible reference paths do not resolve

| | |
|---|---|
| **Code** | `ASSET-MISSING` |
| **Severity** | CRITICAL for any tool that reads the bible |
| **Status** | Open |
| **Evidence** | `source_material/imported_bibles/character-bibles/MZ-CHAR-005/` directory listing |

`bible.yaml` declares `primary_reference_image: references/primary/primary-reference.webp`
plus nine supporting images under `references/alternate/` and `references/group/`.

**No `references/` directory exists** — not under MZ-CHAR-005, and not under any
of the twelve character bibles in this repository. MZ-CHAR-005 contains exactly
four files: `bible.md`, `bible.yaml`, `continuity-log.md`, `development-notes.md`.

Any generation or QA step that resolves reference art from the bible will fail
or, worse, silently fall back. Resolve from
`source_material/imported_canon/approved_characters/neonblue/` and
`source_material/imported_canon/character_layers/neonblue/` instead.

---

## KF-NB-06 — Bible contradicts itself on the earring

| | |
|---|---|
| **Code** | `ISSUE-CANON-BREACH` (documentation-level) |
| **Severity** | MINOR, but it undermines a BLOCKER-level guard |
| **Status** | Open — needs an owner ruling |
| **Evidence** | `bible.yaml` `visual_canon.accessories` vs `visual_canon.features_that_must_never_change` |

- `accessories`: *silver gauge/plug earring in left ear* — status **`optional`**
- `features_that_must_never_change`: *left-ear silver plug earring* — status
  `canon`, strength **`defining`**

The compositor's `NO_FLIP["MZ-CHAR-005"]` guard cites the earring as its entire
justification for refusing to mirror this character. If the accessory really is
optional, the guard's stated reason is wrong for any layer that omits it.

The identity checklist takes the stricter reading. It should not have to.

---

## KF-NB-07 — Bible wardrobe text disagrees with the approved art

| | |
|---|---|
| **Code** | `IDENT-WARDROBE-DRIFT` (documentation-level) |
| **Severity** | MINOR |
| **Status** | Open — needs an owner ruling |
| **Evidence** | Visual inspection of `neonblue_00_clean_base.png`, `_16_worried`, `_27_defeated`, `_30_backview` |

`bible.yaml` says *black vest/tank* and describes *black vest and white-studded
punk pants*. The approved art shows a chocolate-brown jacket over a pale grey
**stitched** chest panel.

Separately: the bible assigns *stitched chest detail* to MZ-CHAR-004 (in
`NO_FLIP`) and *stitched pale chest* to Moodz, yet NeonBlue's art clearly carries
one too.

**Do not resolve this by editing the art.** The art is approved canon; the bible
text is a description of it and is the thing that is wrong. Flagged for the
owner.

---

## Not a NeonBlue failure, but it will look like one

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
| Action / movement staging (`running`, `jumping` layers) | Never attempted |
| `inpaint_repair` against a real defect | Workflow built, never executed |
| IP-Adapter reference path | Model installed, never used for this character |
| ControlNet pose path | Model installed, never used for this character |
| Any composite working space other than 960×1024 | Never attempted |
| Three successful runs of any panel type | Never achieved — the maximum is one |
