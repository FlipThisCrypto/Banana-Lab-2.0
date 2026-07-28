# ComfyUI Integration Plan

Capability facts: `COMFYUI_CAPABILITY_AUDIT.md`. This document is what we do
about them.

## Principle

> The generator changes **pose, expression and place**. It never invents a
> **character**.

Identity comes from art the owner approved. There is no style LoRA and neither
installed checkpoint produces the house style, so uncontrolled text-to-image
cannot be trusted with a character. That is not a limitation to work around —
it is the constraint the whole design rests on.

---

## Four job classes

### Class A — Background plate generation
**Risk: low.** A plate is a place, not a character. Drift is tolerable and
correctable, and every plate is human-selected before use.

- Base: SDXL, prompted from the location `bible.md` and palette
- Optional: depth from an approved plate, via ControlNet Union, for a new camera
  angle on an established location
- Output: frameless, textless, no characters, no panel borders
- Destination: `06_backgrounds/generated_candidates/`

### Class B — Alpha layer extraction
**Risk: low.** Deterministic, no diffusion involved.

- Input: approved character art
- Process: RemBG or TransparentBG, then baked-shadow stripping
- Output: true-alpha PNG
- **First job: the Lil Devil layer set.** He appears in 17 panels and has no
  layer at all.

### Class C — New pose and expression
**Risk: high.** This is where identity drifts.

- Base: SDXL with IP-Adapter Plus conditioned on approved character reference
- Control: ControlNet Union in openpose mode, from an approved pose
- Output: candidate only, into `characters/generated_candidates/`
- **Never overwrites an approved asset. Always human-reviewed.**

The source project's integration track already rejected img2img for this, with
measured identity-drift evidence and hallucination at cfg 1.0. **Do not retry
it.**

### Class D — Panel repair
**Risk: medium.** Targeted inpainting on an approved composite.

- Masked region only, everything else untouched
- Output preserves the original as a version; repair is never destructive

---

## Job manifest

Every job, of every class, produces a manifest. No job runs without one.

```yaml
job_id: JOB-issue001-P16-02-bg-001
job_class: A
workflow_version: bg-plate-v1
created: 2026-08-01T10:00:00Z

issue_id: issue-001
panel_id: ISSUE001-P16-02
character_id: null

prompt: >-
  Service corridor interior, pipework along one wall, floor grating, single
  overhead red practical light midway, deep one-point perspective, MonkeyZoo
  house style, flat cel shading, thick black outlines, no characters, no text,
  no panel border
negative_prompt: >-
  characters, people, text, watermark, logo, panel border, frame, speech bubble,
  photorealistic, blurry

model: RealVisXL_V4.0.safetensors
vae: sdxl_vae.safetensors
lora: null
sampler: dpmpp_2m
scheduler: karras
steps: 30
cfg: 6.5
seed: 811420
width: 1536
height: 864

source_references: []
control_images: []
masks: []

output: 06_backgrounds/generated_candidates/P16-02_corridor_a.png
output_sha256: <filled after the run>

review_status: candidate      # candidate | approved | rejected
reviewed_by: ""
review_note: ""
```

Rules:

1. **Seed is always recorded.** An unreproducible image cannot be iterated on.
2. **`review_status` starts at `candidate`.** No job may write `approved`.
3. **Manifests are committed; outputs are not.** The manifest is the provenance
   record; `.gitignore` keeps the bytes out.
4. **Output hash is recorded** so a swapped file is detectable.

---

## The controlled test — gate before any bulk work

Nothing generates in bulk until one panel proves the chain end to end.

**Test panel: `ISSUE001-P16-02`** — NeonBlue and Moodz in the service corridor.

Chosen because it exercises everything that matters and nothing that does not:

- Two characters at measurably different depths
- One strong, directional, coloured practical light
- A hard floor plane with a grating pattern that shadows must follow
- A quiet performance beat needing readable expressions
- An existing approved location plate to work from

### Steps

| Step | Class | Output |
|---|---|---|
| 1 | — | Calibrate the corridor plate: horizon, scale reference, light direction, ground surface |
| 2 | A | Generate corridor plate candidates, human-select one |
| 3 | B | Confirm NeonBlue and Moodz alpha layers are clean at panel scale |
| 4 | — | Composite: scale, ground contact, contact shadow, relight, colour spill, edge treatment |
| 5 | — | Human review against the pass criteria |

### Pass criteria

1. Both characters recognisably themselves against approved reference.
2. Feet meet the grating with correct perspective.
3. Contact shadow follows the grating pattern, not a generic ellipse.
4. Key light direction on both figures matches the overhead practical.
5. No matte halo at any character edge.
6. Relative scale consistent with the door-frame reference in the plate.
7. Moodz is visibly not reaching toward NeonBlue — the staging reads.
8. It sits beside an Edition Two panel without looking like a different project.

**If any criterion fails, diagnose and fix the method. Do not proceed and do not
work around it.**

---

## Rollout after the test passes

| Phase | Work | Gate |
|---|---|---|
| 1 | Calibrate all four festival plates | — |
| 2 | Lil Devil alpha layer set | Human review |
| 3 | Background plates for pages 1–7 | Human selection |
| 4 | Composite pages 1–7 | Panel QA |
| 5 | Review the first seven pages as a block | **Owner** |
| 6 | Remaining plates and composites | Panel QA per page |
| 7 | Full-page splash plate for page 11 | Owner — highest-value single plate |
| 8 | Lettering, effects, assembly | Page QA |

Reviewing pages 1–7 as a block before continuing means a systemic problem costs
seven pages, not twenty-two.

---

## Hard rules

1. Never write into `source_material/`. `app/core/paths.py` refuses.
2. Never write into any `approved/` directory from a generation job.
3. Never overwrite an approved asset. Revisions are new versioned files.
4. Never use text-to-image alone for an established character.
5. Never retry img2img edge unification — tested and rejected with evidence.
6. Never run an unattended batch larger than one page. ZLUDA has a documented
   hang history on this rig.
7. Never let a job set `review_status: approved`.
8. Always record the seed.
9. Always keep intermediate layers and masks, so a defect can be repaired
   without regenerating the panel.

---

## Deferred

Not built in this run, and deliberately so:

- **Queue submission.** The adapter is read-only. Submission is added after the
  controlled test defines what a correct job looks like.
- **Style LoRA training.** Highest-value future work. Training data exists —
  three published editions plus the approved canon library.
- **Upscale.** No upscale model is installed. Needed before print-resolution
  splash pages.
- **Automated composite pipeline.** The source project's `build_panel.py`
  approach is proven and should be ported, but only after the method is
  re-validated on this issue.
