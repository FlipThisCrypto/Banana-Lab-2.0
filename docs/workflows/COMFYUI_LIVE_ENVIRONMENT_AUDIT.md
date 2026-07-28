# ComfyUI Live Environment Audit

**Audited 2026-07-28.** Phase 2 deliverable. This is the *operational* audit: what
the machine did when we ran real work on it, what it has never been asked to do,
and what that means for scheduling.

`COMFYUI_CAPABILITY_AUDIT.md` is the *capability* audit — what is installed and
registered, discovered by read-only probe before any job was run. It remains the
reference for the installed inventory. This document does not repeat it; it
qualifies it with execution evidence and corrects it where execution disagreed.

**Corrections to the earlier audit are listed in §2. Read that section first if
you have already read the earlier document.**

---

## 1. Evidence grades

Every claim below carries one of these markers. Nothing is unmarked.

| Marker | Meaning |
|---|---|
| **MEASURED** | Observed in a retained artefact in this repo — a job manifest, a PNG, a history dump, or source code. Path given. |
| **INFERRED** | Reasoned from a measured fact. The reasoning is stated so it can be attacked. |
| **NOT MEASURED** | Nobody has tested this. Stated so it is not mistaken for a known quantity. |

Primary evidence used:

| Evidence | Path |
|---|---|
| 7 GPU job manifests with timings, seeds, graphs, output hashes | `workflows/comfyui/experiments/exp00{1,2,3,6}-*/` |
| 2 CPU composite reports | `workflows/comfyui/experiments/exp00{4,5}-*/exp00*_report.json` |
| 337-job history summary | `workflows/comfyui/discovery/comfy_history_summary.json` |
| Read-only probe implementation | `app/adapters/comfyui.py` |
| Job client implementation | `app/adapters/comfy_client.py` |
| Graph builders | `app/services/workflows.py` |
| Compositor | `app/services/compositor.py` |

---

## 2. Corrections to `COMFYUI_CAPABILITY_AUDIT.md`

The earlier audit was written before any job had been run and said so plainly.
Four of its statements are now out of date, and one of its methods is weaker than
it reads. None of this is a criticism of that document — it was correct at the
time and honest about its limits.

| Earlier statement | Status now | Correction |
|---|---|---|
| "**No image has been generated.** This audit is capability discovery only." | **Superseded** | 7 GPU jobs have run. Manifests retained. |
| "Expected time per SDXL image — **Not benchmarked — do not plan schedules on a guess**" | **Superseded** | Benchmarked. See §8. The instruction not to plan schedules on a guess still holds for a different reason: contention, not absence of data. |
| "Generation speed was deliberately **not** estimated. No job has been run." | **Superseded** | See §8. |
| "Batch reliability — Assume low. Documented hang history." | **Still unverified** | The hang history is inherited from the source project's records, not observed here. No hang, crash or failed job has been observed on this instance in any retained evidence. See §10. |
| Capability table: 14 capabilities marked "Yes" | **Correct but narrower than it reads** | "Yes" means *a node class of that name is registered*. It does not mean the auxiliary model weights the node needs are on disk, and it does not mean the node has ever executed under ZLUDA. Neither was checked. See §7. |

One imprecision worth flagging rather than correcting: the earlier audit says of
the prior output directories that "none of them produced finished Issue 001
artwork." `COMFYUI_PREVIOUS_WORKFLOW_FORENSICS.md` establishes that
`MZ-2026-08-01` output *is* the origin of the five off-model pink figures on the
published page 1. Both statements are defensible under different readings of
"finished", but the directory did produce artwork that shipped.

Nothing else in the earlier audit is contradicted here.

---

## 3. Service and API surface

| Property | Value | Grade |
|---|---|---|
| Endpoint | `http://127.0.0.1:8188` | MEASURED |
| ComfyUI version | 0.19.3 | MEASURED |
| Python | 3.13.12 | MEASURED (earlier audit) |
| PyTorch | 2.7.0+cu118 | MEASURED (earlier audit) |
| Registered node types | 1158 | MEASURED |
| Transport | HTTP, unauthenticated, loopback only | MEASURED |

### Endpoints actually exercised

