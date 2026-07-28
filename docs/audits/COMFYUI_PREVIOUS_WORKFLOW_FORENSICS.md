# ComfyUI Previous Workflow — Forensics

**Investigated 2026-07-28.** Primary evidence: the live ComfyUI instance's own
`/history` endpoint, which had retained **337 completed jobs** including every
legacy Issue 001 generation, with full graphs and prompts.

Raw evidence retained at `workflows/comfyui/discovery/comfy_history_summary.json`.

---

## Headline

**The previous process did not break. It never did the thing it appeared to be
doing.**

There was no ControlNet stage, no IP-Adapter stage, no reference image, no
img2img, no mask, no LoRA, and no compositing step anywhere in the recorded
history. Every panel was a single text-to-image roll from a written description
of the character.

Nothing was lost. Nothing regressed. The identity-preservation step was never
built.

---

## What the history actually contains

337 jobs. Node classes used, across all of them:

| Count | Node class |
|---:|---|
| 672 | `CLIPTextEncode` |
| 337 | `KSampler` |
| 337 | `VAEDecode` |
| 337 | `SaveImage` |
| 335 | `CheckpointLoaderSimple` |
| 335 | `EmptyLatentImage` |
| 2 | `UNETLoader`, `CLIPLoader`, `VAELoader`, `ConditioningZeroOut`, `EmptySD3LatentImage`, `ModelSamplingAuraFlow` |

That is the complete list.

**Absent from all 337 jobs:**

- `ControlNetLoader` / `ControlNetApplyAdvanced` / `SetUnionControlNetType`
- `IPAdapterModelLoader` / `IPAdapterAdvanced` / `IPAdapterFaceID`
- `CLIPVisionLoader`
- `LoadImage` — **no reference image was ever loaded**
- `VAEEncode` / `VAEEncodeForInpaint` / `SetLatentNoiseMask` — no img2img, no inpainting
- `LoraLoader`
- `ImageCompositeMasked` — no compositing
- Any background-removal or mask node

### Checkpoints and settings actually used

| Checkpoint | Jobs |
|---|---:|
| `RealVisXL_V4.0.safetensors` | 286 |
| `animagine-xl-4.0.safetensors` | **49** |

| Sampler config | Jobs |
|---|---:|
| `dpmpp_2m` / `karras` / 28 steps / cfg 5.5 | 286 |
| `dpmpp_2m` / `karras` / 28 steps / cfg 6.0 | **49** |
| `res_multistep` / `simple` / 8 steps / cfg 1.0 | 2 |

| Latent size | Jobs |
|---|---:|
| 1344×768 | 143 |
| 1024×1024 | 143 |
| **1216×832** | **49** |

The 49-job cluster is the legacy Issue 001 run: `animagine-xl-4.0`, cfg 6.0,
1216×832. The 286-job cluster is an unrelated project (`signal-notes/hero`).

---

## The exact graph that produced the published page 1

Recovered verbatim from history, job prefix
`MZ-2026-08-01/MZ-2026-08-01_P01_PANEL02_seed100102`:

```
[1] CheckpointLoaderSimple   ckpt_name = animagine-xl-4.0.safetensors
[2] CLIPTextEncode           positive
[3] CLIPTextEncode           negative
[4] EmptyLatentImage         1216 x 832
[5] KSampler                 seed=100102 steps=28 cfg=6.0 dpmpp_2m/karras denoise=1.0
[6] VAEDecode
[7] SaveImage                MZ-2026-08-01/..._P01_PANEL02_seed100102
```

**Seven nodes.** The positive prompt described the character in words:

> "MonkeyZoo house style: chibi cartoon monkey with oversized round head, huge
> white oval eyes with tiny black dot pupils, two small dot nostrils, thick
> uniform black outlines, flat color fills with soft cel shading, simplified
> plush body with visible stitch seams, mitten hands, curled tail, clean vector
> cartoon look, dark cartoon sci-fi cyberpunk backdrop. NeonBlue listing duties
> on fingers while Li…"

The negative prompt already contained the right instincts — `extra limbs`,
`fingers`, `identity drift`, `cutout cards`, `borders`, `frame boxes` — which
tells us the operator knew the failure modes. They had no mechanism to prevent
them.

### What that graph produced

