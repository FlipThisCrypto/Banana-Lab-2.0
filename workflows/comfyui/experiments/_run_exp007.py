"""EXP-007: how do we produce an extreme-aspect letterbox panel?

ISSUE001-P18-01 is 2149x278 - a 7.73:1 letterbox. SDXL has no native bucket
anywhere near that. Two candidate strategies, one variable between them:

  A. Generate directly at an extreme ratio (1920x256, 7.5:1)
  B. Generate at a supported wide bucket (1536x640, 2.4:1) and crop the band

Hypothesis: A degrades badly because it is far outside SDXL's training
distribution; B is usable. If A works, it is simpler and preferred.
"""
import sys
sys.path.insert(0, ".")
from pathlib import Path
from app.adapters.comfy_client import ComfyClient, write_job_manifest, archive_graph
from app.services import workflows as wf

EXP = Path("workflows/comfyui/experiments/exp007-extreme-aspect")
c = ComfyClient(timeout=1800)

scene = ("wide establishing shot of a night festival main stage seen from far back "
         "across the crowd, stage structure and lighting rig on the horizon, "
         "dark crowd silhouettes filling the lower edge, night sky above")
neg = "close-up, portrait, tall composition"

variants = [
    ("A_direct_7500", dict(width=1920, height=256), "direct extreme 7.5:1"),
    ("B_bucket_crop", dict(width=1536, height=640), "supported 2.4:1, crop later"),
]
for tag, size, note in variants:
    g = wf.background_plate(prompt=scene, negative_extra=neg, seed=780101,
                            steps=30, cfg=6.0, filename_prefix=f"bananalab/exp007_{tag}", **size)
    r = c.run(g, EXP, f"exp007_{tag}")
    print(f"{tag:16s} {size['width']}x{size['height']} ok={r.ok} {r.seconds:.0f}s {r.error[:100]}", flush=True)
    archive_graph(g, EXP / f"exp007_{tag}_graph.json")
    write_job_manifest(EXP / f"exp007_{tag}_manifest.json", job_id=f"EXP007-{tag}",
                       job_class="A", workflow_version=wf.WORKFLOW_VERSION, graph=g, result=r,
                       extra={"hypothesis": "extreme aspect degrades; bucket+crop is the route",
                              "variable": f"generation size ({note})",
                              "target_panel": "ISSUE001-P18-01",
                              "target_px": [2149, 278], "target_aspect": 7.73})
print("DONE", flush=True)