| Endpoint | Used by | Exercised | Evidence |
|---|---|---|---|
| `GET /system_stats` | `app/adapters/comfyui.py:probe` | **Yes** | version, VRAM, RAM, argv all recovered |
| `GET /object_info` | `app/adapters/comfyui.py:probe` | **Yes** | 1158 node types, model lists |
| `POST /prompt` | `comfy_client.submit` | **Yes** | 7 `prompt_id` values in manifests |
| `GET /history/{prompt_id}` | `comfy_client.wait` | **Yes** | all 7 jobs collected |
| `GET /history` | forensics dump | **Yes** | 337 jobs summarised |
| `GET /view` | `comfy_client.fetch_outputs` | **Yes** | 7 PNGs retained |
| `POST /upload/image` | `comfy_client.upload_image` | **No — never called** | code exists; no retained job uses it |
| `GET /queue`, `POST /interrupt` | nothing | **No** | not called anywhere in the codebase |
| WebSocket `/ws` | nothing | **No** | the client polls `/history` every 2 s instead |

**The upload path has never run.** This matters more than it looks. Three of the
four workflow builders (`background_from_reference`, `inpaint_repair`, and any
future IP-Adapter character job) require pushing a local image into ComfyUI's
input directory and referencing it from `LoadImage`. Neither the upload nor the
`LoadImage` node has ever executed on this instance — not in our 7 jobs, and not
in any of the 337 history jobs (`LoadImage` count: **0**). Treat it as untested
code on untested hardware.

### Queue visibility — a real gap

`comfy_client.wait` polls `GET /history/{prompt_id}` every 2 seconds until the
job appears, with a default 900 s deadline. It never reads `/queue`.

Consequence: **the client cannot distinguish "queued behind another project's
job" from "running slowly".** Both look like an absent history entry. On a shared
instance (§11) that is the difference between a 42-second job and a 409-second
one, and we currently have no way to tell them apart at runtime. Reading `/queue`
before and during a submission is the cheapest available fix and is not built.

---

## 4. Filesystem and paths

| Purpose | Path | Grade |
|---|---|---|
| Input | `I:\ai\nft\input` | MEASURED (launch argv) |
| Output | `I:\ai\nft\output` | MEASURED (launch argv) |
| Temp | `I:\ai\cache\temp` | MEASURED (launch argv) |

Launch flags:

```
--input-directory  I:\ai\nft\input
--output-directory I:\ai\nft\output
--temp-directory   I:\ai\cache\temp
--preview-method auto
--use-split-cross-attention
--disable-cuda-malloc
--disable-smart-memory
```

The last three are ZLUDA stability flags. They cost throughput. **Do not remove
them casually** — and note that no measurement exists of what they cost, because
no run has been attempted without them (NOT MEASURED).

**These paths are machine-specific and outside the repository.** Nothing in the
repo may hard-code them. `config/local/comfyui.yaml` is the only place they
belong, it is git-ignored, and `python -m app.cli.main validate` fails the build
on absolute paths found in committed YAML. See `config/local/README.md`.

One consequence of the output directory being external: **generated PNGs are
fetched over `GET /view` and written into the repo by
`comfy_client.fetch_outputs`, not read from `I:\ai\nft\output` directly.** That
is deliberate and it is the behaviour that keeps the pipeline working if the
ComfyUI host ever moves off this box.

---

## 5. Hardware and runtime

| Property | Value | Grade |
|---|---|---|
| GPU | AMD Radeon RX 6800 via ZLUDA, presents as `cuda:0` | MEASURED |
| VRAM | 17.2 GB | MEASURED |
| System RAM | 137.4 GB | MEASURED |

ZLUDA is a CUDA compatibility shim over ROCm. The general risk is well known:
most operations work, some do not, and failures tend to surface as hangs or
silent wrong results rather than clean exceptions.

**What we have actually observed on this rig, however, is uneventful.** Across
337 retained history jobs and our own 7 jobs, there is no recorded failure,
crash, hang or error status. Every job returned success. See §10 before reading
that as reassurance — the workload exercised is extremely narrow.

---

## 6. Models by class

All MEASURED, by `/object_info` option enumeration (`app/adapters/comfyui.py:_options`).

