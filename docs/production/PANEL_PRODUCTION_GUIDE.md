# Panel Production Guide

**How to produce one panel with the pipeline as it exists today.**

Written 2026-07-28 from the code and the artefacts in this repository. Every
number below is either read out of a file in the repo or derived with the
arithmetic shown. Where something is unverified it says so.

Evidence base: `docs/audits/PANEL_PRODUCTION_LOOP_REPORT.md` (experiments
exp001–exp005) and `docs/audits/COMFYUI_PREVIOUS_WORKFLOW_FORENSICS.md` (why the
previous process produced off-model art).

---

## Status of the thing you are about to use

| Question | Answer |
|---|---|
| Does it work end to end? | Yes, for one panel type: two characters standing in a corridor |
| How many panel types are validated? | **1 of 10**. Seven were never attempted |
| How many runs per type? | 1. The brief requires 3 |
| Is any panel approved? | **No.** `ISSUE001-P16-02` is a `candidate` |
| Does it generate characters? | **No.** It composites approved alpha layers. Nothing else |
| Is it locked? | No. `workflows/comfyui/locked/` does not exist |

Read that table before you promise anyone a page.

---

## 0. Before you start

### Check the machine

```bash
python -m app.cli.main comfy
```

Read-only probe (`app/adapters/comfyui.py`). It never queues a job.

Verified state on this host, 2026-07-28 (`docs/workflows/COMFYUI_CAPABILITY_AUDIT.md`,
re-checked against `/object_info` while writing this guide):

| Item | Value |
|---|---|
| ComfyUI | 0.19.3 at `http://127.0.0.1:8188`, 1158 node types |
| GPU | AMD Radeon RX 6800 via ZLUDA, 17.2 GB VRAM, 137.4 GB system RAM |
| Checkpoints | `RealVisXL_V4.0.safetensors`, `animagine-xl-4.0.safetensors` |
| VAEs | `sdxl_vae`, `z_image_ae`, `taesd`, `taesdxl`, `taesd3`, `taef1`, `pixel_space` |
| ControlNet | `controlnet-union-sdxl-1.0-promax.safetensors` |
| IP-Adapter | `ip-adapter-plus_sdxl_vit-h.safetensors`, `CLIP-ViT-H-14-laion2B-s32B-b79K` |
| LoRAs | **none** |
| Upscale models | **none** |
| Launch flags | `--use-split-cross-attention --disable-cuda-malloc --disable-smart-memory` |
| Directories | input `I:\ai\nft\input`, output `I:\ai\nft\output`, temp `I:\ai\cache\temp` |

### The instance is shared

An unrelated `signal-notes/hero` project generates on the same GPU. 286 of the
337 jobs in `/history` belong to it. Consequences you will actually feel:

| Measurement | Uncontended | Contended |
|---|---:|---:|
| 960×1024, 32 steps | 117 s | 398 s |
| 1344×768, 30 steps | 113 s | 91 s |

Set `ComfyClient(timeout=1800)` for plate jobs. The default is 900 s and one run
during the experiment loop timed out at 10 minutes.

### Check the guards still hold

```bash
python -m pytest -q
```

76 passed, 5.1 s, on 2026-07-28. The style-contract and canon-guard tests in
`tests/production_validation/test_comfyui_pipeline.py` are the ones that matter —
they encode the exp001/exp003/exp004 findings. If they fail, stop.

---

## 1. Read the panel spec

Two files. Neither is hand-authored; both are generated and will be overwritten.

| File | Gives you |
|---|---|
| `issues/<issue>/03_script/panel-script.yaml` | What the panel must show |
| `issues/<issue>/05_layouts/layout-spec.yaml` | How big it is, in fractions |

### From panel-script.yaml

The fields the pipeline actually consumes, using `ISSUE001-P16-02` as the
worked example throughout this guide:

| Field | Value for P16-02 | Used for |
|---|---|---|
| `location` | `LOC-festival-service-corridor` | Which plate |
| `background_description` | "Service corridor running away from camera. Pipework along one wall, a red practical overhead midway, floor grating underfoot." | The plate prompt |
| `depth_plan` | NeonBlue nearer, Moodz further | `depth_plane` per character |
| `lighting.key_direction` | "Overhead red practical, between and slightly behind them" | `LightContract.key_angle_deg` |
| `lighting.key_color` | "Deep red-orange" | `LightContract.key_color` |
| `lighting.fill` | "Faint cyan bounce from the corridor's far end" | `LightContract.fill_color` |
| `character_blocking[].position` | "Frame left, side-on…" / "Frame right, a clear step further…" | `Placement.centre_x` |
| `character_blocking[].ground_contact` | "Both feet flat on the corridor floor" | `Placement.foot_y`, `contact_offset` |
| `character_blocking[].scale_note` | "8 percent smaller than NeonBlue" | `Placement.scale_multiplier` |
| `character_blocking[].expression_id` | `EXP-005-sad`, `EXP-001-neutral` | Which layer file |
| `qa_checklist` | 9 items | The review package |

Everything in `lighting` is prose. **You convert it to numbers by hand.** No
code does this. That conversion is the single biggest source of judgement in the
whole pipeline and nothing records it except the calibration YAML you write in
step 3.

### From layout-spec.yaml: the panel's pixel size

