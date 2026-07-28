"""ComfyUI graph builders for each production stage.

Graphs are built in code rather than loaded from exported JSON because the
parameters that matter - seed, size, prompt, control strength - need to come
from the panel job, and hand-patching node IDs inside an exported blob is how
workflows silently drift.

Every builder returns a plain API-format graph. `workflows/comfyui/templates/`
holds a serialised copy of each for inspection and for import into the ComfyUI
editor.

Stage coverage:
    background_plate      Class A - place, no characters
    background_depth      Class A - new camera angle from an approved plate
    inpaint_repair        Class D - masked local repair
"""

from __future__ import annotations

WORKFLOW_VERSION = "panel-production-v1"

# Verified installed on this host. Never reference a model that is not here.
SDXL_CHECKPOINT = "RealVisXL_V4.0.safetensors"
ANIME_CHECKPOINT = "animagine-xl-4.0.safetensors"
SDXL_VAE = "sdxl_vae.safetensors"
CONTROLNET_UNION = "controlnet-union-sdxl-1.0-promax.safetensors"

# The style contract every background plate carries. Derived from
# canon/style/HOUSE_STYLE.md and the three published Fiend Studios editions.
#
# Emphasis weights and the trailing repeat are not decoration. Experiment 002
# proved the contract is positionally weak: a long scene description pushed the
# style tokens out of effect and RealVisXL reverted to photorealism even with
# "photorealistic" in the negative. Weighting the three load-bearing terms and
# restating the style after the scene fixed it (experiment 003).
STYLE_POSITIVE = (
    "(flat 2d vector cartoon illustration:1.5), "
    "(thick uniform black outlines:1.4), "
    "(flat colour fills with hard cel shading:1.4), "
    "comic book background art, graphic novel panel, bold saturated palette, "
    "clear perspective"
)

#: Restated after the scene description so length cannot dilute it.
STYLE_SUFFIX = (
    "(flat cartoon vector art:1.4), (bold black outlines:1.3), "
    "(cel shaded:1.3), non-photorealistic"
)

# Everything that has previously gone wrong, encoded once.
STYLE_NEGATIVE = (
    "(photorealistic:1.6), (photograph:1.6), (realistic lighting:1.4), "
    "(3d render:1.4), (volumetric light:1.3), (depth of field:1.3), "
    "cinematic photography, film still, octane render, unreal engine, "
    "realistic textures, reflections, bokeh, lens flare, "
    "characters, people, person, figure, animal, monkey, creature, mascot, "
    "text, letters, words, signature, watermark, logo, caption, speech bubble, "
    "panel border, frame, comic frame, white border, gutter, "
    "blurry, noisy, jpeg artifacts, low contrast mush, "
    "duplicated objects, warped architecture, broken geometry, extra limbs"
)


def _clip(node_id: str, text: str, clip_from: str) -> dict:
    return {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": text, "clip": [clip_from, 1]},
        "_meta": {"title": f"prompt-{node_id}"},
    }


def background_plate(
    *,
    prompt: str,
    negative_extra: str = "",
    width: int,
    height: int,
    seed: int,
    steps: int = 30,
    cfg: float = 6.0,
    sampler: str = "dpmpp_2m",
    scheduler: str = "karras",
    checkpoint: str = SDXL_CHECKPOINT,
    filename_prefix: str = "bananalab/bg",
) -> dict:
    """Class A: a frameless, characterless background plate.

    The style contract is prepended to the caller's scene description so no
    caller can accidentally omit it, and the negative prompt always excludes
    characters, text and panel borders.
    """
    positive = f"{STYLE_POSITIVE}. {prompt}. {STYLE_SUFFIX}"
    negative = STYLE_NEGATIVE + (f", {negative_extra}" if negative_extra else "")

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
            "_meta": {"title": "checkpoint"},
        },
        "2": _clip("2", positive, "1"),
        "3": _clip("3", negative, "1"),
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "_meta": {"title": "panel-size"},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
            "_meta": {"title": "sampler"},
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
            "_meta": {"title": "decode"},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["6", 0]},
            "_meta": {"title": "save"},
        },
    }