| Class | Count | Installed |
|---|---:|---|
| Checkpoints | 2 | `RealVisXL_V4.0.safetensors` (SDXL, photoreal base), `animagine-xl-4.0.safetensors` (SDXL, anime) |
| UNet | 1 | `z_image_turbo_bf16.safetensors` |
| VAE | 7 | `sdxl_vae`, `z_image_ae`, TAESD family, `pixel_space` |
| ControlNet | 1 | `controlnet-union-sdxl-1.0-promax.safetensors` |
| IP-Adapter | 1 | `ip-adapter-plus_sdxl_vit-h.safetensors` |
| CLIP Vision | 1 | `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` |
| **LoRA** | **0** | — |
| **Upscale models** | **0** | — |

### Which of these have ever been loaded

| Model | Loaded in a real job | Evidence |
|---|---|---|
| `RealVisXL_V4.0` | **Yes** — 286 history jobs + 5 of our 7 | history summary; exp001/002/003/006 manifests |
| `animagine-xl-4.0` | **Yes** — 49 history jobs + 1 of ours | history summary; exp001 animagine manifest |
| `z_image_turbo_bf16` | **Yes** — 2 history jobs | history summary: `UNETLoader` ×2, `EmptySD3LatentImage` ×2, `ModelSamplingAuraFlow` ×2 |
| `sdxl_vae` (standalone) | **No** | our graphs use the checkpoint's baked VAE (`["1", 2]`) |
| `controlnet-union-sdxl-1.0-promax` | **No** | `ControlNetLoader` count in 337 history jobs: **0**. Zero in our jobs. |
| `ip-adapter-plus_sdxl_vit-h` | **No** | `IPAdapterModelLoader` count: **0** |
| `CLIP-ViT-H-14-...` | **No** | `CLIPVisionLoader` count: **0** |

**The two models the whole identity-preservation plan depends on — the ControlNet
union and the IP-Adapter — have never been loaded on this machine.** They are
installed. Whether they load, whether they fit alongside SDXL in 17.2 GB, and
whether they execute correctly under ZLUDA are all open questions.

### Auxiliary model weights — unverified

Node registration does not imply the node's own model file is present. Two known
cases:

| Needed by | File | Status |
|---|---|---|
| `DepthAnythingV2Preprocessor` in `background_from_reference` | `depth_anything_v2_vitl.pth` | **Presence unverified.** Hard-coded at `app/services/workflows.py:180`. |
| `RemBGSession+` / `TransparentBGSession+` (Class B alpha extraction) | RemBG session weights | **Presence unverified.** These packs typically fetch on first use, which on a machine with no assured outbound path is a failure mode of its own. |

Verifying both is a two-minute job and should be done before either workflow is
scheduled.

---

## 7. Custom node packs and capabilities

### Packs

MEASURED by live probe. Counts are node classes contributed per pack.

| Pack | Node classes |
|---|---:|
| `was-node-suite-comfyui` | 220 |
| `ComfyUI_essentials` | 85 |
| `comfyui_controlnet_aux` | 64 |
| `ComfyUI_IPAdapter_plus` | 37 |
| `comfyui-tooling-nodes` | 28 |
| `rgthree-comfy` | 24 |
| `comfyui-tensorops` | 17 |
| **Pack subtotal** | **475** |
| Core ComfyUI and everything else | 683 |
| **Total registered** | **1158** |

The raw probe output backing the per-pack counts is **not retained in this
repository** — only the summary above and the aggregate 1158 from
`/object_info`. That is a gap. `python -m app.cli.main comfy` reproduces the
probe but writes nothing to disk; it should dump JSON into
`workflows/comfyui/discovery/` the way the history dump does.

### Capability matrix

`app/adapters/comfyui.py:CAPABILITY_NODES` maps 14 capability names to node
classes and reports a capability present if **any** listed class is registered.
That is a deliberately loose test and it needs saying out loud.