`I:\ai\nft\output\MZ-2026-08-01\MZ-2026-08-01_P01_PANEL02_seed100102_00001_.png`
— a **pink alien creature with a detached floating eyeball**, on a purple
striped background. 1216×832.

Prompt and output are both recovered, and the causal chain is complete: this
image is the origin of the five off-model pink figures on the published page 1.

---

## Why it failed — root cause

**Text-to-image cannot preserve character identity.** Asking SDXL to draw
"NeonBlue" produces whatever the model associates with the words around it. The
approved character art existed the whole time — 417 files — and was never
connected to the generator.

Contributing factors, in order of severity:

| # | Factor | Evidence |
|---|---|---|
| 1 | **No identity conditioning of any kind** | Zero `LoadImage`, `IPAdapter*`, `ControlNet*` or `LoraLoader` nodes in 337 jobs |
| 2 | **Wrong checkpoint for the job** | `animagine-xl-4.0` used for all 49 Issue 001 jobs. Experiment 001 shows it produces incoherent, over-saturated output for this style; `RealVisXL_V4.0` is markedly better |
| 3 | **No compositing stage** | The card-paste in `compose_issue01_draft_panels.py` was a fallback for the missing render, not a design |
| 4 | **No output curation** | Raw rolls were copied into a directory named `selected_panels` with no selection step |
| 5 | **No provenance link** | Four different images per panel ID across four directories; nothing recorded which was authoritative |

### What did NOT cause it

Ruled out by evidence, so nobody re-investigates them:

- **Not** missing workflow files — the graphs are intact in history.
- **Not** changed model paths — both checkpoints are still installed and load.
- **Not** missing custom nodes — every node the graphs use is registered, and
  far more besides.
- **Not** a broken API — 337 jobs completed with `status: success`.
- **Not** the wrong output directory — outputs are exactly where the graphs said.
- **Not** ZLUDA or AMD instability — no failed jobs in the retained history.
- **Not** lost reference images — no reference image was ever used.
- **Not** a resolution or aspect problem — 1216×832 is a valid SDXL bucket.

The environment was healthy throughout. The workflow was the problem.

---

## Why the finished process was never saved

Because there was no finished process to save.

The `.art-workspace/attempts/*.json` records describe imports with
`"source_type": "manual_import"` and `"provider": "draft_composite"` — the
pipeline recorded that a human handed it a file, not that ComfyUI produced a
panel. The generation step and the assembly step were never connected.

---

## What is recoverable

| Asset | State |
|---|---|
| Every legacy prompt and graph | **Recovered** from `/history`, 337 jobs |
| Seeds | **Recovered** — encoded in filenames and graphs (100101–100801 series) |
| Model and sampler settings | **Recovered** |
| Output images | Present in `I:\ai\nft\output\MZ-2026-08-01\` (49 files) |
| PNG embedded metadata | Present — every output carries a `prompt` chunk |
| 139 true-alpha character layers | Intact, imported |
| Approved canon, 417 character files | Intact, imported |

Nothing needed for the rebuild is missing.

---

## What should be rebuilt

Everything between "background exists" and "panel exists". Specifically:

1. A background stage that produces frameless, characterless plates in house
   style — **built and validated**, see `PANEL_PRODUCTION_LOOP_REPORT.md`.
2. A character stage that sources identity from approved art rather than text.
3. A compositing stage with ground-plane placement, scale, contact shadow, cast
   shadow, relight and colour spill.
4. Metadata capture on every job.
5. A curation step between generation and `selected`.

---

## What should not be reused

| Do not reuse | Why |
|---|---|
| The 7-node text-to-image graph for characters | It is the root cause |
| `animagine-xl-4.0` for backgrounds | Experiment 001: incoherent for this style |
| The legacy prompt strings | They describe a character the model cannot draw |
| The card-paste compositor | Produces the pasted-on defect by construction |
| Anything in `selected_panels/` | Uncurated raw output |

---

## Environment note discovered during this run

**The ComfyUI instance is shared.** During experiment 002, jobs with the prefix
`signal-notes/hero` interleaved with ours in the queue — an unrelated project is
actively generating on the same GPU. 286 of the 337 history entries belong to it.

Consequences:

- Wall-clock timings are contended and not reproducible.
- The queue is not exclusively ours; batch scheduling must tolerate interleaving.
- Recorded in `COMFYUI_LIVE_ENVIRONMENT_AUDIT.md` as an operational constraint.