`box` is `[x, y, w, h]` as fractions of the **live area** — inside the margins,
not the trim. `scripts/production/build_layout_spec.py` records the live area as
**2149 × 3177 px** (A4 at 300 dpi, minus a 14 mm live margin each side) in the
comment above its `LIVE_ASPECT` constant, and the spec's own header says
"Coordinates are fractions of the LIVE AREA (inside the margins)".

```
panel_px = round(box_w * 2149), round(box_h * 3177)
```

For `ISSUE001-P16-02`, `box = [0.0, 0.2416, 0.7136, 0.5167]`:

```
width  = 0.7136 * 2149 = 1533.5  -> 1534
height = 0.5167 * 3177 = 1641.6  -> 1642
```

which is the size of `09_composites/ISSUE001-P16-02_composite_v1.png`. Confirmed
by opening the file.

**No script performs this conversion.** Do it yourself and write the result into
the plate job.

---

## 2. Generate the background plate

### Which builder

`app/services/workflows.py` exposes three, registered in `BUILDERS`:

| Builder | Class | State |
|---|---|---|
| `background_plate` | A — place, no characters | **Working.** exp001–exp003, exp006 |
| `background_from_reference` | A with depth control | Built, **never executed** |
| `inpaint_repair` | D — masked local repair | Built, **never executed** |

Use `background_plate`. The other two are covered in section 10.

### Parameters

Signature defaults from `workflows.py`:

| Parameter | Default | What exp003 used | Note |
|---|---|---|---|
| `prompt` | — | the scene text below | Style contract is added for you |
| `negative_extra` | `""` | `"lockers, cabinets, doors along walls, clutter"` | Appended to `STYLE_NEGATIVE` |
| `width` / `height` | — | 960 / 1024 | Must be an SDXL-friendly bucket |
| `seed` | — | 760201, 760202 | Always explicit |
| `steps` | 30 | 32 | |
| `cfg` | 6.0 | 6.0 | |
| `sampler` / `scheduler` | `dpmpp_2m` / `karras` | same | |
| `checkpoint` | `RealVisXL_V4.0.safetensors` | same | |
| `filename_prefix` | `bananalab/bg` | `bananalab/exp003_<seed>` | ComfyUI-side name |

### Why RealVisXL and not animagine

EXP-001 held scene, size, seed, steps and cfg fixed and varied only the
checkpoint:

| Checkpoint | Result |
|---|---|
| `RealVisXL_V4.0` | Coherent. Correct one-point perspective, readable grating floor, red overhead practical, flat cel-shaded look with dark outlines |
| `animagine-xl-4.0` | Failed. Over-saturated primaries, incoherent wall detail reading as abstract blocks, wrong light colour |

The hypothesis going in was that the written style contract would carry the look
and the checkpoint was secondary. It was rejected. The legacy Issue 001 run used
`animagine-xl-4.0` for all 49 of its jobs.

`test_default_checkpoint_is_the_one_that_won` asserts this. Do not change it
without a new experiment.

### Plate size: pick the panel's aspect, not a convenient one

exp002/exp003 generated 960×1024 for a panel that is 1534×1642. That was a
deliberate test-plate shortcut and it costs you twice:

- **1.60× upscale** at composite time (1534/960 = 1.598, 1642/1024 = 1.604),
  through `Image.LANCZOS`, with **no upscale model installed**.
- **0.35 % differential stretch**, because 960/1024 = 0.9375 but
  1534/1642 = 0.9342.