| Capability | Probe node classes | Registered | **Ever executed here** |
|---|---|---|---|
| ControlNet | `ControlNetLoader`, `ControlNetApplyAdvanced` | Yes | **No** |
| ControlNet Union type select | `SetUnionControlNetType` | Yes | **No** |
| IP-Adapter | `IPAdapterModelLoader`, `IPAdapterAdvanced` | Yes | **No** |
| IP-Adapter FaceID | `IPAdapterFaceID` | Yes | **No** |
| Pose (OpenPose) preprocessor | `OpenposePreprocessor` | Yes | **No** |
| Depth preprocessor | `DepthAnythingV2Preprocessor`, `MiDaS-DepthMapPreprocessor` | Yes | **No** |
| Canny preprocessor | `CannyEdgePreprocessor`, `Canny` | Yes | **No** |
| Inpainting | `VAEEncodeForInpaint`, `InpaintModelConditioning` | Yes | **No** |
| Inpaint preprocessor | `InpaintPreprocessor` | Yes | **No** |
| Background removal | `RemBGSession+`, `Image Rembg (Remove Background)` | Yes | **No** |
| Transparency / transparent background | `TransparentBGSession+` | Yes | **No** |
| Mask compositing | `ImageCompositeMasked`, `LatentCompositeMasked` | Yes | **No** |
| CLIP Vision | `CLIPVisionLoader` | Yes | **No** |
| Upscale model loader | `UpscaleModelLoader` | Yes (node) | **No** — and **0 models installed** |

**Every node class that has ever executed on this instance, across the 337-job
history snapshot plus our 7 experiment jobs, is one of these seven:**

`CheckpointLoaderSimple`, `CLIPTextEncode`, `EmptyLatentImage`, `KSampler`,
`VAEDecode`, `SaveImage` — plus `UNETLoader`/`CLIPLoader`/`VAELoader`/
`ConditioningZeroOut`/`EmptySD3LatentImage`/`ModelSamplingAuraFlow` in exactly 2
of the 337 history jobs.

Segmentation is a further step removed: it is available in principle through
`SetUnionControlNetType` (the promax union model covers segmentation among other
types) and through `comfyui_controlnet_aux`, but no segmentation-specific node
was enumerated by the probe and none has run. Treat segmentation as **NOT
VERIFIED**, not as available.

Transparency has two independent routes (`RemBGSession+` and
`TransparentBGSession+`) and neither has been exercised. Note that the 139
existing true-alpha character layers were **imported**, not produced here — the
alpha extraction path is entirely unproven on this machine.

---

## 8. Measured performance

MEASURED. Source: the `seconds` field of each retained job manifest.

**What `seconds` measures:** `comfy_client.run` starts the clock before
`POST /prompt` and stops it after the last output has been downloaded over
`/view`. It therefore includes queue wait, sampling, VAE decode, PNG encode and
HTTP transfer, and it is quantised to the 2-second poll interval. It is
wall-clock cost to us, not GPU time. On a shared instance that is the right thing
to measure and the wrong thing to extrapolate from.

| Job | Size | Steps | Model | Seconds |
|---|---|---:|---|---:|
| `EXP002-760201` | 960×1024 | 32 | RealVisXL | **42.3** |
| `EXP001-animagine` | 1344×768 | 30 | animagine-xl | **90.8** |
| `EXP006-determinism` | 960×1024 | 32 | RealVisXL | **98.6** |
| `EXP001-realvis` | 1344×768 | 30 | RealVisXL | **112.6** |
| `EXP003-760201` | 960×1024 | 32 | RealVisXL | **116.6** |
| `EXP003-760202` | 960×1024 | 32 | RealVisXL | **397.9** |
| `EXP002-760202` | 960×1024 | 32 | RealVisXL | **409.4** |

Read as a spread, not an average:

| Configuration | Fastest | Slowest | Ratio |
|---|---:|---:|---:|
| 960×1024 @ 32 steps, RealVisXL, 5 runs | 42.3 s | 409.4 s | **9.7×** |
| 1344×768 @ 30 steps, 2 runs, different checkpoints | 90.8 s | 112.6 s | 1.24× |

**The 9.7× spread on an otherwise identical configuration is the single most
important operational number in this document.** It is not model behaviour, it is
not resolution, and it is not seed. It is contention with the other project on
this GPU (§11). Both 400-second runs are the second seed of a two-seed loop —
consistent with another project's job landing in the queue mid-loop.

Useful planning figures, all INFERRED from the above:

| Figure | Value | Reasoning |
|---|---|---|
| Uncontended cost, ~1 Mpx SDXL, 30–32 steps | 90–120 s | four of seven runs cluster here |
| Best observed | 42 s | one run only; do not plan on it |
| Contended cost | 400 s+ | two runs; upper bound unknown |
| Planning figure per plate | **assume 400 s** | planning on 120 s means every contended run blows the estimate by 3× |

Do not compute a throughput number from these seven points and put it in a
schedule. Seven jobs across two configurations on a shared GPU is not a benchmark.

