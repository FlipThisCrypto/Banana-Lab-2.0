import sys, json
sys.path.insert(0, ".")
from pathlib import Path
from app.adapters.comfy_client import ComfyClient, write_job_manifest, archive_graph
from app.services import workflows as wf

EXP = Path("workflows/comfyui/experiments/exp003-weighted-style")
c = ComfyClient(timeout=1800)

# Hypothesis: weighting the style tokens and restating them AFTER the scene
# prevents a long scene description from diluting them (the exp002 failure).
# Variable under test: style contract only. Scene, size, seed, steps, cfg fixed
# to exp002 values so the comparison is clean.
scene = ("narrow industrial service corridor at night in deep one-point perspective, "
         "pipework along the left wall, metal floor grating receding to a vanishing point, "
         "one red strip light on the ceiling midway down, "
         "cyan glow from a distant doorway at the far end, "
         "empty corridor, clear open floor in the foreground")
neg = "lockers, cabinets, doors along walls, clutter"

results = []
for seed in (760201, 760202):
    g = wf.background_plate(prompt=scene, negative_extra=neg, width=960, height=1024,
                           seed=seed, steps=32, cfg=6.0,
                           filename_prefix=f"bananalab/exp003_{seed}")
    r = c.run(g, EXP, f"exp003_seed{seed}")
    print(f"seed {seed}: ok={r.ok} {r.seconds:.0f}s {r.error[:120]}", flush=True)
    archive_graph(g, EXP / f"exp003_seed{seed}_graph.json")
    write_job_manifest(EXP / f"exp003_seed{seed}_manifest.json", job_id=f"EXP003-{seed}",
                       job_class="A", workflow_version=wf.WORKFLOW_VERSION, graph=g, result=r,
                       extra={"hypothesis": "weighted + suffixed style contract resists dilution",
                              "variable": "style contract (weights + suffix); scene/seed/size fixed vs exp002",
                              "compare_against": f"exp002_seed{seed}",
                              "panel_id": "ISSUE001-P16-02"})
    results.append(r.ok)
print("DONE", results, flush=True)
