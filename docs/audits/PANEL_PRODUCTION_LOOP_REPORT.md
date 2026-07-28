# Panel Production Loop — Evidence Report

**Run date:** 2026-07-28 · **Target:** Issue 001 `ISSUE001-P16-02`

---

## Honest final status

### `PANEL PIPELINE PARTIALLY WORKING`

The chain works end to end and produces a coherent panel: an approved character
standing on a calibrated ground plane in a house-style plate, with contact and
cast shadows, at the exact pixel dimensions the layout spec demands. That is a
real result and it is reproducible from saved configuration.

It is **not locked**, and I am not going to call it locked. The brief requires
ten representative panel types with three successful runs each before locking.
**One panel type was validated. Two of the ten were touched. Seven were not
attempted.** Calling this validated would repeat exactly the failure this
project exists to correct.

---

## 1. Starting state

| Item | State at run start |
|---|---|
| ComfyUI connection | Live at `127.0.0.1:8188`, v0.19.3, RX 6800 / ZLUDA |
| Saved workflows in repo | **None** |
| Saved API payloads | **None** |
| Panel job schema | None |
| Compositing code | None |
| Plate calibrations | 4, none for a festival location |
| Previous process evidence | **337 jobs retained in ComfyUI `/history`** |
| Issue 001 artwork | None |

---

## 2. Root cause — what actually broke

Full detail: `COMFYUI_PREVIOUS_WORKFLOW_FORENSICS.md`.

**Nothing broke. The identity-preservation step was never built.**

All 337 retained jobs use the same six node classes:
`CheckpointLoaderSimple`, `CLIPTextEncode` ×2, `EmptyLatentImage`, `KSampler`,
`VAEDecode`, `SaveImage`.

| Node the pipeline needed | Times used in 337 jobs |
|---|---:|
| `ControlNetLoader` | **0** |
| `IPAdapterModelLoader` | **0** |
| `LoadImage` (any reference at all) | **0** |
| `LoraLoader` | **0** |
| `VAEEncode` (img2img / inpaint) | **0** |
| `ImageCompositeMasked` | **0** |

Every panel was one text-to-image roll from a **written description of the
character**. The 417 approved character art files were never connected to the
generator.

### The smoking gun

Recovered graph for `MZ-2026-08-01_P01_PANEL02_seed100102`: 7 nodes,
`animagine-xl-4.0`, 1216×832, seed 100102, prompt describing "chibi cartoon
monkey with oversized round head… NeonBlue listing duties on fingers while Li…".

