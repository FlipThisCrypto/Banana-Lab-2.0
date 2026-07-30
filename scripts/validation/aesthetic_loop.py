"""Sweep finishing parameters over cached plates and measure every result.

The aesthetic loop was costing ~10 minutes of GPU per iteration because every
change re-generated all 11 plates. Most of the remaining levers are FINISHING
parameters - palette size, vignette strength and centre, the ink threshold - and
those touch no model at all. This runs them over the cached raw plates, scores
each configuration against the published editions, and appends the result to a
ledger so iterations are comparable rather than remembered.

    python scripts/validation/aesthetic_loop.py --list
    python scripts/validation/aesthetic_loop.py --config it11 it12 it13
    python scripts/validation/aesthetic_loop.py --all

The ledger is `docs/audits/aesthetic-loop-ledger.json`. Every row records the
configuration, the measured properties, which tolerances passed, and whether the
C_p95 guardrail held - so a configuration that scores well by breaking the
guardrail is visible as such rather than looking like progress.

Pages are assembled from the cached raw plates WITHOUT characters, because the
properties being tuned here are properties of the plate and the page furniture.
Character staging is measured by the likeness gate, which is a separate
instrument and the hard constraint.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

sys.path.insert(0, ".")

from app.services import plate_finish  # noqa: E402

ISSUE = Path("issues/issue-001-neonblue-the-last-light-of-summer")
PLATES = ISSUE / "06_backgrounds" / "generated_candidates"
LEDGER = Path("docs/audits/aesthetic-loop-ledger.json")

#: Published targets and the tolerance each must satisfy. Lifted from
#: scripts/validation/aesthetic_scorecard.py so there is one source of truth for
#: what "matching" means.
TOLERANCES = {
    "rule_L": ("<=", 10.0, None),
    "rule_chroma": ("<=", 6.0, None),
    "ground_L": ("range", 20.0, 66.0),
    "lettering_pct": (">=", 2.0, None),
    "share_in_large_shapes": (">=", 0.26, None),
    "hairline_ink_density": ("range", 0.4, 11.0),
    "peak_over_field": ("range", 42.6, 66.6),
    "n_hue_families": ("<=", 5.5, None),
}
GUARDRAIL = ("C_p95", ">=", 50.0)


@dataclass
class Config:
    """One finishing configuration, and why it is being tried."""

    name: str
    rationale: str
    palette_size: int = 10
    vignette: float = 0.42
    vignette_centre: tuple[float, float] = (0.5, 0.46)
    chroma_gain: float = 0.40
    ink_l: float = 34.0


#: Each entry is one iteration of the loop. The rationale is the hypothesis; the
#: ledger records whether it held.
CONFIGS: list[Config] = [
    Config("it10-baseline", "the shipped configuration, for comparison"),
    Config("it11-palette6", "fewer cells should pull n_hue_families under 5.5",
           palette_size=6),
    Config("it12-palette4", "four cells is the published hue-family count",
           palette_size=4),
    Config("it13-chroma70", "peak_over_field is chroma contrast; push harder",
           chroma_gain=0.70),
    Config("it14-chroma100", "further still, watching the C_p95 guardrail",
           chroma_gain=1.00),
    Config("it15-vig60", "deeper corners raise the field/peak separation",
           vignette=0.60, chroma_gain=0.70),
    Config("it16-palette6-chroma70",
           "combine the two changes that worked alone",
           palette_size=6, chroma_gain=0.70),
    Config("it17-palette5-chroma85-vig55",
           "the best combination found, pushed one step",
           palette_size=5, chroma_gain=0.85, vignette=0.55),
    Config("it18-ink28", "a lower ink threshold posterises more of the plate, "
                         "which should cut hairline ink",
           palette_size=6, chroma_gain=0.70, ink_l=28.0),
    Config("it19-ink40", "a higher threshold protects more linework; does "
                         "hairline get worse, confirming the mechanism",
           palette_size=6, chroma_gain=0.70, ink_l=40.0),
    Config("it20-centre-low",
           "the figure stands in the lower half, so put the glow there",
           palette_size=6, chroma_gain=0.85, vignette=0.55,
           vignette_centre=(0.5, 0.58)),
]


def finish_with(path: Path, config: Config) -> Image.Image:
    """Apply one configuration, patching the module constants it reads."""
    original_ink = plate_finish.INK_L
    plate_finish.INK_L = config.ink_l
    try:
        with Image.open(path) as source:
            plate = source.convert("RGB")
        flat = plate_finish.posterise(plate, config.palette_size)
        return _vignette(flat, config)
    finally:
        plate_finish.INK_L = original_ink


def _vignette(image: Image.Image, config: Config) -> Image.Image:
    """focal_vignette with the configuration's gain and centre."""
    from app.services.likeness import lab_to_srgb_in_gamut, srgb_to_lab

    rgb = np.asarray(image.convert("RGB")).astype(np.float64)
    height, width = rgb.shape[:2]
    ys = (np.linspace(0.0, 1.0, height)[:, None] - config.vignette_centre[1]) / 0.5
    xs = (np.linspace(0.0, 1.0, width)[None, :] - config.vignette_centre[0]) / 0.5
    radius = np.sqrt(xs ** 2 + ys ** 2) / np.sqrt(2.0)
    field = np.cos(np.clip(radius, 0.0, 1.0) * np.pi)

    lab = srgb_to_lab(rgb)
    ink = lab[..., 0] < config.ink_l
    lab[..., 0] = np.clip(lab[..., 0] + field * config.vignette * 46.0, 0.0, 100.0)
    gain = 1.0 + field * config.chroma_gain
    lab[..., 1] *= gain
    lab[..., 2] *= gain
    out = lab_to_srgb_in_gamut(lab)
    out[ink] = rgb[ink]
    return Image.fromarray(out.astype(np.uint8), "RGB")


