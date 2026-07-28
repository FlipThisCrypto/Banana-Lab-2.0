"""EXP-006: determinism check. Same seed, same graph, third run.

The brief warns against comparing exact pixels because generation may not be
deterministic across environments. This measures whether it is deterministic on
THIS environment, which decides whether golden-image regression is usable here.
"""
import sys, hashlib, json
sys.path.insert(0, ".")
from pathlib import Path
from app.adapters.comfy_client import ComfyClient, write_job_manifest, archive_graph
from app.services import workflows as wf

EXP = Path("workflows/comfyui/experiments/exp006-determinism")
PRIOR = Path("workflows/comfyui/experiments/exp003-weighted-style/exp003_seed760201.png")
prior_hash = hashlib.sha256(PRIOR.read_bytes()).hexdigest()

scene = ("narrow industrial service corridor at night in deep one-point perspective, "
         "pipework along the left wall, metal floor grating receding to a vanishing point, "
         "one red strip light on the ceiling midway down, "
         "cyan glow from a distant doorway at the far end, "
         "empty corridor, clear open floor in the foreground")
neg = "lockers, cabinets, doors along walls, clutter"

c = ComfyClient(timeout=1800)
g = wf.background_plate(prompt=scene, negative_extra=neg, width=960, height=1024,
                        seed=760201, steps=32, cfg=6.0,
                        filename_prefix="bananalab/exp006_determinism")
r = c.run(g, EXP, "exp006_seed760201_rerun")
archive_graph(g, EXP / "exp006_graph.json")
new_hash = hashlib.sha256(r.images[0].read_bytes()).hexdigest() if r.images else ""
write_job_manifest(EXP / "exp006_manifest.json", job_id="EXP006-determinism",
                   job_class="A", workflow_version=wf.WORKFLOW_VERSION, graph=g, result=r,
                   extra={"hypothesis": "identical seed + graph reproduces identical bytes",
                          "prior_sha256": prior_hash, "rerun_sha256": new_hash,
                          "deterministic": prior_hash == new_hash})
print(f"prior  {prior_hash[:24]}")
print(f"rerun  {new_hash[:24]}")
print(f"DETERMINISTIC: {prior_hash == new_hash}")