def background_from_reference(
    *,
    prompt: str,
    reference_image: str,
    negative_extra: str = "",
    width: int,
    height: int,
    seed: int,
    control_strength: float = 0.55,
    control_end: float = 0.75,
    steps: int = 30,
    cfg: float = 6.0,
    checkpoint: str = SDXL_CHECKPOINT,
    filename_prefix: str = "bananalab/bg_ref",
) -> dict:
    """Class A with depth control: a new camera angle on an established location.

    Depth is extracted from an approved plate and used as a ControlNet Union
    hint, so the new plate inherits the location's spatial structure rather than
    inventing a different place. `control_end` below 1.0 lets the sampler settle
    style in the late steps without the depth map fighting it.
    """
    positive = f"{STYLE_POSITIVE}. {prompt}. {STYLE_SUFFIX}"
    negative = STYLE_NEGATIVE + (f", {negative_extra}" if negative_extra else "")

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": _clip("2", positive, "1"),
        "3": _clip("3", negative, "1"),
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "8": {
            "class_type": "LoadImage",
            "inputs": {"image": reference_image, "upload": "image"},
            "_meta": {"title": "approved-plate"},
        },
        "9": {
            "class_type": "DepthAnythingV2Preprocessor",
            "inputs": {"ckpt_name": "depth_anything_v2_vitl.pth",
                       "resolution": 1024, "image": ["8", 0]},
            "_meta": {"title": "depth-from-plate"},
        },
        "10": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": CONTROLNET_UNION},
        },
        "11": {
            "class_type": "SetUnionControlNetType",
            "inputs": {"type": "depth", "control_net": ["10", 0]},
        },
        "12": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "strength": control_strength,
                "start_percent": 0.0,
                "end_percent": control_end,
                "positive": ["2", 0],
                "negative": ["3", 0],
                "control_net": ["11", 0],
                "image": ["9", 0],
                "vae": ["1", 2],
            },
            "_meta": {"title": "apply-depth"},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["12", 0],
                "negative": ["12", 1],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["6", 0]},
        },
    }


def inpaint_repair(
    *,
    prompt: str,
    image_name: str,
    mask_name: str,
    negative_extra: str = "",
    seed: int,
    denoise: float = 0.75,
    steps: int = 28,
    cfg: float = 6.0,
    checkpoint: str = SDXL_CHECKPOINT,
    filename_prefix: str = "bananalab/repair",
) -> dict:
    """Class D: regenerate only the masked region of an existing composite.

    Used for local defects. Everything outside the mask is preserved, so a bad
    hand does not cost the whole panel.
    """
    positive = f"{STYLE_POSITIVE}. {prompt}. {STYLE_SUFFIX}"
    negative = STYLE_NEGATIVE + (f", {negative_extra}" if negative_extra else "")

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": _clip("2", positive, "1"),
        "3": _clip("3", negative, "1"),
        "8": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name, "upload": "image"},
            "_meta": {"title": "panel-to-repair"},
        },
        "9": {
            "class_type": "LoadImageMask",
            "inputs": {"image": mask_name, "channel": "red", "upload": "image"},
            "_meta": {"title": "repair-mask"},
        },
        "10": {
            "class_type": "VAEEncodeForInpaint",
            "inputs": {
                "pixels": ["8", 0], "vae": ["1", 2], "mask": ["9", 0],
                "grow_mask_by": 8,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg,
                "sampler_name": "dpmpp_2m", "scheduler": "karras",
                "denoise": denoise,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["10", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["6", 0]},
        },
    }


BUILDERS = {
    "background_plate": background_plate,
    "background_from_reference": background_from_reference,
    "inpaint_repair": inpaint_repair,
}