Its output — recovered from `I:\ai\nft\output\MZ-2026-08-01\` — is a **pink
alien creature with a detached floating eyeball**. That image is the origin of
the five off-model pink figures on the published page 1.

Prompt and output both recovered. The causal chain is complete.

### Ruled out, with evidence

Missing workflow files, changed model paths, missing custom nodes, broken API,
wrong output directory, ZLUDA instability, lost reference images, wrong
resolution. All disproved — the graphs are intact, every node loads, 337 jobs
returned `success`, and outputs are where the graphs said.

### Why nothing was saved

There was no finished process to save. `.art-workspace/attempts/*.json` record
`"source_type": "manual_import"`, `"provider": "draft_composite"` — the pipeline
logged that a human handed it a file. Generation and assembly were never
connected.

---

## 3. Experiments

Five iterations. One variable per iteration, as required.

### EXP-001 — Which checkpoint produces house style?

**Hypothesis:** the written style contract is enough; checkpoint choice is
secondary.
**Variable:** checkpoint. Scene, size, seed, steps, cfg fixed.

| Variant | Result |
|---|---|
| `RealVisXL_V4.0` | **Coherent.** Correct one-point perspective, readable grating floor, red overhead practical, flat cel-shaded look with dark outlines |
| `animagine-xl-4.0` | **Failed.** Over-saturated primaries, incoherent wall detail reading as abstract blocks, wrong light colour |

**Outcome:** hypothesis rejected — checkpoint choice is decisive.
`RealVisXL_V4.0` adopted. Notable: the legacy Issue 001 run used
`animagine-xl-4.0` for all 49 jobs.

**Timing:** 113 s and 91 s at 1344×768, 30 steps.

### EXP-002 — Portrait plate for the real panel

**Hypothesis:** the style contract transfers to a portrait aspect and a longer,
more specific scene description.
**Variable:** aspect 1344×768 → 960×1024, and a longer scene prompt.

**Result: FAILED.** Both seeds returned **photorealistic** corridors — wet
reflective floors, volumetric neon, depth-of-field — despite `photorealistic`
already being in the negative prompt.

**Root cause identified:** the style contract was prepended only. A long scene
description carrying photographic language ("moody, high contrast, cool cyan
light spilling") pushed the style tokens out of effect.

### EXP-003 — Weighted and restated style contract

**Hypothesis:** weighting the load-bearing style terms and restating them
*after* the scene prevents dilution.
**Variable:** style contract only. Scene, seed, size, steps, cfg held identical
to EXP-002 for a clean comparison.

Change:
```
(flat 2d vector cartoon illustration:1.5), (thick uniform black outlines:1.4),
(flat colour fills with hard cel shading:1.4), …
  …scene…
(flat cartoon vector art:1.4), (bold black outlines:1.3), (cel shaded:1.3)
negative: (photorealistic:1.6), (photograph:1.6), (realistic lighting:1.4), …
```

**Result: CONFIRMED.** Same seed, same scene, same everything else — output
went from photoreal to flat cartoon with thick black linework, hard cel
shading, and a legible grid floor receding to a vanishing point.

This is the single most important finding of the run and is now protected by
regression tests.

### EXP-004 — First composite

**Hypothesis:** approved alpha layers composited onto a calibrated plate produce
a coherent panel.
**Variable:** introduced the compositor.

**Result: partial.** Characters were unmistakably the right characters and the
style was coherent — the core thesis held. But four real defects:

| Defect | Class |
|---|---|
| NeonBlue placed as standing while using a **seated** pose layer | `STAGE-POSE-MISMATCH` |
| **Moodz mirrored**, moving his blue accent to the wrong eye | `IDENT-CANON-VIOLATION` |
| Relight desaturated both characters | `INTEG-LIGHT-COLOR` |
| Characters oversized relative to the corridor | `INTEG-SCALE` |

The mirror defect is the serious one — a canon violation introduced by the
compositor itself.

### EXP-005 — Corrected composite

**Variables:** standing poses; flip refused; key colour matched to the plate's
actual cyan light rather than the script's ideal red; key strength 0.50 → 0.22;
fill 0.20 → 0.10; scale ×0.78.

**Result: PASS on the tested criteria.**

- Both characters identifiable against approved reference — NeonBlue's
  white/cyan spike crown and under-eye bags, Moodz's fringe and blue accent
- Both standing, feet on the floor
- Scale falls off correctly with depth (NeonBlue 314 px at `foot_y` 930; Moodz
  245 px at `foot_y` 820)
- No mirroring; the compositor **refused** it and logged a `CANON` warning
- No extra or missing limbs
- Style coherent between characters and plate
- Output at the layout spec's exact 1534×1642

### Shadow verification — measured, not eyeballed

Contact and cast shadows are hard to see against this plate's near-black floor,
so they were verified numerically rather than by impression:

```
pixels changed by shadow: 13252
bbox x[226-434] y[864-994]   max delta 146.3
expected contact region around y=930, x~330
```

The shadow lands exactly at the contact point. Visual evidence:
`12_qa/review-packages/ISSUE001-P16-02/evidence_contact_shadow.jpg`.

---

## 4. Character results

| Character | Method | Result | Notes |
|---|---|---|---|
| **NeonBlue** | Approved true-alpha layer, composited | **Identity: PASS** | 17 layers available. Only front-facing turnarounds — no true profile |
| **Moodz** | Approved true-alpha layer, composited | **Identity: PASS** | 18 layers. **Must never be mirrored** — now enforced |
| Lil Devil | — | **Not testable** | Zero alpha layers exist |

### Known failure modes discovered

| Failure | Cause | Mitigation |
|---|---|---|
| Mirrored asymmetric feature | Compositor `flip` | `NO_FLIP` guard, refuses and warns |
| Seated pose placed as standing | Pose slug not checked | `NON_STANDING_POSES` guard, warns |
| Desaturation | Relight too strong | Key strength ≤ 0.25 for cel-shaded art |
| Eye lines fixed forward | Source layers are front-facing turnarounds | **Unsolved.** Limits two-character conversations |

---

## 5. Panel results

| Panel type | Attempts | Passed | Status |
|---|---:|---:|---|
| Two-character conversation | 2 | 1 | Validated once |
| Close-up | 1 | 1 | Derived by crop, not independently generated |
| Wide environmental | 3 | 2 | Plate only, no characters staged |
| Single-character full body | 0 | 0 | **Not attempted** |
| Seated / furniture interaction | 0 | 0 | **Not attempted** |
| Prop interaction | 0 | 0 | **Not attempted** |
| Action / movement | 0 | 0 | **Not attempted** |
| Foreground occlusion | 0 | 0 | **Not attempted** |
| Nonstandard aspect | 0 | 0 | **Not attempted** |
| Emotionally important panel | 0 | 0 | **Not attempted** |

**1 of 10 panel types validated. The brief requires 10, three times each.**

---

## 6. What is built and saved

| Component | Path |
|---|---|
| ComfyUI job client with metadata capture | `app/adapters/comfy_client.py` |
| Workflow builders (plate, depth-guided, inpaint) | `app/services/workflows.py` |
| Deterministic compositor | `app/services/compositor.py` |
| Plate calibration tool | `scripts/production/calibrate_plate.py` |
| API payload templates + digests | `workflows/comfyui/api_payloads/` |
| Style contract, versioned | `workflows/comfyui/templates/STYLE_CONTRACT.json` |
| Forensic evidence summary | `workflows/comfyui/discovery/` |
| Every experiment: graph, manifest, output | `workflows/comfyui/experiments/exp001…exp005` |
| Review package | `issues/…/12_qa/review-packages/ISSUE001-P16-02/` |
| Final composite | `issues/…/09_composites/ISSUE001-P16-02_composite_v1.png` |

Every generation carries a job manifest with prompt, negative, seed, model,
sampler, steps, cfg, dimensions and output SHA-256. The panel is re-runnable
from saved configuration with no reliance on ComfyUI browser state.

---

## 7. Tests

```
python -m pytest -q
74 passed
```

New: `tests/production_validation/test_comfyui_pipeline.py`, 18 tests.

| Protects | How |
|---|---|
| Style contract weighting | Asserts the weighted terms and the suffix survive |
| Photorealism suppression | Asserts negative weights |
| Correct checkpoint | Asserts `RealVisXL_V4.0`, not the one that failed |
| Frameless/textless plates | Asserts the negative excludes characters, text, borders |
| ControlNet path really uses ControlNet | The previous system had zero such nodes |
| Canon: no mirroring | Asserts the guard fires and `flip` is forced false |
| Staging: seated-as-standing | Asserts the guard warns |
| Ground-plane scale falloff | Asserts depth reduces rendered height |
| Live environment | Skips cleanly when ComfyUI is down |

---

## 8. Limitations

1. **Seven of ten panel types untested.**
2. **No panel type has three successful runs.**
3. **Repair workflow built but never executed** — `inpaint_repair` is untested
   against a real defect.
4. **Depth-guided plate workflow built but never executed** —
   `background_from_reference` needs `depth_anything_v2_vitl.pth`, presence
   unverified.
5. **Eye lines cannot be directed.** Source layers are front-facing
   turnarounds. Two characters "looking at each other" is not currently
   achievable from the layer library.
6. **Lil Devil is unproducible** — no alpha layers.
7. **The plate used is a test plate, not an approved location plate.** It does
   not match the approved `festival-service-corridor` reference.
8. **The GPU is shared.** `signal-notes/hero` jobs interleaved with ours
   throughout; timings are contended and one run timed out at 10 minutes.
9. **Calibration is by eye.** Horizon and reference height were read off the
   plate, not measured.
10. **No panel is approved.** The composite is `candidate`.

---

## 9. Next actions, in order

1. Run the remaining seven panel types, three runs each.
2. Execute the repair workflow against a deliberately introduced defect.
3. Verify `depth_anything_v2_vitl.pth` and run the depth-guided plate path.
4. Produce Lil Devil alpha layers via RemBG.
5. Solve eye-line direction — likely ControlNet openpose over approved art.
6. Calibrate the four approved festival plates.
7. Only then create `workflows/comfyui/locked/panel-production-v1/`.

---

## 10. Git

| Item | Value |
|---|---|
| Files changed | See commit |
| Commit | Recorded below on push |
| Push | To `origin/main` |
| Working tree | Clean at commit |

**No lock commit was created**, per the brief's instruction not to lock until
validation passes. It has not.