Compositing (exp004, exp005) is CPU-side PIL and carries no GPU cost; no timing
was recorded for it (NOT MEASURED, and low value).

---

## 9. Determinism — a correction to the exp006 record

EXP-006 re-ran `exp003_seed760201` with a byte-identical graph and the same seed
to decide whether golden-image regression testing is usable on this rig. Its
manifest records:

```
"deterministic": false
```

**That conclusion is wrong, and it is wrong in a way that would have cost us a
useful test method.** Verified during this audit:

| Check | Result | Grade |
|---|---|---|
| File SHA-256 identical | **No** — `8913bc12…` vs `06e7e65f…` | MEASURED |
| File size | 1 606 293 B vs 1 606 298 B (+5 B) | MEASURED |
| **Decoded RGB pixel data identical** | **Yes — 0 of 983 040 pixels differ, max channel delta 0** | MEASURED |
| Cause of the 5-byte difference | the embedded `prompt` PNG text chunk: `filename_prefix` was `bananalab/exp003_760201` vs `bananalab/exp006_determinism` — 5 characters longer. Every other graph field is identical. | MEASURED |

**Generation on this rig is pixel-deterministic for a fixed graph and seed.** The
exp006 script hashed the PNG container, which carries the submitted graph as
metadata, including the output filename — so the hash could never have matched.

Consequences:

1. **Golden-image regression testing is viable here**, provided the hash is taken
   over decoded pixel data (`Image.open(p).convert("RGB").tobytes()`), never over
   the PNG file.
2. `workflows/comfyui/experiments/_run_exp006.py` should be corrected, and its
   manifest's `deterministic: false` should be treated as a known-bad record
   until it is.
3. `comfy_client.sha256_of` hashes file bytes. That is correct for its actual
   purpose — provenance and tamper detection on the delivered artefact — and it
   should stay. A separate pixel-level hash is needed for reproducibility checks.

Scope limit: one repeat, one configuration, minutes apart, same process
lifetime. Determinism across a ComfyUI restart, a driver update or a different
resolution is **NOT MEASURED**.

`PANEL_PRODUCTION_LOOP_REPORT.md` does not mention EXP-006 at all — §3 describes
"Five iterations" and §6 lists `exp001…exp005`. The experiment directory,
manifest and script exist. That is an evidence-record gap, not a contradiction.

---

## 10. Resolution, batch size and stability

### Resolution actually executed

MEASURED. Every latent size ever sampled on this instance:

| Size | Pixels | Jobs | Source |
|---|---:|---:|---|
| 1024×1024 | 1 048 576 | 143 | history summary |
| 1344×768 | 1 032 192 | 143 | history summary |
| 1216×832 | 1 011 712 | 49 | history summary — the legacy Issue 001 run |
| 960×1024 | 983 040 | 5 | our exp002/003/006 manifests |

The history snapshot contains no 960×1024 entries, so it was captured before
exp002 and does not cover our last five jobs. Whether it already includes the two
1344×768 exp001 jobs cannot be determined from the summary (INFERRED). Total
distinct jobs on this instance is therefore 342 or 344, not exactly one of them.

**Nothing above 1 048 576 pixels has ever been generated on this machine.** The
entire measured envelope sits within a 6.7 % band around 1 Mpx — the standard
SDXL bucket range and nothing more.

### Maximum stable resolution — INFERRED

The earlier audit estimates ~1536×1536 or ~1920×1080. Restating the reasoning so
it can be judged:

- 17.2 GB VRAM is generous for SDXL inference; the weights are a small part of it.
- `--use-split-cross-attention` chunks the attention computation, which is
  precisely the term that grows worst with pixel count. It lowers the peak at a
  throughput cost.
- `--disable-smart-memory` makes ComfyUI evict models rather than hold them
  resident, further lowering the steady-state peak, again at a time cost.
- 137.4 GB of system RAM means eviction has somewhere to go.

On those grounds 1536×1536 (2 359 296 px) is plausible. **But it is 2.25× the
largest job ever executed here, the inference carries no ZLUDA-specific
evidence, and the memory peak at high resolution is usually VAE decode rather
than sampling** — a tiled-decode fallback exists in stock ComfyUI but was not
verified as registered on this instance.