def passes(name: str, value: float) -> bool:
    operator, low, high = TOLERANCES[name]
    if operator == "<=":
        return value <= low
    if operator == ">=":
        return value >= low
    return low <= value <= high


def score_config(config: Config, scorecard, layout, script_panels,
                 assemble) -> dict:
    """Finish every plate under this configuration, assemble, and measure."""
    finished: dict[str, Path] = {}
    scratch = Path("characters/working/_loop") / config.name
    scratch.mkdir(parents=True, exist_ok=True)

    for page in layout["pages"][:2]:
        for panel in page["panels"]:
            raw = PLATES / f"{panel['panel_id']}.png"
            if not raw.is_file():
                continue
            out = scratch / f"{panel['panel_id']}.png"
            finish_with(raw, config).save(out)
            finished[panel["panel_id"]] = out

    values: dict[str, list[float]] = {}
    for page in layout["pages"][:2]:
        rendered = assemble(page, finished, layout["page"],
                            layout.get("page_ground"), script_panels)
        row = scorecard.score_page(np.asarray(rendered.convert("RGB")))
        for key, value in row.items():
            if isinstance(value, (int, float)):
                values.setdefault(key, []).append(float(value))

    measured = {k: round(float(np.median(v)), 3) for k, v in values.items()}
    verdicts = {k: passes(k, measured[k]) for k in TOLERANCES if k in measured}
    name, operator, threshold = GUARDRAIL
    held = measured.get(name, 0.0) >= threshold

    return {
        "config": asdict(config),
        "measured": measured,
        "verdicts": verdicts,
        "scored": sum(verdicts.values()),
        "of": len(TOLERANCES),
        "guardrail_held": held,
        "guardrail_value": measured.get(name),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for config in CONFIGS:
            print(f"  {config.name:26s} {config.rationale}")
        return 0

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "asc", "scripts/validation/aesthetic_scorecard.py")
    scorecard = importlib.util.module_from_spec(spec)
    sys.modules["asc"] = scorecard
    spec.loader.exec_module(scorecard)

    spec2 = importlib.util.spec_from_file_location(
        "rsp", "scripts/production/run_sample_pages.py")
    runner = importlib.util.module_from_spec(spec2)
    sys.modules["rsp"] = runner
    spec2.loader.exec_module(runner)

    layout = yaml.safe_load((ISSUE / "05_layouts/layout-spec.yaml")
                            .read_text(encoding="utf-8"))
    script = yaml.safe_load((ISSUE / "03_script/panel-script.yaml")
                            .read_text(encoding="utf-8"))
    script_panels = {p["panel_id"]: p for p in script["panels"]}

    wanted = CONFIGS if (args.all or not args.config) else [
        c for c in CONFIGS if c.name in args.config]

    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else []
    keys = list(TOLERANCES) + [GUARDRAIL[0]]

    header = f"{'config':26s}{'scored':>7s}" + "".join(
        f"{k[:11]:>12s}" for k in keys)
    print(header)
    for config in wanted:
        row = score_config(config, scorecard, layout, script_panels,
                           runner.assemble_page)
        ledger = [r for r in ledger if r["config"]["name"] != config.name]
        ledger.append(row)
        marks = "".join(
            f"{row['measured'].get(k, float('nan')):12.2f}" for k in keys)
        flag = "" if row["guardrail_held"] else "  GUARDRAIL BROKEN"
        print(f"{config.name:26s}{row['scored']:4d}/{row['of']:<2d}{marks}{flag}",
              flush=True)
        # Write after EVERY config, not at the end. The first long sweep was
        # reaped mid-run and lost nine measured configurations, because the
        # ledger was only flushed once at the end. An experiment ledger that can
        # lose experiments is not a ledger.
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    best = max((r for r in ledger if r["guardrail_held"]),
               key=lambda r: r["scored"], default=None)
    if best:
        print(f"\nbest with guardrail held: {best['config']['name']} "
              f"at {best['scored']}/{best['of']}")
        failing = [k for k, v in best["verdicts"].items() if not v]
        print(f"  still failing: {', '.join(failing) or 'nothing'}")
    print(f"ledger: {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
