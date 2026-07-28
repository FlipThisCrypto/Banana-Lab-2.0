"""Read-only adapter for a local ComfyUI instance.

Scope is deliberately narrow: discover what the machine can actually do. This
module never queues a job. Generation is added only after a controlled test
proves identity preservation and scene integration (see
`docs/workflows/COMFYUI_INTEGRATION_PLAN.md`), and it will live in a separate
module with its own job-manifest contract.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DEFAULT_HOST = "http://127.0.0.1:8188"
TIMEOUT = 30

#: Node types whose presence tells us a capability exists. Keys are the
#: capability names reported to the user.
CAPABILITY_NODES: dict[str, tuple[str, ...]] = {
    "controlnet": ("ControlNetLoader", "ControlNetApplyAdvanced"),
    "controlnet_union": ("SetUnionControlNetType",),
    "ipadapter": ("IPAdapterModelLoader", "IPAdapterAdvanced"),
    "ipadapter_faceid": ("IPAdapterFaceID",),
    "openpose_preprocessor": ("OpenposePreprocessor",),
    "depth_preprocessor": ("DepthAnythingV2Preprocessor", "MiDaS-DepthMapPreprocessor"),
    "canny_preprocessor": ("CannyEdgePreprocessor", "Canny"),
    "inpaint": ("VAEEncodeForInpaint", "InpaintModelConditioning"),
    "inpaint_preprocessor": ("InpaintPreprocessor",),
    "background_removal": ("RemBGSession+", "Image Rembg (Remove Background)"),
    "transparent_bg": ("TransparentBGSession+",),
    "mask_composite": ("ImageCompositeMasked", "LatentCompositeMasked"),
    "image_upscale_model": ("UpscaleModelLoader",),
    "clip_vision": ("CLIPVisionLoader",),
}


@dataclass
class ComfyReport:
    host: str
    reachable: bool
    error: str = ""
    version: str = ""
    devices: list[str] = field(default_factory=list)
    ram_total_gb: float = 0.0
    vram_total_gb: float = 0.0
    python_version: str = ""
    torch_version: str = ""
    argv: list[str] = field(default_factory=list)
    node_count: int = 0
    checkpoints: list[str] = field(default_factory=list)
    vaes: list[str] = field(default_factory=list)
    loras: list[str] = field(default_factory=list)
    controlnets: list[str] = field(default_factory=list)
    ipadapters: list[str] = field(default_factory=list)
    clip_visions: list[str] = field(default_factory=list)
    upscalers: list[str] = field(default_factory=list)
    unets: list[str] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            k: v for k, v in self.__dict__.items()
        }


def _get(host: str, path: str) -> dict:
    with urllib.request.urlopen(f"{host}{path}", timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _options(object_info: dict, node: str, input_name: str) -> list[str]:
    """Pull the option list for one node input, if the node exists."""
    spec = object_info.get(node)
    if not spec:
        return []
    for section in ("required", "optional"):
        entry = spec.get("input", {}).get(section, {}).get(input_name)
        if entry and isinstance(entry[0], list):
            return [str(v) for v in entry[0]]
    return []


def probe(host: str = DEFAULT_HOST) -> ComfyReport:
    """Query a running ComfyUI and describe what it can do."""
    report = ComfyReport(host=host, reachable=False)

    try:
        stats = _get(host, "/system_stats")
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        report.error = str(exc)
        return report

    report.reachable = True
    system = stats.get("system", {})
    report.version = system.get("comfyui_version", "unknown")
    report.python_version = system.get("python_version", "").split(" ")[0]
    report.torch_version = system.get("pytorch_version", "")
    report.argv = system.get("argv", [])
    report.ram_total_gb = round(system.get("ram_total", 0) / 1e9, 1)

    for device in stats.get("devices", []):
        report.devices.append(f"{device.get('name', '?')} ({device.get('type', '?')})")
        report.vram_total_gb = max(report.vram_total_gb, round(device.get("vram_total", 0) / 1e9, 1))

    try:
        object_info = _get(host, "/object_info")
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        report.error = f"system_stats ok but object_info failed: {exc}"
        return report

    report.node_count = len(object_info)
    report.checkpoints = _options(object_info, "CheckpointLoaderSimple", "ckpt_name")
    report.vaes = _options(object_info, "VAELoader", "vae_name")
    report.loras = _options(object_info, "LoraLoader", "lora_name")
    report.controlnets = _options(object_info, "ControlNetLoader", "control_net_name")
    report.ipadapters = _options(object_info, "IPAdapterModelLoader", "ipadapter_file")
    report.clip_visions = _options(object_info, "CLIPVisionLoader", "clip_name")
    report.upscalers = _options(object_info, "UpscaleModelLoader", "model_name")
    report.unets = _options(object_info, "UNETLoader", "unet_name")

    report.capabilities = {
        name: any(node in object_info for node in nodes)
        for name, nodes in CAPABILITY_NODES.items()
    }
    return report