**Recommendation: measure a resolution ladder before any commitment.** Single
jobs at 1152×1152, 1344×1344, 1536×1536, 1920×1088, recording success, seconds
and peak VRAM from `/system_stats`. That is four jobs and it converts the single
largest planning unknown into a fact. It has not been run.

Print context, for scale of the problem: a 300 dpi A4 page is 2480×3508
(8 699 840 px) — **8.3× the largest job ever run here**, with no upscale model
installed.

### The panel is a resample, not a render

MEASURED, `app/services/compositor.py:377`:

```python
canvas = canvas.resize(output_size, Image.LANCZOS)
```

`ISSUE001-P16-02` is 1534×1642. The plate under it is 960×1024. The delivered
panel is therefore a **~1.6× LANCZOS enlargement** of a 1 Mpx plate, produced on
CPU, with no diffusion upscaler anywhere in the chain because none is installed.

That is acceptable for a candidate. It should not be assumed acceptable at print
size, and it has not been assessed against `docs/quality/QUALITY_STANDARD.md`.

### Batch size — NOT MEASURED

Every graph ever submitted, ours and the legacy ones, sets `batch_size: 1`
(`app/services/workflows.py`, all three builders). No batched job has ever run on
this instance.

**There is no stable batch size figure and I am not going to invent one.** The
only defensible statement is: batch 1 works, and it is the only value with
evidence.

### Crash and hang behaviour — NOT MEASURED

| Claim in circulation | Evidence here |
|---|---|
| "ZLUDA has a documented hang history on this rig" | Inherited from the source project's records. **No hang, crash, OOM or error status appears in any retained artefact on this instance.** 337 history jobs: all `status: success`. Our 7 jobs: all `ok: true`, all `error: ""`. |
| "One run timed out at 10 minutes" (`PANEL_PRODUCTION_LOOP_REPORT.md` §8) | **Not reproducible from retained artefacts.** No manifest records a timeout; every retained manifest is `ok: true`. The retained scripts use `timeout=1800`, and the client default is `900` — neither is 600 s. The exp002 run script was not retained, so a timed-out attempt may have occurred and been re-run without leaving a record. Treat as unverified. |

The honest position: **the failure envelope of this machine is unknown because
nothing has stressed it.** ~343 jobs of a 7-node text-to-image graph at 1 Mpx and
batch 1 is the narrowest possible workload. Every hard operation in the
production plan — ControlNet, IP-Adapter, CLIP Vision, inpainting, RemBG,
multi-model graphs, higher resolution — is unexercised. A clean record over a
trivial workload is not evidence of stability under a hard one.

The existing mitigations stand and should stay: resumable job manifests, no
unattended batch larger than one page, every job independently re-runnable from
saved configuration.

---

## 11. The shared instance

**This ComfyUI is not ours.** An unrelated project, prefix `signal-notes/hero`,
generates on the same GPU and interleaves with our jobs in the same queue.

| Fact | Value | Grade |
|---|---|---|
| History entries belonging to `signal-notes/hero` | **286 of 337 (84.9 %)** | MEASURED |
| Their configuration | `RealVisXL_V4.0`, `dpmpp_2m`/`karras`, 28 steps, cfg 5.5, 1344×768 and 1024×1024 | MEASURED |
| Observed effect on our wall-clock | **42.3 s → 409.4 s on identical work** | MEASURED |
| Their schedule | unknown | NOT MEASURED |
| Any coordination mechanism | none exists | MEASURED (nothing in the codebase reads or respects the queue) |

Note the collision risk in their configuration: they use the same checkpoint and
the same output root we do. Ours are namespaced by `filename_prefix`
(`bananalab/…`) and theirs by `signal-notes/hero`, which is the only thing
keeping the two apart.

### What this means for scheduling

1. **Never plan on uncontended timings.** Budget 400 s per ~1 Mpx plate. The four
   fast runs are the exception, not the baseline.
2. **Never plan a long unattended batch.** Not because of ZLUDA — because a job
   that would take 2 minutes can take 7, and the client cannot tell you which is
   happening. The existing "no unattended batch larger than one page" rule is
   correct and this is a second, independent reason for it.
3. **Raise the client timeout deliberately.** The default 900 s is only 2.2×
   the slowest observed run. At higher resolution, with contention, that is not
   enough headroom. The retained scripts already override to 1800 s; that should
   become the default, not a per-script choice.
