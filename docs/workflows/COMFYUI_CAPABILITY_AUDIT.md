# ComfyUI Capability Audit

**Audited 2026-07-28 by direct query against the running instance.** Reproduce
with:

```bash
python -m app.cli.main comfy
```

Adapter: `app/adapters/comfyui.py`. Read-only — it never queues a job.

---

## Connection

| Property | Value |
|---|---|
| Endpoint | `http://127.0.0.1:8188` |
| Status | **Reachable and responding** |
| ComfyUI version | 0.19.3 |
| Python | 3.13.12 |
| PyTorch | 2.7.0+cu118 |
| Node types registered | **1158** |

The brief anticipated a separate machine. The instance is on `127.0.0.1` from
this host. Whether that is the same physical box or a tunnel was not
determined and does not change the plan.

### Launch configuration

```
ComfyUI/main.py
  --input-directory  I:\ai\nft\input
  --output-directory I:\ai\nft\output
  --temp-directory   I:\ai\cache\temp
  --preview-method auto
  --use-split-cross-attention
  --disable-cuda-malloc
  --disable-smart-memory
```

`--use-split-cross-attention`, `--disable-cuda-malloc` and
`--disable-smart-memory` are all ZLUDA stability flags. They cost throughput and
are presumably load-bearing on this rig. **Do not remove them casually.**

---

## Hardware

| Property | Value |
|---|---|
| GPU | **AMD Radeon RX 6800, via ZLUDA** (presents as `cuda:0`) |
| VRAM | 17.2 GB total |
| System RAM | 137.4 GB |

Matches the brief. ZLUDA is a CUDA compatibility layer over ROCm — most things
work, some do not, and failures tend to be silent or crashes rather than clean
errors. The source project's own records note a hang history on this rig.

**Implication:** treat every generation job as potentially failing. Job manifests
must be resumable, and nothing should depend on a long unattended batch.

---

## Models installed

### Checkpoints — 2

| Model | Character |
|---|---|
| `RealVisXL_V4.0.safetensors` | SDXL, photorealistic |
| `animagine-xl-4.0.safetensors` | SDXL, anime |

### UNet — 1
`z_image_turbo_bf16.safetensors` — fast, low step count.

### VAE — 7
`sdxl_vae`, `z_image_ae`, plus TAESD family and `pixel_space`.

### ControlNet — 1
`controlnet-union-sdxl-1.0-promax.safetensors` — a union model covering openpose,
depth, canny, scribble, segmentation and more through one loader, selected via
`SetUnionControlNetType`.

### IP-Adapter — 1
`ip-adapter-plus_sdxl_vit-h.safetensors`, with
`CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` as the vision encoder.

### LoRA — **0**
### Upscale models — **0**

---

## The finding that shapes everything

> **There is no MonkeyZoo style LoRA, and neither installed checkpoint produces
> the house style.**

`RealVisXL` is photoreal. `animagine-xl` is anime. The house style — established
by three published Fiend Studios editions — is flat-fill cel-shaded vector
cartoon with thick uniform outlines and chibi proportions.

Prompt engineering can push SDXL toward a cartoon look. It cannot make it
reliably produce *this* cartoon look, and it certainly cannot make it produce
*this character* consistently across 103 panels.

Three consequences, and they are the whole production plan:

1. **Character identity must come from approved art, not from text-to-image.**
   The 139-file true-alpha layer library is not a convenience — it is the only
   route to consistent identity.
2. **Backgrounds can be generated**, because a plate is a place, not a
   character, and drift is tolerable and correctable. They still need palette
   locking and human selection.
3. **A style LoRA is the highest-value future investment.** Training data
   already exists: three published editions plus the approved canon library.

---

## Capabilities confirmed present

Verified by node registration:

| Capability | Present | Use here |
|---|---|---|
| ControlNet | Yes | Pose and depth control |
| ControlNet Union type selection | Yes | One model, many control types |
| IP-Adapter | Yes | Reference conditioning from approved art |
| IP-Adapter FaceID | Yes | Face consistency; value on chibi faces untested |
| OpenPose preprocessor | Yes | Pose extraction from approved poses |
| Depth preprocessor | Yes | Depth from approved plates for new angles |
| Canny preprocessor | Yes | Line control |
| Inpainting | Yes | Targeted panel repair without full regeneration |
| Inpaint preprocessor | Yes | Mask preparation |
| Background removal (RemBG) | Yes | New alpha layers, including Lil Devil |
| Transparent background session | Yes | Alternative alpha route |
| Mask compositing | Yes | Deterministic layer assembly |
| CLIP Vision | Yes | Required by IP-Adapter |
| Upscale model loader | Node present, **no models installed** | Cannot upscale until one is added |

---

## Gaps

| Gap | Impact | Fix |
|---|---|---|
| No style LoRA | Generated art will not match house style unaided | Train one from the published editions and approved canon |
| No upscale model | Cannot enlarge panel art for print | Install a 4x model |
| ZLUDA instability | Long batches unreliable | Small resumable jobs, checkpointed manifests |
| Only SDXL-class checkpoints | Neither is close to house style | Style LoRA on top of SDXL, or a different base |
| No Lil Devil alpha layer | Issue 001 guest cannot be staged | RemBG over approved Lil Devil art |
| No festival plate calibration | Character scale has no defensible basis | Author calibrations to the existing format |

---

## Practical limits

| Constraint | Estimate | Basis |
|---|---|---|
| Max practical SDXL resolution | ~1536×1536, or ~1920×1080 landscape | 17.2 GB VRAM with split cross-attention |
| Panel plate target | 1536×864 (16:9) or 1024×1536 (portrait) | Above final print need at 300 dpi for most panels |
| Full-page splash plate | Needs tiling or an upscale model | Page 11 at 300 dpi is 2480×3508 |
| Expected time per SDXL image | Not measured | **Not benchmarked — do not plan schedules on a guess** |
| Batch reliability | Assume low | Documented hang history |

Generation speed was deliberately **not** estimated. No job has been run.

---

## What was NOT tested

Stated plainly because it matters:

- **No image has been generated.** This audit is capability discovery only.
- Identity preservation via IP-Adapter against approved MonkeyZoo art: untested.
- ControlNet Union pose transfer onto chibi proportions: untested.
- RemBG quality on flat cel-shaded art with black outlines: untested.
- Actual generation speed: unmeasured.
- Batch stability: unmeasured.

The controlled test defined in `COMFYUI_INTEGRATION_PLAN.md` exists to close
these gaps before any bulk work.

---

## Output paths

| Purpose | Path |
|---|---|
| Input | `I:\ai\nft\input` |
| Output | `I:\ai\nft\output` |
| Temp | `I:\ai\cache\temp` |

These are **outside this repository** and are machine-specific. Nothing in the
repo may hard-code them; the integration reads them from
`config/local/`, which is git-ignored.

Existing output subdirectories show prior MonkeyZoo work: `MZ-2026-07-05`,
`MZ-2026-08-01`, `MZ-2026-08-06`, `MZ-CLEVER-PILOT`, and an `mz-canon` input
directory. Prior batches were run here; none of them produced finished Issue 001
artwork.