For a real plate, match the panel aspect and round to a multiple of 8. For
P16-02 the closest fit near one megapixel is **1024 × 1096** (1024/1096 = 0.93431
against the panel's 0.93423, a 0.008 % error). *This size has not been run —
it is arithmetic, not evidence.*

### Running it

There is no CLI verb for generation. The pattern is the one in
`workflows/comfyui/experiments/_run_exp003.py`:

```python
from pathlib import Path
from app.adapters.comfy_client import ComfyClient, archive_graph, write_job_manifest
from app.services import workflows as wf

OUT = Path("issues/issue-001-neonblue-the-last-light-of-summer/06_backgrounds/generated_candidates")

scene = ("narrow industrial service corridor at night in deep one-point perspective, "
         "pipework along the left wall, metal floor grating receding to a vanishing point, "
         "one red strip light on the ceiling midway down, "
         "cyan glow from a distant doorway at the far end, "
         "empty corridor, clear open floor in the foreground")

client = ComfyClient(timeout=1800)
graph = wf.background_plate(
    prompt=scene,
    negative_extra="lockers, cabinets, doors along walls, clutter",
    width=960, height=1024, seed=760201, steps=32, cfg=6.0,
    filename_prefix="bananalab/issue001_p16_02",
)
result = client.run(graph, OUT, "ISSUE001-P16-02_plate_seed760201")

archive_graph(graph, OUT / "ISSUE001-P16-02_plate_seed760201_graph.json")
write_job_manifest(
    OUT / "ISSUE001-P16-02_plate_seed760201_manifest.json",
    job_id="ISSUE001-P16-02-plate-760201",
    job_class="A",
    workflow_version=wf.WORKFLOW_VERSION,
    graph=graph, result=result,
    extra={"panel_id": "ISSUE001-P16-02"},
)
```

`ComfyClient.run` submits, polls `/history/<prompt_id>` every 2 s, and downloads
every `type: output` image into `dest_dir` with deterministic names. It returns
a `JobResult` carrying `ok`, `error`, `seconds`, `images` and the graph.

Write the scene prompt describing **the place only**. `STYLE_NEGATIVE` already
excludes `characters, people, person, figure, animal, monkey, creature, mascot`
and every form of text and panel border. A plate with a character in it is a
defect (`PANEL-FRAME-BAKED` / off-brief), not a head start.

### Determinism: do not expect the same bytes twice

EXP-006 re-ran the exp003 graph with the identical seed and graph on this host:

```
prior  8913bc12de225e94ead…
rerun  06e7e65fde43c8fb8032…
deterministic: False
```

Recorded in `workflows/comfyui/experiments/exp006-determinism/exp006_manifest.json`.
Consequences:

- Golden-image regression testing is **not usable** on this environment.
- "Re-runnable from saved configuration" means *the same recipe*, not the same
  pixels. If you need a specific plate, keep the PNG.

*Note: the loop report describes five experiments. exp006 exists in the repo and
is not in that report. See section 12.*

---

## 3. Calibrate the plate

A plate is not usable until you know where the floor is. Without that, character
scale is guesswork — which is how the previous system produced a row of
equally-sized cut-outs.

### The four numbers

`scripts/production/calibrate_plate.py` writes a YAML sidecar next to the plate:

| Key | Meaning |
|---|---|
| `horizon_y` | Screen y of the horizon / vanishing point |
| `calib_foot_y` | Screen y where your reference object meets the floor |
| `calib_height_px` | That object's screen height, in pixels |
| `calib_height_in_characters` | How tall it is, measured in character heights |

`calib_x` (optional) only positions the preview overlay. `calib_object` and
`ground_surface` are free text for the next reader.

### What they buy you

`GroundPlane.character_height_at` in `app/services/compositor.py`:

```
unit          = calib_height_px / calib_height_in_characters
calib_drop    = calib_foot_y - horizon_y
height(foot_y) = unit * (foot_y - horizon_y) / calib_drop
```

A flat plane under a pinhole camera: apparent height scales linearly with
distance below the horizon. Feet at or above the horizon raise `ValueError` —
the compositor catches it, logs a warning and **skips that character**, so a bad
`foot_y` produces a silently missing figure. Check the placement report.

### The command that works

```bash
cd <directory containing the plate>
python R:/BananaLab2.0/scripts/production/calibrate_plate.py testplate.png \
    --horizon 430 --calib-foot 1000 --calib-height 460 --calib-characters 1.0 \
    --calib-x 480 \
    --calib-object "notional standing character at the near floor edge" \
    --ground-surface "metal floor grating, hard reflective" \
    --key-angle 90 --key-color "#C8503A" --fill-color "#1E4A55" \
    --note "ISSUE001-P16-02 method gate" --show
```

Output:

```
wrote testplate.calibration.yaml
wrote testplate_calib_preview.jpg
  one character at the calibration depth = 460px tall
```

`--key-angle` is degrees: **0 = from frame right, 90 = from directly above,
180 = from frame left.** `--key-color` and `--fill-color` are hex and are
converted to RGB triples in the YAML.

> **Known bug.** If you pass an absolute path that is not inside the repository,
> line 109 raises an unhandled `ValueError: … is not in the subpath of
> 'R:\BananaLab2.0'`. Since ComfyUI writes to `I:\ai\nft\output`, this bites
> immediately. Work around it by `cd`-ing to the plate's directory and passing a
> relative filename, as above.

### Reading the scale-ladder preview

`--show` writes `<plate>_calib_preview.jpg`. `preview()` draws:

| Overlay | Colour | Means |
|---|---|---|
| Horizontal line, labelled `horizon y=` | Yellow | Where you said the horizon is |
| Rectangle with `ref Npx = M char` | Green | Your calibration object |
| Five rectangles with an ellipse at the base and a pixel label | Pink | A character standing at five depths |

The ladder is the sanity check. Look at it and ask one question: **would a person
standing there be that size?** If the near figures are giants or the far figures
are ants, the horizon is wrong. Fix `horizon_y` first — it dominates.

### Worked values for the test plate

`workflows/comfyui/experiments/exp003-weighted-style/exp003_seed760201.calibration.yaml`,
for a 960×1024 plate:

```yaml
ground_plane:
  horizon_y: 430.0
  calib_foot_y: 1000.0
  calib_height_px: 460.0
  calib_height_in_characters: 1.0
  calib_x: 480
  calib_object: notional standing character at the near floor edge
  ground_surface: metal floor grating, hard reflective
light:
  key_angle_deg: 90.0
  key_color: [200, 80, 58]
  fill_color: [30, 74, 85]
```

The file carries its own honesty note, and the tool writes it automatically:

> Ground-plane values are art-directed estimates read off the plate by eye and
> checked against the scale-ladder preview. They are not camera calibration.
> Treat as a production convention, not a measurement.

Leave that note in. It is true.

---

## 4. Choose the character layers

There is **no character generation stage.** This pipeline composites
pre-existing true-alpha layers. If a layer does not exist, the panel cannot be
made.

### The library

`source_material/imported_canon/character_layers/` — read-only by policy;
`app/core/paths.assert_safe_write_target()` raises `PermissionError` for any
caller that routes through it. 139 PNGs, all RGBA:

| Directory | Layers | Character ID |
|---|---:|---|
| `ash/` | 18 | MZ-CHAR-004 |
| `clever/` | 30 | — |
| `moodz/` | 18 | MZ-CHAR-001 |
| `neonblue/` | 17 | MZ-CHAR-005 |
| `scarline/` | 17 | MZ-CHAR-006 |
| `static/` | 19 | MZ-CHAR-003 |
| `twotone/` | 19 | MZ-CHAR-002 |
| `zombie/` | 1 | — |

`layer_menu.json` in the same directory maps each file to a pose slug. **Lil
Devil has no layers at all** and appears in 17 panels of Issue 001. Those panels
are unproducible today.

### The pose slug is load-bearing

`compositor.pose_slug()` takes everything after the second underscore:
`neonblue_27_defeated.png` → `defeated`. That string is what the staging guard
checks, so filenames are part of the contract. Slugs present in the library:

`angry armscrossed backview celebrating clean_base confused crouching defeated
determined disgusted freeze jumping laughing lookingup neutral overshoulder
pointing profile reaching running sad shocked shout sitting sleepy smile
thinking threeqtr walking waving worried`

### Guard 1 — NO_FLIP (refusal)

Mirroring a character whose identity depends on a left/right asymmetry moves a
canon feature to the wrong side. That is `IDENT-CANON-VIOLATION`, not a staging
choice. From `compositor.NO_FLIP`:

| Character | Asymmetry |
|---|---|
| `MZ-CHAR-001` Moodz | Black fringe over one eye, blue accent on the left |
| `MZ-CHAR-004` Ash | Stitched chest detail |
| `MZ-CHAR-005` NeonBlue | Left-ear silver plug earring |
| `MZ-CHAR-006` Scarline | Scarlet streak on the viewer-left side |

Set `flip=True` on one of these and the compositor **forces it back to False**,
appends a `CANON:` warning and carries on. This guard was added after exp004
mirrored Moodz and moved his blue accent to the wrong eye.

### Guard 2 — NON_STANDING_POSES (warning only)

Poses whose contact point is not the soles of the feet:

| Slug | Real contact point |
|---|---|
| `sitting` | Hips |
| `defeated` | Hips — slumped/seated |
| `crouching` | Feet plus one hand |
| `jumping` | None — airborne |
| `running` | One foot, mid-stride |

If the slug is in this set and `contact_offset == 0.0`, you get a `STAGING:`
warning. **It does not stop.** exp004 placed a seated NeonBlue as if standing
(`STAGE-POSE-MISMATCH`) and this guard exists to make that visible, not to
prevent it. Read the warnings.

Note `walking` is *not* guarded even though it is a one-foot contact.

### The expression trap

Check `07_character_staging/expression-coverage.csv` before you pick a layer.
For P16-02 the script asks for:

| Character | Script wants | Approved layer exists? | What exp005 actually used |
|---|---|---|---|
| MZ-CHAR-005 NeonBlue | `EXP-005-sad` | **no** — `GENERATE CANDIDATE` | `neonblue_16_worried.png` |
| MZ-CHAR-001 Moodz | `EXP-001-neutral` | **no** — `GENERATE CANDIDATE` | `moodz_00_clean_base.png` |

Only `clever/` has `sad` and `neutral` layers. NeonBlue has neither. The
validated panel therefore ships with **substituted expressions**, which is a
live `STAGE-EXPRESSION-MISMATCH` risk that no guard catches and that the review
package does not mention. If you substitute, record it in the manifest `extra`.

### Other known limits of the library

| Limit | Consequence |
|---|---|
| Layers are front-facing turnarounds | **Eye lines cannot be directed.** Two characters "looking at each other" is not achievable. Unsolved |
| No true profile for NeonBlue | Side-on blocking is approximated |
| Lil Devil: zero layers | 17 panels blocked |

---

## 5. Composite

`app/services/compositor.py`. No diffusion — everything here is deterministic
PIL and NumPy, which means a defect can be diagnosed rather than re-rolled.

### The three inputs

**`GroundPlane`** — the four calibration numbers, straight from the YAML.

**`LightContract`** — the plate's lighting as numbers:

| Field | Default | Notes |
|---|---|---|
| `key_angle_deg` | — | 0 = frame right, 90 = overhead, 180 = frame left |
| `key_color` | — | RGB tuple |
| `key_strength` | 0.55 | **Use ≤ 0.25 for cel-shaded art.** 0.55 desaturated both characters in exp004 (`INTEG-LIGHT-COLOR`) |
| `fill_color` | `(40, 46, 60)` | |
| `fill_strength` | 0.18 | exp005 used 0.10 |
| `rim_strength` | 0.0 | |
| `cast_length` | 0.6 | Multiple of character height |
| `cast_opacity` | 0.42 | |
| `contact_opacity` | 0.72 | |
| `spill_strength` | 0.20 | Colour sampled from the plate, 90 px radius around the figure's midpoint |
| `ambient_lift` | 0.0 | |

**`Placement`** — one per character:

| Field | Notes |
|---|---|
| `character_id` | Must be the `MZ-CHAR-###` id — that is what `NO_FLIP` keys on |
| `layer_path` | Path into the layer library. The filename supplies the pose slug |
| `centre_x` | Screen x of the centre line |
| `foot_y` | Screen y where feet meet the ground |
| `depth_plane` | `foreground` / `midground` / `background`. Controls draw order, blur (0/0/1.1) and haze (0/0.06/0.18) |
| `scale_multiplier` | Multiplies the ground-plane height. 1.0 = standing adult |
| `flip` | Refused for `NO_FLIP` characters |
| `contact_offset` | Move the contact point for non-standing poses |
| `occluder` | Full-canvas RGBA drawn over this character |

### Worked example — exp005

This reproduces the placement geometry of `ISSUE001-P16-02` exactly. Verified by
running it and diffing against
`workflows/comfyui/experiments/exp005-composite-v2/exp005_report.json`.

```python
from pathlib import Path
from app.services.compositor import (
    GroundPlane, LightContract, Placement, composite_panel,
)

REPO   = Path("R:/BananaLab2.0")
PLATE  = REPO / "workflows/comfyui/experiments/exp003-weighted-style/exp003_seed760201.png"
LAYERS = REPO / "source_material/imported_canon/character_layers"

# Straight from exp003_seed760201.calibration.yaml
ground = GroundPlane(
    horizon_y=430.0,
    calib_foot_y=1000.0,
    calib_height_px=460.0,
    calib_height_in_characters=1.0,
)

# key/fill from the calibration; strengths reduced per the exp005 finding.
light = LightContract(
    key_angle_deg=90.0,          # overhead practical
    key_color=(200, 80, 58),
    key_strength=0.22,           # 0.55 default desaturated the cast in exp004
    fill_color=(30, 74, 85),     # the corridor's cyan bounce
    fill_strength=0.10,
)

placements = [
    Placement(
        character_id="MZ-CHAR-005",                       # NeonBlue
        layer_path=LAYERS / "neonblue/neonblue_16_worried.png",
        centre_x=330, foot_y=930,
        depth_plane="midground", scale_multiplier=0.78,
    ),
    Placement(
        character_id="MZ-CHAR-001",                       # Moodz
        layer_path=LAYERS / "moodz/moodz_00_clean_base.png",
        centre_x=660, foot_y=820,
        depth_plane="midground", scale_multiplier=0.78,
    ),
]

panel, report = composite_panel(
    PLATE, ground, light, placements,
    output_size=(1534, 1642),        # the layout spec's size for this panel
)

for warning in report.warnings:
    print("WARNING:", warning)
panel.save("ISSUE001-P16-02_composite_v1.png")
```

### Check the arithmetic before you look at the picture

```
character_height_at(930) = 460 * (930 - 430) / (1000 - 430) = 403.5
  x scale_multiplier 0.78                                   = 314.7  -> 314 px rendered
character_height_at(820) = 460 * (820 - 430) / (1000 - 430) = 314.7
  x scale_multiplier 0.78                                   = 245.5  -> 245 px rendered

top_left(NeonBlue) = (330 - 209//2, 930 - 314) = (226, 616)
top_left(Moodz)    = (660 - 195//2, 820 - 245) = (563, 575)
```

Those four numbers appear verbatim in `exp005_report.json`. If yours differ, the
ground plane or the multiplier is wrong, not the art.

**One check the loop report did not make:** the script's `scale_note` for Moodz
says "8 percent smaller than NeonBlue". 245 / 314 = 0.780, so he renders **22 %
smaller**. Either the blocking or the `foot_y` needs revisiting. This is an open
`INTEG-SCALE` question against `ISSUE001-P16-02`.

### What the compositor does, in order

1. Sort placements back to front by `depth_plane`.
2. Apply the `NO_FLIP` and `NON_STANDING_POSES` guards.
3. `trim_alpha` — crop to visible pixels so the height maths is about the
   character, not the transparent padding.
4. `erode_alpha(1)` — pull the matte in one pixel. Kills the background-removal
   fringe (`INTEG-MATTE-HALO`), which the previous project's own notes record as
   recurring.
5. Resize to the ground-plane height, flip if permitted, apply depth blur.
6. Sample the plate around the figure for the spill colour, then `relight`.
7. Apply depth haze.
8. Draw contact shadow (ellipse, 82 % of layer width, 5.5 % of height, blurred)
   and cast shadow (sheared silhouette leaning away from the key) into a single
   shadow layer.
9. Burn the whole shadow layer into the plate **before** any character lands.
10. Composite characters front to back; apply occluders.
11. Resize to `output_size` if given.

Step 11 is a plain LANCZOS resize. With a 960×1024 plate and a 1534×1642 panel
that is a 1.6× upscale and there is no upscale model on this host. Generate the
plate at panel aspect (section 2) rather than relying on it.

### Read the warnings

`CompositeReport.warnings` is the only channel the guards have. It is a list of
strings, not exceptions:

| Prefix | Meaning |
|---|---|
| `CANON:` | A flip was refused. The panel is fine; your staging spec is wrong |
| `STAGING:` | Non-standing pose with `contact_offset = 0`. The figure will float or sink |
| `<character_id>: feet must sit below the horizon` | **The character was skipped entirely** |

Save `report.placements` and `report.warnings` next to the panel.

---

## 6. Produce the review package

`issues/<issue>/12_qa/review-packages/<panel_id>/`. **No script builds this.**
The P16-02 package was assembled by hand. What it contains:

| File | Size | Purpose |
|---|---|---|
| `placement_report.json` | — | `report.placements` + `report.warnings` |
| `composition_grayscale.png` | 960×1024 | Value structure without colour distraction |
| `crop_face_neonblue.png` | 420×315 | Identity check against approved reference |
| `crop_face_moodz.png` | 420×263 | Identity check |
| `crop_contact_neonblue.png` | 420×180 | Feet, contact shadow, ground plane |
| `crop_contact_moodz.png` | 420×180 | Feet, contact shadow, ground plane |
| `closeup_neonblue_from_panel.png` | 900×571 | Derived close-up, cropped not regenerated |
| `evidence_contact_shadow.jpg` | 1140×346 | Before / after / difference for the shadow |
| `readability_final_size.png` | 429×459 | Panel at reading size |

*The 429×459 readability size is not derived anywhere in the repo. If you
reproduce this package, record where that number came from.*

### Verify shadows numerically, not by eye

Contact shadows against a near-black corridor floor are invisible in a
screenshot. Diff the composite against the bare plate and report the numbers.
For exp005:

```
pixels changed by shadow: 13252
bbox x[226-434] y[864-994]   max delta 146.3
expected contact region around y=930, x~330
```

The bbox brackets the expected contact point, so the shadow lands where the feet
do. That is evidence. "It looks right" is not.

### Then review against the standard

Work `docs/quality/QUALITY_STANDARD.md` with the artwork at final print size.
Record every defect in `12_qa/defects.csv` with a code from
`docs/quality/DEFECT_TAXONOMY.md`. The single question that decides the panel:

> Does the character look like they are **in** the scene, or **in front of** it?

`python -m app.cli.main validate` runs the mechanical subset. **None of its
checks look at a picture.** A machine gate may only reject; it may never approve.

---

## 7. Record the job manifest

Every generated image needs one. An image with no manifest cannot be promoted.

```python
from app.adapters.comfy_client import write_job_manifest
```

Fields written automatically: `job_id`, `job_class`, `workflow_version`,
`prompt_id`, `ok`, `error`, `seconds`, `outputs` (path + SHA-256 + byte size),
the full `graph`, and `review_status: "candidate"` with empty `reviewed_by` and
`review_note`.

`extra` is where the human context goes. Use it for `panel_id`, `hypothesis`,
`variable`, `compare_against`, and any layer substitution you made in step 4.

For a composite there is no ComfyUI graph. Record the equivalent by hand:
plate path and hash, calibration YAML path, every `Placement`, the
`LightContract`, `report.warnings`, and the output hash.

### The line you do not cross

`write_job_manifest` sets `review_status: "candidate"`. Only a human moves it on,
and only by writing `issues/<issue>/13_approved/approval-record.yaml` by hand. No
script in this repository writes that file (ADR-005,
`docs/quality/APPROVAL_WORKFLOW.md`). `ISSUE001-P16-02` is a candidate and stays
one until an owner says otherwise.

---

## 8. The style contract, and why it looks like that

Defined once in `app/services/workflows.py`, mirrored for inspection in
`workflows/comfyui/templates/STYLE_CONTRACT.json`. Every builder prepends
`STYLE_POSITIVE`, appends `STYLE_SUFFIX` and uses `STYLE_NEGATIVE`, so no caller
can omit it:

```python
positive = f"{STYLE_POSITIVE}. {prompt}. {STYLE_SUFFIX}"
negative = STYLE_NEGATIVE + (f", {negative_extra}" if negative_extra else "")
```

```
STYLE_POSITIVE
  (flat 2d vector cartoon illustration:1.5), (thick uniform black outlines:1.4),
  (flat colour fills with hard cel shading:1.4), comic book background art,
  graphic novel panel, bold saturated palette, clear perspective

STYLE_SUFFIX
  (flat cartoon vector art:1.4), (bold black outlines:1.3), (cel shaded:1.3),
  non-photorealistic

STYLE_NEGATIVE
  (photorealistic:1.6), (photograph:1.6), (realistic lighting:1.4),
  (3d render:1.4), (volumetric light:1.3), (depth of field:1.3), … plus
  characters/people/animal, all text and lettering, panel borders and frames,
  and the usual artefact terms.
```

### Why the weights and the repeat exist

They are not decoration. EXP-002 and EXP-003 differ in **the style contract
only** — same seed, same scene, same size, same steps, same cfg:

| | EXP-002 | EXP-003 |
|---|---|---|
| Style contract | Unweighted, prepended only | Weighted terms + restated suffix |
| Seeds | 760201, 760202 | 760201, 760202 |
| Scene / size / steps / cfg | corridor / 960×1024 / 32 / 6.0 | identical |
| Result | **Photorealistic.** Wet reflective floors, volumetric neon, depth of field — despite `photorealistic` already being in the negative | **Correct house style.** Flat cartoon, thick black linework, hard cel shading, legible grid floor to a vanishing point |

Root cause: the contract was **positionally weak**. A long scene description
carrying photographic language ("moody, high contrast, cool cyan light
spilling") pushed the style tokens out of effect. Weighting the three
load-bearing terms and restating them *after* the scene fixed it. Confirmed
across both seeds.

This is the single most important finding of the run. Two tests protect it:

| Test | Asserts |
|---|---|
| `test_style_contract_weights_the_load_bearing_terms` | `(flat 2d vector cartoon illustration:1.5)` and `(thick uniform black outlines:1.4)` survive |
| `test_style_is_restated_after_the_scene` | With a 400-character prompt, the positive still *starts* with `STYLE_POSITIVE` and *ends* with `STYLE_SUFFIX` |

**Practical rule:** put the place in `prompt` and keep photographic vocabulary
out of it. Do not describe lighting the way a cinematographer would. If you need
to exclude scene furniture, use `negative_extra` — exp003 used
`"lockers, cabinets, doors along walls, clutter"`.

---

## 9. Troubleshooting

Keyed on defects actually observed in this repository. Codes are from
`docs/quality/DEFECT_TAXONOMY.md`.

| Symptom | Code | Cause | Fix |
|---|---|---|---|
| Plate comes back photoreal — wet floors, bokeh, volumetric light | `PANEL-ARTIFACT` / off-style | Style contract diluted by a long or photographic scene prompt (exp002) | Confirm the positive starts with `STYLE_POSITIVE` and ends with `STYLE_SUFFIX`. Strip cinematographic language from `prompt` |
| Plate is over-saturated, walls read as abstract blocks | off-style | `animagine-xl-4.0` (exp001) | Use `RealVisXL_V4.0`. `test_default_checkpoint_is_the_one_that_won` should have caught this |
| Character's identity mark is on the wrong side | `IDENT-CANON-VIOLATION` | `flip=True` on a `NO_FLIP` character (exp004, Moodz) | The guard now refuses. If it slipped through, the id in `Placement` was wrong — `NO_FLIP` keys on `character_id` |
| Character sinks into or floats above the floor | `INTEG-NO-GROUND-CONTACT` | Non-standing pose with `contact_offset = 0` (exp004, seated NeonBlue) | Read the `STAGING:` warning. Set `contact_offset`, or use a standing layer |
| Characters look washed out and grey against the plate | `INTEG-LIGHT-COLOR` | `key_strength` at the 0.55 default (exp004) | Drop to ≤ 0.25. exp005 used key 0.22, fill 0.10 |
| Characters too big for the space | `INTEG-SCALE` | `scale_multiplier` 1.0 with a horizon estimate that is too low | exp005 used 0.78. Re-check the scale ladder before touching the multiplier |
| Moodz renders 22 % smaller when the script says 8 % | `INTEG-SCALE` | `foot_y` gap larger than the blocking implies | Open against P16-02. Recompute `foot_y` from the intended 0.92 height ratio |
| Pale or dark fringe at a character's edge | `INTEG-MATTE-HALO` | Background-removal fringe | `erode_alpha(1)` runs by default. If it persists the source layer needs a cleaner matte |
| A character is simply absent from the output | — | `feet must sit below the horizon` — the character was skipped | Check `report.warnings`. `foot_y` is above `horizon_y` |
| Contact shadow invisible on a dark floor | `INTEG-NO-CONTACT-SHADOW` (suspected) | Usually not a real defect | Diff against the bare plate and report pixels changed + bbox before filing |
| Character expression does not match the beat | `STAGE-EXPRESSION-MISMATCH` | Scripted `expression_id` has no approved layer; a substitute was used | Check `expression-coverage.csv`. Record the substitution in the manifest |
| Two characters cannot be made to look at each other | `STAGE-EYELINE` | Source layers are front-facing turnarounds | **Unsolved.** Re-block the panel, or wait for openpose-guided rendering |
| Panel is soft at final size | `PANEL-READABILITY` | Plate generated smaller than the panel and upscaled | Generate at panel aspect and size. No upscale model is installed |
| Job never returns | — | Shared GPU. `signal-notes/hero` interleaves | `ComfyClient(timeout=1800)`. Expect 398 s where uncontended is 117 s |
| Same seed, different image | — | Generation is not deterministic here (exp006) | Keep the PNG. Do not build golden-image tests |
| `ValueError: … is not in the subpath of 'R:\BananaLab2.0'` | — | `calibrate_plate.py` with an absolute path outside the repo | `cd` to the plate directory, pass a relative filename |

---

## 10. What is NOT built

Be explicit about this with anyone who asks for a schedule.

| Capability | State | Detail |
|---|---|---|
| **Character generation** | **Does not exist** | The pipeline composites approved alpha layers. Nothing renders a character. Characters with no layers (Lil Devil, 17 panels) cannot be produced |
| **Repair / inpaint** | Built, **never executed** | `workflows.inpaint_repair` produces a valid graph and has a saved payload. It has never run against a real defect. `denoise=0.75`, `grow_mask_by=8` are untested defaults |
| **Depth-guided plate** | Built, **never executed** | `workflows.background_from_reference`. `DepthAnythingV2Preprocessor` is registered and offers `depth_anything_v2_vitl.pth` as its default — but the option list does not prove the weights are on disk, and the path has never been executed end to end |
| **Upscaling** | **Not possible** | Zero upscale models installed. `UpscaleModelLoader` has nothing to load. Final sizing is a LANCZOS resize |
| **LoRA style enforcement** | **Not possible** | Zero LoRAs installed. Style comes from the prompt contract only |
| **IP-Adapter identity** | Installed, **unused** | `ip-adapter-plus_sdxl_vit-h` and CLIP-ViT-H are present. No workflow builder uses them |
| **Eye-line direction** | **Unsolved** | Front-facing turnarounds only |
| **Review-package build** | **Manual** | No script. The P16-02 package was assembled by hand |
| **Layout box → pixels** | **Manual** | No script converts `box` fractions into a plate size |
| **Prose lighting → LightContract** | **Manual** | No mapping exists between `lighting.key_direction` text and `key_angle_deg` |
| **Panel-type coverage** | **1 of 10** | Single-character full body, seated/furniture, prop interaction, action, foreground occlusion, nonstandard aspect and emotionally-important panels were never attempted |
| **Locked workflow** | **Does not exist** | `workflows/comfyui/locked/panel-production-v1/` will not be created until validation passes |

### Also true, and inconvenient

- The plate used for the validated panel is a **test plate**
  (`workflows/comfyui/experiments/exp003-weighted-style/`). It does not match the
  approved `festival-service-corridor` reference and it does not live in
  `06_backgrounds/`.
- Consequently `python -m app.cli.main status` reports **Backgrounds: not
  started** and **Character Rendering: not started** while **Compositing:
  complete**. `stage_status()` checks each stage's own evidence and
  `IssueState.blockers()` only reports on the first incomplete stage, so nothing
  flags the inversion. Do not read "Compositing complete" as "the stages before
  it are done".
- Only 4 plate calibrations exist repo-wide
  (`source_material/imported_canon/plate_calibrations/`), none for a festival
  location, and they are a different format (`scene_blocking.json`) from what
  `calibrate_plate.py` writes.

---

## 11. Commands that exist and work today

```bash
python -m app.cli.main status [issue]     # production state, read from disk
python -m app.cli.main validate           # schemas, panel scripts, format, manifest, hygiene
python -m app.cli.main schemas            # list schemas
python -m app.cli.main comfy [--host]     # read-only ComfyUI probe
python -m app.cli.main dashboard [--out]  # static HTML dashboard
python -m pytest -q                       # 76 tests, ~5 s

# Regenerate the generated inputs after a source change
python scripts/production/build_panel_script.py <issue-slug>
python scripts/production/derive_script_views.py <issue-slug>
python scripts/production/build_layout_spec.py <issue-slug>
python scripts/production/render_layout_thumbnails.py <issue-slug>
python scripts/production/build_character_coverage.py <issue-slug>

# Calibrate a plate (run from the plate's own directory - see section 3)
python <repo>/scripts/production/calibrate_plate.py <plate.png> \
    --horizon Y --calib-foot Y --calib-height PX --calib-characters N --show
```

There is **no CLI verb that generates or composites**. Generation is a Python
script using `ComfyClient`; compositing is a Python script using
`composite_panel`. `workflows/comfyui/experiments/_run_exp003.py` and
`_run_exp006.py` are the working templates.

---

## 12. Known gaps in the existing records

Found while writing this guide. Recorded so the next person does not re-derive
them.

| Record | Problem |
|---|---|
| `PANEL_PRODUCTION_LOOP_REPORT.md` §2 | "All 337 retained jobs use the same six node classes" — the history summary shows **335**. Two jobs used `UNETLoader`/`CLIPLoader`/`VAELoader`/`EmptySD3LatentImage`/`ModelSamplingAuraFlow` at 8 steps, cfg 1.0. The forensics doc has this right. The conclusion — zero identity nodes in all 337 — is unaffected |
| `PANEL_PRODUCTION_LOOP_REPORT.md` §3 | Describes five experiments. `exp006-determinism` exists in the repo, ran successfully, and returned **`deterministic: False`**. It is not mentioned |
| `PANEL_PRODUCTION_LOOP_REPORT.md` §6 | "The panel is re-runnable from saved configuration" — exp001/002/003/006 have runner scripts, graphs and manifests. **exp004 and exp005 have only a placement report.** No `LightContract`, no script. The geometry reproduces exactly; the pixels do not |
| `PANEL_PRODUCTION_LOOP_REPORT.md` §3 | "Output at the layout spec's exact 1534×1642" — true, but it is a 1.6× LANCZOS upscale of a 960×1024 render, with no upscale model installed |
| `PANEL_PRODUCTION_LOOP_REPORT.md` §7 | Records "74 passed". The suite now reports **76** |
| `12_qa/review-packages/ISSUE001-P16-02/placement_report.json` | `warnings: []`. The exp005 report carries the `CANON: refused to mirror MZ-CHAR-001` warning. **The shipped review package does not contain the guard evidence the report cites** |
| `COMFYUI_PREVIOUS_WORKFLOW_FORENSICS.md` final section | References `COMFYUI_LIVE_ENVIRONMENT_AUDIT.md`. No such file exists. The content is in `docs/workflows/COMFYUI_CAPABILITY_AUDIT.md` |
| `ISSUE001-P16-02` staging | Both scripted expressions (`EXP-005-sad`, `EXP-001-neutral`) have no approved layer. Substitutes were used and the substitution is recorded nowhere |
| `ISSUE001-P16-02` scale | Script says Moodz is 8 % smaller; he renders 22 % smaller |

---

## 13. Next actions

From the loop report, in order, unchanged:

1. Run the remaining seven panel types, three runs each.
2. Execute the repair workflow against a deliberately introduced defect.
3. Verify `depth_anything_v2_vitl.pth` is on disk and run the depth-guided path.
4. Produce Lil Devil alpha layers via RemBG.
5. Solve eye-line direction — likely ControlNet openpose over approved art.
6. Calibrate the four approved festival plates.
7. Only then create `workflows/comfyui/locked/panel-production-v1/`.

Add, from section 12:

8. Save the exp004/exp005 compositor configuration so the validated panel is
   actually reproducible.
9. Re-export `placement_report.json` into the review package with its warnings.
10. Write the layout-box-to-pixels conversion into a script so it stops being a
    hand calculation.