4. **Read `/queue` before submitting and while waiting.** It is the difference
   between "we are queued" and "we are hung", and we currently cannot tell. This
   is the highest-value small piece of unbuilt plumbing in the integration.
5. **Never call `/interrupt` or clear the queue.** We would be cancelling someone
   else's work. Nothing in the codebase does this today and nothing should.
6. **Do not treat GPU access as exclusive when reasoning about VRAM.** The
   resolution ladder in §10 measures headroom *at that moment*, with whatever the
   other project has resident. A high-resolution job that succeeds uncontended may
   OOM contended. This is untested and is a genuine risk to the splash-page plan.
7. **Serialise our own submissions.** One job at a time from our side, always.
   We add nothing by competing with ourselves as well as with them.

---

## 12. Missing models and nodes

| Missing | Class | Impact | Grade |
|---|---|---|---|
| **Style LoRA** | model | No installed checkpoint produces the house style. The mitigation is the weighted style contract (exp003), which works but is prompt-level and fragile. | MEASURED — `loras: 0` |
| **Upscale model** | model | Cannot enlarge to print resolution. The current panel is a LANCZOS resample (§10). | MEASURED — `upscalers: 0` |
| `depth_anything_v2_vitl.pth` | auxiliary weights | `background_from_reference` cannot run without it. Hard-coded in `workflows.py:180`. | **Presence unverified** |
| RemBG / TransparentBG session weights | auxiliary weights | Class B alpha extraction cannot run. Blocks the Lil Devil layer set. | **Presence unverified** |
| Tiled VAE decode node | node | Likely the limiting factor at high resolution. | **Registration unverified** |
| Segmentation preprocessor | node | Named as a capability but no specific node was enumerated. | **NOT VERIFIED** |

No node required by any currently-built workflow is known to be missing. Every
node class in the three builders in `app/services/workflows.py` appears in the
capability matrix as registered — but see §7 on what "registered" is worth.

---

## 13. Open measurements, in priority order

Each of these is cheap and each converts a guess into a fact. None has been done.
**None of these should be run without checking GPU availability first** — see §11.

| # | Measurement | Cost | Removes |
|---|---|---|---|
| 1 | Confirm `depth_anything_v2_vitl.pth` and RemBG weights exist on disk | seconds, no GPU | two silent workflow failures |
| 2 | Dump the full `/object_info` probe to `workflows/comfyui/discovery/` | seconds, no GPU | the unretained-evidence gap in §7 |
| 3 | One ControlNet job and one IP-Adapter job, smallest viable | 2 jobs | the largest unknown in the whole plan |
| 4 | Resolution ladder: 1152², 1344², 1536², 1920×1088 | 4 jobs | the resolution guess in §10 |
| 5 | One `upload_image` + `LoadImage` round trip | 1 job | untested code on the reference path |
| 6 | Correct `_run_exp006.py` to hash pixels, re-record | no GPU | the wrong determinism record in §9 |
| 7 | Read `/queue` and log depth alongside each job's timing | no GPU | the queue-vs-hang blindness in §3 |
| 8 | One batch-2 job | 1 job | the batch-size unknown in §10 |

---

## 14. Summary

| Question | Answer | Grade |
|---|---|---|
| Is the instance healthy? | Yes, for the workload it has been given | MEASURED |
| Is that workload representative? | **No.** 7 node classes, 1 Mpx, batch 1, text-to-image only | MEASURED |
| Can it generate house-style plates? | Yes, with the weighted style contract | MEASURED (exp003) |
| Can it do identity preservation? | **Unknown — never attempted on this hardware** | NOT MEASURED |
| Is generation reproducible? | **Yes, pixel-exact**, within one session | MEASURED (§9, corrects exp006) |
| How long does a plate take? | 90–120 s uncontended, 400 s+ contended | MEASURED |
| How big can it go? | ~1 Mpx proven; 1536² plausible but untested | MEASURED / INFERRED |
| What batch size is safe? | Only 1 has evidence | NOT MEASURED |
| Will it crash? | Unknown. Nothing has stressed it. | NOT MEASURED |
| Do we control the GPU? | **No. 85 % of its recorded work is another project's.** | MEASURED |

Overall: **the environment is adequate and proven for background plate
generation, and entirely unproven for everything else the production plan
needs.**
