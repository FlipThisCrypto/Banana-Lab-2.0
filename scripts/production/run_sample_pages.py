"""Sample run: generate plates, composite the cast, lay out pages, export a PDF.

This is the first end-to-end run of the pipeline on real script data. It is a
SAMPLE: everything it writes is a candidate. Nothing is approved, nothing is
promoted, and the approval record is not touched (ADR-005).

    python scripts/production/run_sample_pages.py --pages 1 2 --cover --pdf

What it does, per requested page:

  1. Derives a plate spec for every panel from `03_script/panel-script.yaml`
     and `05_layouts/layout-spec.yaml`. The plate is generated at the panel's
     ACTUAL aspect ratio, never a standard bucket - exp007 established that
     bucket-and-crop loses composition built for different proportions.
  2. Generates the plate through the locked background_plate workflow, so the
     style contract cannot be omitted, and writes a job manifest with prompt,
     seed, sampler, model and both output hashes.
  3. Composites approved character layers onto the plate, measuring likeness
     AND scene integration for every placement.
  4. Assembles the page at print geometry from the layout spec, with the page's
     declared frame colour and gutters.
  5. Optionally exports the assembled pages as a PDF.

Ground planes for the festival locations are ESTIMATED - see GROUND_ESTIMATES.
No festival plate calibration exists in approved canon, and this run does not
invent one; the estimate is recorded per panel in the run report so a later
calibration pass can supersede it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

sys.path.insert(0, ".")

from app.adapters.comfy_client import (  # noqa: E402
    ComfyClient, write_job_manifest,
)
from app.core import paths  # noqa: E402
from app.services import workflows as wf  # noqa: E402
from app.services.compositor import (  # noqa: E402
    GroundPlane, LightContract, Placement, composite_panel,
)
from app.services.lettering import Balloon, draw_balloon, draw_sfx  # noqa: E402
from app.services.plate_finish import finish_plate  # noqa: E402
from app.services.plate_calibration import (  # noqa: E402
    build_calibration,
    ground_from_calibration,
    load_calibration,
    write_calibration,
)

ISSUE = Path("issues/issue-001-neonblue-the-last-light-of-summer")
LAYERS = Path("source_material/imported_canon/character_layers")
REPAIRED = Path("characters/working/repaired_layers")
#: Layers cut from approved pose sheets by scripts/production/cut_character_layers.py
#: for characters who had no true-alpha set in imported canon.
DERIVED = Path("characters/working/derived_layers")

OUT_PLATES = ISSUE / "06_backgrounds" / "generated_candidates"
OUT_MANIFESTS = ISSUE / "06_backgrounds" / "metadata"
OUT_PROMPTS = ISSUE / "06_backgrounds" / "prompts"
OUT_COMPOSITES = ISSUE / "09_composites" / "generated_candidates"
OUT_PAGES = ISSUE / "09_composites" / "sample_pages"
OUT_EXPORT = ISSUE / "14_exports" / "sample"

WORKFLOW_VERSION = "sample-pages-1"

#: Character id -> approved layer folder. Taken from the character bibles.
CHARACTERS = {
    "MZ-CHAR-001": "moodz",
    "MZ-CHAR-002": "twotone",
    "MZ-CHAR-003": "static",
    "MZ-CHAR-004": "ash",
    "MZ-CHAR-005": "neonblue",
    "MZ-CHAR-006": "scarline",
    # Cut from approved pose sheets; imported canon has no alpha set for him.
    "MZ-CHAR-LILDEVIL": "lildevil",
}

#: Characters named in the script with no approved alpha layers. Recorded and
#: skipped - never substituted with someone else's art. Lil Devil was the only
#: entry until his 31 layers were cut from the approved sheets.
NO_LAYERS: dict[str, str] = {}

#: Ground-plane ESTIMATES, as a fraction of plate height, per camera shot.
#: (horizon, foot line for a character standing at mid-depth, character height)
#:
#: These are not calibrations. No festival plate calibration exists in approved
#: canon, and the four that do exist are for corridor/transit locations. Every
#: panel records which estimate it used so a real calibration pass can replace
#: it. Values follow the pattern of the approved calibrations: horizon above the
#: standing foot line, character height a modest fraction of frame.
GROUND_ESTIMATES = {
    "extreme_wide":  (0.46, 0.95, 0.16),
    "wide":          (0.44, 0.96, 0.30),
    "medium_wide":   (0.42, 0.97, 0.42),
    "medium":        (0.40, 0.99, 0.62),
    "medium_close":  (0.36, 1.06, 0.95),
    "close":         (0.30, 1.20, 1.45),
}

#: Shots where the reader is asked to recognise the character. Anything wider is
#: staged as background presence, and the legibility floor is waived per
#: placement and recorded. Derived from the shot the SCRIPT declares, not chosen
#: to make the gate pass - see LIKENESS_TUNING_REPORT.md ruling R-01.
IDENTITY_SHOTS = {"medium", "medium_close", "close"}

#: SDXL works best near 1 megapixel. Plates are generated at the panel's exact
#: aspect near this budget, then upscaled to print size. Generating at
#: 2480 px wide directly is far outside the model's trained range.
GEN_PIXEL_BUDGET = 1_150_000


def _round8(value: float) -> int:
    return max(256, int(round(value / 8.0)) * 8)


def gen_size(width: int, height: int) -> tuple[int, int]:
    """The generation size at the panel's exact aspect, near the pixel budget."""
    aspect = width / height
    gen_h = (GEN_PIXEL_BUDGET / aspect) ** 0.5
    return _round8(gen_h * aspect), _round8(gen_h)


#: What each script location actually looks like, so a short panel description
#: still lands somewhere real.
#:
#: The first run omitted this and it was the single worst defect: panels whose
#: background_description is one defocus phrase ("Defocused stall lights
#: behind", 30 characters) gave the model nothing to hold onto and it drifted
#: to generic scenes - a bookshop interior, two crowds of uniformed men, a
#: greyscale city street. Six of eleven plates were off-brief. The location was
#: in the script the whole time and simply was not being sent.
#: Deliberately SHORT. Three elements, not eight.
#:
#: The previous version was a shopping list - stalls, awnings, bulbs, bunting,
#: rides, a ferris wheel, grass and a crowd, eight object classes in one prompt -
#: and the model dutifully drew all eight, every time, across the whole frame.
#: That is why hairline_ink_density sat at 13-17 against an 11.0 ceiling and why
#: peak_over_field would not rise: saturation spread evenly over a busy frame
#: gives a high smoothed field median and no focal accent.
#:
#: The published plates carry two or three elements. So do these.
LOCATION_ANCHORS = {
    "LOC-festival-grounds": (
        "a summer funfair at dusk, one ferris wheel silhouette against the sky, "
        "two or three stall canopies, wide open trodden ground"
    ),
    "LOC-festival-main-stage": (
        "one dark stage silhouette against a lit sky, open ground in front"
    ),
}

#: The same locations described for a TIGHT shot: a couple of nearby elements,
#: not the whole site.
#:
#: The full anchor above lists rows of stalls, a ferris wheel and a crowd, which
#: on a close shot fights the framing and wins - it is why every close and
#: medium_close panel came back as another aerial fairground even after the shot
#: term was moved to the front at weight 1.4. A close shot needs to know it is at
#: a festival, not to be handed the festival.
NEAR_ANCHORS = {
    "LOC-festival-grounds": (
        # Iteration 2's near-anchor said "one striped stall awning" and produced
        # a cafe storefront, a cocktail bar and a treeline - generic premises,
        # because nothing in it said FAIRGROUND. It does now, twice, and names
        # only two things so the frame stays empty enough for a figure.
        "at a night funfair, one striped stall canopy edge and a few round "
        "glowing bulbs, nothing else"
    ),
    "LOC-festival-main-stage": (
        "one truss upright and a wash of stage light, everything else dark"
    ),
}

#: Shots that get NEAR_ANCHORS instead of the full site.
TIGHT_SHOTS = {"medium", "medium_close", "close"}

#: Below this, a description is too thin to anchor an image on its own and the
#: location anchor is added. Measured against the failures above: the panels
#: that drifted had 30-79 characters.
THIN_DESCRIPTION = 110

#: What each shot type means as framing, since "close shot" alone does not stop
#: SDXL producing an establishing view. Every page-2 close and medium_close
#: panel came back aerial before this existed.
SHOT_FRAMING = {
    "extreme_wide": "the whole location seen from far back, figures tiny",
    "wide": "the full setting, plenty of headroom and floor visible",
    "medium_wide": "waist-up framing distance, setting still readable behind",
    "medium": "the immediate surroundings only, background simplified",
    "medium_close": "very close to the subject, background reduced to a few "
                    "soft shapes, almost no detail behind",
    "close": "extremely tight framing, background almost entirely out of focus, "
             "one or two large soft colour shapes only, no scenery",
}

#: A background whose job is to POINT AT the character, not to be looked at.
#:
#: This is the mechanism the published editions use and this pipeline was
#: missing entirely. TheFusionSquad page 7 is the clearest case: a single green
#: field, brightest directly behind the figure, radial streaks converging on it,
#: three or four hue families, a handful of large simple shapes, and no detailed
#: scenery anywhere. The character reads instantly because the background is
#: built to make it read.
#:
#: The plates this pipeline produced were the opposite - detailed aerial
#: fairground wimmelbild with no focal point at all, which is simultaneously why
#: share_in_large_shapes measured 0.115 against a 0.26 floor, why
#: hairline_ink_density measured 18.8 against an 11.0 ceiling, why
#: n_hue_families measured 6.4 against 5.5, and why every figure looked tiny: an
#: aerial view has nowhere to put a large character.
FOCAL_BACKGROUND = (
    # Iteration 2 asked for a vignette and got evenly-lit daylight:
    # peak_over_field went the WRONG way, 41.0 -> 37.1 against a 42.6 floor.
    # The light has to be stated as the subject, not as an adjective.
    "(dramatic single source lighting:1.45), "
    "(bright glow behind the centre of frame:1.4), "
    "(deep black shadow in all four corners:1.35), (strong vignette:1.3), "
    # hairline_ink_density 13.0 against an 11.0 ceiling, n_hue_families 5.9
    # against 5.5: still too many small things and too many hues.
    "(only three colours:1.4), (very few objects:1.35), "
    "(large simple flat shapes:1.35), "
    "(hard edged flat colour, no gradients, no airbrush:1.35), "
    "(seen from standing eye level:1.25), "
    "a clear open ground plane in the lower third, generous empty space in the "
    "middle of frame for a figure to stand in"
)

#: Things the published editions never do, and every failed plate did.
FOCAL_NEGATIVE = (
    "aerial view, bird's eye view, isometric, top-down, map view, "
    "crowd of detailed people, hundreds of small figures, busy, cluttered, "
    "wimmelbild, densely packed stalls, repeated small objects, "
    "fine intricate detail, tiny text, signage lettering, "
    "flat evenly-lit scene, no focal point, evenly lit, bright daylight, "
    "many small objects, repeated detail, surface texture, "
    # Asking for simplicity without these produced a soft airbrushed field with
    # no outlines at all - simple, but not the house style. The published art is
    # simple AND hard-edged: flat fills inside black linework.
    "airbrushed, soft gradient, painterly, oil painting, watercolour, "
    "blurry, out of focus photography, photographic bokeh, hazy, misty, "
    "soft focus, feathered edges, no linework"
)

#: Target character height as a share of PANEL height, per declared shot.
#:
#: Owner brief: characters should occupy 25-70% of the panel depending on the
#: shot, never tiny figures pasted into enormous environments. Measured against
#: the published editions, which sit in the same band. This replaces deriving
#: height purely from an uncalibrated ground plane, which produced 68-231 px
#: figures on 3508 px pages - 2 to 7%.
#:
#: The ground plane still decides WHERE the feet go and how depth ranks the
#: cast; this decides HOW BIG they are once placed.
CHARACTER_SHARE = {
    "extreme_wide": 0.26,
    "wide": 0.34,
    "medium_wide": 0.45,
    "medium": 0.58,
    "medium_close": 0.68,
    "close": 0.70,
}

#: How much smaller the furthest figure is than the nearest, as a multiplier on
#: CHARACTER_SHARE. Keeps real depth separation without returning anyone to the
#: 2-7% band - the deepest figure in a six-up still clears the 25% floor.
DEPTH_FALLOFF = 0.74


def plate_prompt(panel: dict) -> str:
    """The scene description, assembled from the script rather than invented.

    The style contract is added by workflows.background_plate, which is why
    nothing here restates it.
    """
    light = panel.get("lighting") or {}
    description = panel["background_description"].strip().rstrip(".")
    if panel["camera_shot"] in TIGHT_SHOTS:
        anchor = NEAR_ANCHORS.get(panel["location"], "")
    else:
        anchor = LOCATION_ANCHORS.get(panel["location"], "")
    shot = panel["camera_shot"].replace("_", " ")
    angle = panel.get("camera_angle", "eye level").replace("_", " ")

    # The shot goes FIRST and weighted. It used to be appended last, after a
    # long location paragraph, and was simply ignored: P02-03's prompt ended
    # "close shot, eye level" and came back as another aerial establishing shot,
    # as did every other close and medium_close panel on page 2. Framing is the
    # first thing a reader sees, so it is the first thing the model is told.
    parts = [f"({shot} shot:1.4), ({angle}:1.2)"]
    parts.append(SHOT_FRAMING.get(panel["camera_shot"], ""))

    interior = any(
        token in description.lower()
        for token in ("interior", "inside", "counter", "corridor", "room", "booth")
    )
    if interior:
        # A location-wide "funfair + ferris wheel + open ground" anchor beats
        # "food stand interior" every time. P03-01 proved it twice.
        anchor = ""

    if anchor and len(description) < THIN_DESCRIPTION:
        # Anchor after the framing, so the setting fills in the shot rather than
        # replacing it. Whole-site language ahead of the shot term is what turned
        # every page-2 panel into an establishing view.
        parts.append(description)
        parts.append(f"setting: {anchor}")
    else:
        parts.append(description)
        if anchor:
            parts.append(f"setting: {anchor}")

    parts.append(f"depth: {panel['depth_plan'].strip().rstrip('.')}")
    parts.append(f"lit by {light.get('key_direction', 'ambient light')}, "
                 f"{light.get('key_color', 'neutral')} key")
    if light.get("fill"):
        parts.append(f"{light['fill']} fill")

    # Measured against the published editions: their panel art sits in LARGE
    # flat colour cells (share of art inside a cell >= 0.05 sq in: published
    # median 0.558, this pipeline 0.201 and 0.029) with far less fine linework
    # (hairline ink 2.65 published, 14.2 and 23.3 here) and fewer competing hues
    # (4 families published, 6.8 and 6.1 here). That is the real gap - not
    # saturation, which is already slightly BELOW published peak. So ask for
    # simplicity, and do not ask for less colour.
    # The script's background_description is art direction written for a human
    # artist. "Booth rows, bunting, dense warm crowd" tells an illustrator to
    # render a massed shape; handed verbatim to SDXL it draws every booth and
    # every person. The script's CONTENT is preserved - it is owner material -
    # and only its EXECUTION is directed here.
    parts.append(
        "(render crowds and rows of objects as large simple massed silhouette "
        "shapes:1.35), (not individual figures or individual objects:1.3)"
    )
    if interior or panel["camera_shot"] in TIGHT_SHOTS:
        # FOCAL_BACKGROUND demands an outdoor ground plane and empty mid-frame.
        # That turned P03-01 (food-stand interior, NeonBlue behind the counter)
        # into another sunset establishing shot with a figure pasted on the sky.
        parts.append(
            "(dramatic single source lighting:1.4), "
            "(hard edged flat colour, no gradients, no airbrush:1.35), "
            "(large simple flat shapes:1.3), (very few objects:1.25)"
        )
    else:
        parts.append(FOCAL_BACKGROUND)
    return ", ".join(p for p in parts if p)


def cover_prompt(cover: dict) -> str:
    """The cover plate: the environment only.

    The cast is composited from approved art, so the plate must not contain
    figures - background_plate's negative prompt already excludes characters.
    The title logo, tagline, stamp and spine text are LETTERING and belong to a
    later stage; this run leaves their space clear and does not fake them.
    """
    # Revision 2. Revision 1 said "deep dusk sky" and "the last of the sun" and
    # got a healthy golden-hour festival with every light working - a beautiful
    # plate for page 1 panel 1, and the opposite of the cover's brief, which is
    # the blackout. Sunset language is what did it, so all of it is gone and the
    # darkness is stated positively and repeatedly instead. Both revisions are
    # kept as candidates; neither is approved.
    return (
        "(night:1.4), (blacked out fairground:1.4), the festival grounds during "
        "a total power failure, seen wide and slightly low, ferris wheel and "
        "main stage as dark silhouettes against a starless deep blue night sky, "
        "every bulb dead and unlit, strings of dead bulbs hanging overhead, "
        "stalls and booths in cold blue shadow, "
        "(one single small warm lamp still burning at the centre of frame:1.4), "
        "a narrow pool of warm light on the ground beneath it, "
        "empty foreground path leading in toward that one light, "
        "depth: foreground path and dead bunting, midground darkened rides and "
        "stalls, background black skyline, "
        "lit only by that one small warm source at centre frame, deep amber key "
        "falling off fast into darkness, cold blue moonlight ambient fill, "
        "cover composition with clear central space for a figure and clear "
        "upper third of empty night sky for a title"
    )


@dataclass
class PanelResult:
    panel_id: str
    page: int
    print_size: tuple[int, int]
    gen_size: tuple[int, int]
    prompt: str
    seed: int
    plate: Path | None = None
    raw_plate: Path | None = None
    candidates: list[dict] = field(default_factory=list)
    composite: Path | None = None
    placements: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_characters: list[str] = field(default_factory=list)
    ground_estimate: str = ""
    seconds: float = 0.0
    error: str = ""


#: Words in a blocking `position` that place a figure across frame.
_X_WORDS = [
    (("far left", "left edge"), 0.16),
    (("left rear", "left of centre", "left"), 0.28),
    (("centre rear", "center rear", "centre", "center", "middle"), 0.50),
    (("right of centre", "right rear", "right"), 0.72),
    (("far right", "right edge"), 0.84),
]

#: Words that place a figure in depth. Lower is nearer the camera.
_DEPTH_WORDS = [
    (("foreground", "front of", "nearest", "closest"), 0.0),
    (("half a step behind", "just behind"), 0.30),
    (("centre rear", "center rear", "rear", "behind"), 0.62),
    (("rearmost", "trailing", "furthest", "background"), 0.85),
]


def blocking_for(panel: dict) -> dict[str, dict]:
    """The script's per-character staging direction, keyed by character id.

    `character_blocking` declares position, depth_plane, scale_note,
    ground_contact, eye_line and hand_activity for every figure in frame, and
    this pipeline ignored all of it - spreading the cast evenly across frame on
    a depth ladder of its own invention and picking `clean_base` for everyone.
    The script had already directed the shot; nothing was reading the direction.
    """
    out: dict[str, dict] = {}
    for record in panel.get("character_blocking") or []:
        cid = record.get("character_id")
        if not cid:
            continue
        position = (record.get("position") or "").lower()

        x = None
        for words, value in _X_WORDS:
            if any(w in position for w in words):
                x = value
                break

        depth = None
        for words, value in _DEPTH_WORDS:
            if any(w in position for w in words):
                depth = value
                break
        if depth is None:
            plane = (record.get("depth_plane") or "").lower()
            depth = {"foreground": 0.0, "midground": 0.45,
                     "background": 0.8}.get(plane)

        # "6 percent smaller" -> 0.94. Relative scale the script asked for.
        scale = 1.0
        note = (record.get("scale_note") or "").lower()
        match = re.search(r"(\d+)\s*percent\s*smaller", note)
        if match:
            scale = max(0.4, 1.0 - int(match.group(1)) / 100.0)

        out[cid] = {
            "x": x,
            "depth": depth,
            "scale": scale,
            "plane": (record.get("depth_plane") or "").lower(),
            "feet_in_frame": "out of frame" not in
                             (record.get("ground_contact") or "").lower(),
            "pose_words": " ".join([
                record.get("ground_contact") or "",
                record.get("hand_activity") or "",
                record.get("eye_line") or "",
            ]).lower(),
            "scale_note": note,
            "occlusion": (record.get("occlusion") or "").lower(),
            "position": position,
        }
    return out


def pick_layer(character_id: str, panel: dict,
               direction: dict | None = None) -> Path | None:
    """An approved layer for this character, matching the pose the script asks for.

    Prefers the repaired copy when one exists. Never falls back to a different
    character.

    The first version scored the pose name against the panel's prose beat and
    gave `clean_base` a bonus, so almost every figure on every page came out in
    the same neutral standing pose - six identical postures in a row on P01-02.
    The script had already said what each character is doing: `ground_contact`
    "Both feet mid-stride, weight forward", `hand_activity` "One hand near his
    ear", `eye_line` "Down at the ground". Those are matched here.
    """
    folder = CHARACTERS.get(character_id)
    if not folder:
        return None

    root = LAYERS if (LAYERS / folder).is_dir() else DERIVED
    available = sorted((root / folder).glob("*.png"))
    if not available:
        return None

    words = (direction or {}).get("pose_words", "")
    beat = " ".join([
        panel.get("visual_beat", ""), panel.get("narrative_purpose", ""),
        panel.get("mood", ""),
    ]).lower()

    # Pose name -> the blocking phrases that should select it.
    cues = {
        "walking": ("walking", "mid-stride", "stride", "unhurried", "slowest pace",
                    "pace"),
        "running": ("running", "run", "hurrying", "sprint"),
        "determined": ("weight forward", "braced", "planted", "determined",
                       "sets his", "squares"),
        "worried": ("worried", "hesitating", "uneasy", "anxious", "listening"),
        "sleepy": ("sleepy", "bored", "down at the ground", "slumped"),
        "confused": ("confused", "scanning", "looking about", "puzzled"),
        "laughing": ("laughing", "grinning", "delighted", "laugh"),
        "shocked": ("shocked", "startled", "recoils", "alarm"),
        "angry": ("angry", "furious", "glare", "snaps"),
        "pointing": ("pointing", "points", "one arm raised", "gestures"),
        "waving": ("waving", "waves"),
        "thinking": ("thinking", "considers", "near his ear", "hand to chin"),
        "armscrossed": ("arms crossed", "folded arms", "hands in pockets",
                        "neutral at sides", "hoodie pocket"),
        "lookingup": ("up and off", "looking up", "upward", "overhead"),
        "crouching": ("crouch", "one knee", "kneeling"),
        "jumping": ("jump", "airborne", "leaps"),
        "backview": ("from behind", "walking away", "back to camera"),
        "celebrating": ("celebrating", "cheering", "arms up"),
        "reaching": ("reaching", "reaches", "hand out"),
        "sitting": ("seated", "sitting", "sits"),
        "defeated": ("defeated", "slumped", "beaten"),
    }

    ranked = []
    for path in available:
        pose = path.stem.split("_", 2)[-1]
        score = 0
        # The script's explicit direction for THIS character carries the most.
        for cue in cues.get(pose, ()):
            if cue in words:
                score += 5
                break
        # Then the panel's own beat, which is about the moment not the figure.
        for cue in cues.get(pose, ()):
            if cue in beat:
                score += 2
                break
        if pose.replace("_", " ") in words:
            score += 4
        # clean_base is the fallback of last resort, not a preference.
        if pose == "clean_base":
            score += 1 if not words else 0
        ranked.append((score, path.name, path))
    ranked.sort(key=lambda r: (-r[0], r[1]))
    chosen = ranked[0][2]

    repaired = REPAIRED / folder / chosen.name
    return repaired if repaired.is_file() else chosen


def light_from_panel(panel: dict) -> tuple[LightContract, tuple[int, int, int]]:
    """A light contract for the compositor, from the script's lighting block."""
    light = panel.get("lighting") or {}
    text = f"{light.get('key_color','')} {light.get('key_direction','')}".lower()

    if "amber" in text or "warm" in text or "gold" in text:
        key, fill, spill = (255, 190, 120), (70, 55, 40), (120, 80, 45)
        angle = 20.0
    elif "magenta" in text or "cool white" in text or "cool" in text:
        key, fill, spill = (200, 210, 235), (50, 55, 75), (90, 95, 120)
        angle = 90.0
    else:
        key, fill, spill = (230, 220, 200), (60, 60, 60), (110, 105, 95)
        angle = 60.0

    direction = (light.get("key_direction") or "").lower()
    if "frame left" in direction:
        angle = 160.0
    elif "frame right" in direction:
        angle = 20.0
    elif "overhead" in direction or "above" in direction:
        angle = 90.0

    return LightContract(
        key_angle_deg=angle, key_color=key, fill_color=fill,
        key_strength=0.22, fill_strength=0.10, rim_strength=0.10,
        spill_strength=0.14, protect_neutrals=0.85,
    ), spill


def stage_panel(panel: dict, plate_path: Path, size: tuple[int, int],
                result: PanelResult, layout_panel: dict | None = None) -> Path | None:
    """Composite the panel's cast onto its plate and record every measurement."""
    shot = panel["camera_shot"]
    horizon_f, foot_f, height_f = GROUND_ESTIMATES.get(
        shot, GROUND_ESTIMATES["medium"])
    width, height = size
    measured = load_calibration(ISSUE, panel["panel_id"])
    if measured:
        gp = measured["ground_plane"]
        horizon_f = gp["horizon_fraction"]
        foot_f = gp["calib_foot_fraction"]
        height_f = gp["calib_height_fraction"]
        result.ground_estimate = (
            f"{shot}: horizon {horizon_f:.2f}H MEASURED from this plate "
            f"(was a shot-type guess)"
        )
        ground = ground_from_calibration(measured, size)
    else:
        result.ground_estimate = (
            f"{shot}: horizon {horizon_f:.2f}H, foot {foot_f:.2f}H, "
            f"character {height_f:.2f}H (ESTIMATE, no plate calibration yet)"
        )
        ground = GroundPlane(
            horizon_y=horizon_f * height,
            calib_foot_y=foot_f * height,
            calib_height_px=height_f * height,
        )

    present = [c for c in (panel.get("characters_present") or [])]
    for character_id in present:
        if character_id not in CHARACTERS:
            result.skipped_characters.append(
                f"{character_id} ({NO_LAYERS.get(character_id, 'unknown id')}) "
                f"- no approved alpha layers exist"
            )

    stageable = [c for c in present if c in CHARACTERS]
    if not stageable:
        return None

    light, spill = light_from_panel(panel)
    identity = shot in IDENTITY_SHOTS

    placements: list[Placement] = []
    slots = len(stageable)
    directed = blocking_for(panel)

    # The script already directs this shot. `character_blocking` gives every
    # figure a position, a depth plane, a relative scale and a ground contact,
    # and this pipeline used to ignore all of it: an even spread across frame on
    # a depth ladder of its own, and `clean_base` for everyone. Read the
    # direction; only fall back to the ladder where the script is silent.
    #
    # Depth ordering comes from the script's own words - "Front of the cluster",
    # "Half a step behind", "Centre rear", "Rearmost, trailing".
    ranked = sorted(range(slots),
                    key=lambda i: directed.get(stageable[i], {}).get("depth")
                    if directed.get(stageable[i], {}).get("depth") is not None
                    else 0.5)
    fallback_x = {}
    unplaced = [c for c in stageable if directed.get(c, {}).get("x") is None]
    for n, cid in enumerate(unplaced):
        fallback_x[cid] = (n + 1) / (len(unplaced) + 1)

    span = max(0.0, foot_f - horizon_f) * 0.62

    for index, character_id in enumerate(stageable):
        direction = directed.get(character_id, {})
        layer = pick_layer(character_id, panel, direction)
        if layer is None:
            result.skipped_characters.append(f"{character_id} - no layer found")
            continue

        # depth 0.0 is nearest the camera, so rung 1.0 is nearest.
        depth = direction.get("depth")
        if depth is None:
            depth = 0.5 if slots == 1 else ranked.index(index) / max(1, slots - 1)
        rung = 1.0 - depth
        if slots == 1:
            rung = 1.0

        waist_crop = any(
            token in f"{direction.get('scale_note','')} {direction.get('occlusion','')} {direction.get('position','')}"
            for token in (
                "chest height", "behind the counter", "lower body",
                "cropped at the waist", "waist",
            )
        )
        if waist_crop:
            direction["feet_in_frame"] = False

        foot = foot_f - span * (1.0 - rung)
        foot_y = int(height * min(0.995, foot))

        # Size to a share of PANEL height, then solve the multiplier that gets
        # there. Deriving height from the uncalibrated ground plane alone gave
        # 68-231 px figures on a 3508 px page; the owner brief and the published
        # editions both put a character at 25-70% of the panel.
        share = CHARACTER_SHARE.get(shot, 0.5)
        share *= DEPTH_FALLOFF + (1.0 - DEPTH_FALLOFF) * rung
        # The script's own relative scale, e.g. "20 percent smaller".
        share *= direction.get("scale", 1.0)
        # House style: 25-70% of panel. A medium_close must not become a
        # cropped giant; page 3 panel 3 rendered Lil Devil at 1271px in a
        # 968px plate.
        share = min(0.70, max(0.25, share))
        desired_h = share * height
        try:
            natural_h = ground.character_height_at(foot_y)
        except ValueError:
            natural_h = desired_h
        multiplier = desired_h / natural_h if natural_h > 0 else 1.0

        x_frac = direction.get("x")
        if x_frac is None:
            x_frac = fallback_x.get(character_id, (index + 1) / (slots + 1))

        plane = direction.get("plane") or (
            "midground" if rung > 0.34 else "background")

        # A figure the script says is cropped at the waist must not be given a
        # contact shadow on a ground line it never touches.
        feet_in_frame = direction.get("feet_in_frame", True)

        placements.append(Placement(
            character_id=character_id,
            layer_path=layer,
            centre_x=int(width * x_frac),
            foot_y=foot_y if feet_in_frame else int(height * 1.04),
            scale_multiplier=multiplier,
            depth_plane=plane,
            identity_critical=identity,
            notes=direction.get("pose_words", "")[:120],
        ))

    if not placements:
        return None

    panel_image, report = composite_panel(
        plate_path, ground, light, placements,
        bubble_zones=(layout_panel or {}).get("bubble_zones"),
    )
    result.placements = report.placements
    result.warnings.extend(report.warnings)

    OUT_COMPOSITES.mkdir(parents=True, exist_ok=True)
    out = OUT_COMPOSITES / f"{panel['panel_id']}_composite.png"
    paths.assert_safe_write_target(out)
    panel_image.convert("RGB").save(out)
    return out


#: How many takes to generate per panel before choosing one.
#:
#: Measured: the SAME prompt at four seeds gave hairline_ink_density 18.59,
#: 19.61, 25.11 and 33.86 - a spread of 15.27 with sd 6.05, on a property whose
#: whole tolerance band is 0.4 to 11.0. Every prompt A/B this pipeline ran on
#: single plates was smaller than that noise, and therefore meant nothing.
#:
#: Fighting the variance would need ~16 plates per arm to detect a 3-point
#: effect. Exploiting it is cheaper and is what a studio actually does: generate
#: several takes, keep the best one, and keep the rest as evidence. Every
#: candidate is written and recorded; nothing is hidden.
CANDIDATES_PER_PANEL = 3


def _score_candidate(path: Path) -> dict:
    """Aesthetic properties of one finished candidate."""
    import importlib.util

    global _SCORECARD
    if _SCORECARD is None:
        spec = importlib.util.spec_from_file_location(
            "asc", "scripts/validation/aesthetic_scorecard.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["asc"] = module
        spec.loader.exec_module(module)
        _SCORECARD = module

    import numpy as np
    with Image.open(path) as image:
        return _SCORECARD.score_page(np.asarray(image.convert("RGB")))


_SCORECARD = None

#: The tolerances a plate is judged against, mirroring the scorecard.
PLATE_TOLERANCES = {
    "share_in_large_shapes": (">=", 0.26, None),
    "hairline_ink_density": ("range", 0.4, 11.0),
    "peak_over_field": ("range", 42.6, 66.6),
    "n_hue_families": ("<=", 5.5, None),
}


def _outside(name: str, value: float) -> float:
    """How far outside its tolerance a property sits, 0 when inside."""
    if value is None:
        value = 0.0
    operator, low, high = PLATE_TOLERANCES[name]
    if operator == "<=":
        return max(0.0, value - low) / max(low, 1e-6)
    if operator == ">=":
        return max(0.0, low - value) / max(low, 1e-6)
    span = high - low
    return max(0.0, low - value, value - high) / max(span, 1e-6)


#: What makes one take better than another.
#:
#: The first version ranked on hairline then share, and it worked - hairline went
#: 12.81 -> 9.23 and finally passed. It also dragged peak_over_field 45.25 ->
#: 39.95 into failure, because a proxy was being optimised instead of the goal.
#: Ranking on the NUMBER of tolerances met, then on total distance outside them,
#: optimises what is actually wanted and cannot trade one property away to buy
#: another without that showing in the count.
#:
#: The guardrail stays first and absolute. It has already earned its place: on
#: P02-04 the lowest-hairline take measured C_p95 31.7 and was correctly passed
#: over for one at 60.1.
def _candidate_rank(scores: dict) -> tuple:
    guardrail_ok = scores.get("C_p95", 0.0) >= 50.0
    missed = sum(1 for k in PLATE_TOLERANCES
                 if _outside(k, scores.get(k, 0.0)) > 0)
    distance = sum(_outside(k, scores.get(k, 0.0)) for k in PLATE_TOLERANCES)
    return (0 if guardrail_ok else 1, missed, distance)


def generate_plate(client: ComfyClient, spec: PanelResult, job_class: str,
                   *, dry_run: bool) -> None:
    OUT_PLATES.mkdir(parents=True, exist_ok=True)
    OUT_PROMPTS.mkdir(parents=True, exist_ok=True)
    (OUT_PROMPTS / f"{spec.panel_id}.txt").write_text(spec.prompt, encoding="utf-8")

    if dry_run:
        return

    started = time.time()
    takes: list[tuple[tuple, Path, Path, dict, int]] = []
    outcome = None
    graph = None

    for index in range(CANDIDATES_PER_PANEL):
        seed = spec.seed + index * 7919
        graph = wf.background_plate(
            prompt=spec.prompt,
            negative_extra=FOCAL_NEGATIVE,
            width=spec.gen_size[0], height=spec.gen_size[1],
            seed=seed,
            filename_prefix=f"bananalab/sample/{spec.panel_id}",
        )
        result = client.run(graph, OUT_PLATES, f"{spec.panel_id}_take{index + 1}")
        if not result.ok:
            continue
        outcome = result
        raw = result.images[0]
        finished = raw.with_name(f"{raw.stem}_finished{raw.suffix}")
        paths.assert_safe_write_target(finished)
        finish_plate(raw).save(finished)
        scores = _score_candidate(finished)
        takes.append((_candidate_rank(scores), raw, finished, scores, seed))

    spec.seconds = time.time() - started
    if not takes:
        spec.error = "no candidate generated"
        return

    takes.sort(key=lambda t: t[0])
    _, best_raw, best_finished, best_scores, best_seed = takes[0]
    spec.candidates = [
        {"seed": s, "raw": r.as_posix(), "finished": f.as_posix(),
         **{k: round(sc.get(k) or 0.0, 3) for k in PLATE_TOLERANCES},
         "C_p95": round(sc.get("C_p95") or 0.0, 1),
         "chosen": f == best_finished}
        for _, r, f, sc, s in takes
    ]
    spec.seed = best_seed

    spec.plate = best_finished
    spec.raw_plate = best_raw
    try:
        with Image.open(best_finished) as measured_plate:
            calib = build_calibration(
                best_finished, measured_plate.convert("RGB"),
                panel_id=spec.panel_id,
            )
        dest = write_calibration(ISSUE, calib)
        spec.ground_estimate = (
            f"MEASURED horizon {calib['ground_plane']['horizon_fraction']:.3f}H "
            f"from {dest.name}"
        )
    except Exception as exc:  # measurement must not kill a successful plate
        spec.warnings.append(f"calibration measure failed: {exc}")
    write_job_manifest(
        OUT_MANIFESTS / f"{spec.panel_id}.job.json",
        job_id=spec.panel_id, job_class=job_class,
        workflow_version=WORKFLOW_VERSION, graph=graph, result=outcome,
        extra={
            "panel_id": spec.panel_id, "page": spec.page,
            "prompt": spec.prompt, "seed": spec.seed,
            "gen_size": list(spec.gen_size),
            "print_size": list(spec.print_size),
            "note": "SAMPLE RUN candidate. Not reviewed, not approved.",
        },
    )


def letter_panel(page: Image.Image, panel: dict, layout_panel: dict,
                 box: tuple[int, int, int, int]) -> float:
    """Balloons, captions and sound effects for one panel.

    Zones come from the layout spec, which already declares where a balloon may
    sit and whose it is. Text comes from the script. Neither is invented here.
    Returns the share of the panel the lettering covers, for the record.
    """
    x0, y0, pw, ph = box
    zones = layout_panel.get("bubble_zones") or []
    dialogue = list(panel.get("dialogue") or [])
    caption = panel.get("caption")
    covered = 0.0

    def to_page(zone):
        zx, zy, zw, zh = zone
        return (int(x0 + zx * pw), int(y0 + zy * ph),
                int(zw * pw), int(zh * ph))

    used = set()
    for entry in zones:
        target = entry.get("for", "")
        rect = to_page(entry["zone"])
        if target == "caption" and caption:
            draw_balloon(page, Balloon(text=caption, zone=rect, kind="caption"))
            covered += rect[2] * rect[3]
            caption = None
            continue
        # A zone declared for a character gets that character's line.
        line = next((d for d in dialogue
                     if (d.get("speaker") or d.get("character_id")) == target
                     and id(d) not in used), None)
        if line is None:
            continue
        used.add(id(line))
        draw_balloon(page, Balloon(
            text=line.get("text") or line.get("line") or "",
            zone=rect, speaker=target,
            # Point at the middle of the panel's lower half, where the figure
            # stands. Without per-figure positions to hand this is the honest
            # approximation, and it is better than no tail at all.
            tail_to=(x0 + pw // 2, y0 + int(ph * 0.62)),
        ))
        covered += rect[2] * rect[3]

    # A line the layout gave no zone to is still a line. Drop it into the upper
    # third rather than losing it silently.
    leftovers = [d for d in dialogue if id(d) not in used]
    for n, line in enumerate(leftovers[:2]):
        rect = (x0 + int(pw * (0.06 + 0.48 * n)), y0 + int(ph * 0.05),
                int(pw * 0.42), int(ph * 0.24))
        draw_balloon(page, Balloon(
            text=line.get("text") or "", zone=rect,
            speaker=line.get("speaker") or "",
            tail_to=(x0 + pw // 2, y0 + int(ph * 0.62)),
        ))
        covered += rect[2] * rect[3]

    for effect in (panel.get("sfx") or [])[:2]:
        text = effect if isinstance(effect, str) else effect.get("text", "")
        if not text:
            continue
        draw_sfx(page, text.upper(),
                 (x0 + int(pw * 0.24), y0 + int(ph * 0.78)),
                 max(28, int(ph * 0.17)))

    return covered / max(1, pw * ph)


def assemble_page(page_layout: dict, panels: dict[str, Path],
                  geometry: dict, page_ground: dict | None = None,
                  script_panels: dict[str, dict] | None = None) -> Image.Image:
    """Lay the panel art onto the page at print geometry.

    The published editions float their panels on a COLOURED BOARD behind a thin
    near-black rule. The layout spec says so - `page_ground.style` is
    `coloured_board_with_frame` and it declares `panel_border_color` #101014 -
    and the first version of this function inverted it: it painted the page
    white and used the board colour as a 10 px panel rule. Measured against the
    published pages, that put the rule at L* 71.9 / chroma 57.5 (exactly
    #E8A24A, page 1's declared board) where published rules sit at L* 2.2 /
    chroma 1.3, and the page ground at L* 100 where published boards sit at
    L* ~35. `panel_border_color` was in the spec, unused, the whole time.
    """
    width, height = geometry["print_pixels"]
    dpi = geometry["print_dpi"]
    gutter = int(geometry["gutter_mm"] / 25.4 * dpi)
    ground = page_ground or {}

    # frame_color is the BOARD the panels sit on, per page_ground.style.
    board = page_layout.get("frame_color", "#2A2A32")
    rule_color = ground.get("panel_border_color", "#101014")
    rule_mm = float(ground.get("panel_border_mm", 0.45))
    rule_px = max(1, round(rule_mm / 25.4 * dpi))

    # Panels float inset on the board rather than bleeding to trim. Published
    # median inset is 3.27% of page height at the top, 4.35% of width at the
    # left; the panel grid is scaled into that window.
    inset_x = int(width * float(ground.get("board_inset_x_pct", 4.35)) / 100.0)
    inset_y = int(height * float(ground.get("board_inset_y_pct", 3.27)) / 100.0)
    live_w, live_h = width - 2 * inset_x, height - 2 * inset_y

    page = Image.new("RGB", (width, height), board)
    draw = ImageDraw.Draw(page)

    for panel in page_layout["panels"]:
        box = panel["box"]
        x0 = inset_x + int(box[0] * live_w)
        y0 = inset_y + int(box[1] * live_h)
        pw, ph = int(box[2] * live_w), int(box[3] * live_h)
        # Inset by half a gutter so neighbouring panels sit a full gutter apart.
        half = gutter // 2
        x0, y0 = x0 + half, y0 + half
        pw, ph = max(1, pw - gutter), max(1, ph - gutter)

        art = panels.get(panel["panel_id"])
        if art and Path(art).is_file():
            with Image.open(art) as source:
                page.paste(source.convert("RGB").resize((pw, ph), Image.LANCZOS),
                           (x0, y0))
        else:
            draw.rectangle([x0, y0, x0 + pw, y0 + ph], fill="#EFEFEF")
            draw.text((x0 + 24, y0 + 24), f"{panel['panel_id']} - no art",
                      fill="#999999")

        draw.rectangle([x0, y0, x0 + pw, y0 + ph], outline=rule_color,
                       width=rule_px)

        source = (script_panels or {}).get(panel["panel_id"])
        if source:
            lettered = page.convert("RGBA")
            letter_panel(lettered, source, panel, (x0, y0, pw, ph))
            page = lettered.convert("RGB")
            draw = ImageDraw.Draw(page)

    return page


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, nargs="*", default=[1, 2])
    ap.add_argument("--panel-ids", nargs="*", default=[],
                    help="generate only these panel ids (still need --pages)")
    ap.add_argument("--cover", action="store_true")
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--seed", type=int, default=880101)
    ap.add_argument("--dry-run", action="store_true",
                    help="derive and print the specs without generating")
    args = ap.parse_args()

    script = yaml.safe_load((ISSUE / "03_script/panel-script.yaml")
                            .read_text(encoding="utf-8"))
    layout = yaml.safe_load((ISSUE / "05_layouts/layout-spec.yaml")
                            .read_text(encoding="utf-8"))
    geometry = layout["page"]
    page_width, page_height = geometry["print_pixels"]
    boxes = {p["panel_id"]: p for pg in layout["pages"] for p in pg["panels"]}
    by_page = {pg["page_number"]: pg for pg in layout["pages"]}

    client = ComfyClient(timeout=1800)
    if not args.dry_run and not client.reachable():
        print("ComfyUI is not reachable - start it, or use --dry-run",
              file=sys.stderr)
        return 2

    specs: list[PanelResult] = []

    if args.cover:
        # The cover is a full trim page, not a panel in the grid.
        gw, gh = gen_size(page_width, page_height)
        specs.append(PanelResult(
            panel_id="ISSUE001-COVER", page=0,
            print_size=(page_width, page_height), gen_size=(gw, gh),
            prompt=cover_prompt(layout["cover"]), seed=args.seed,
        ))

    for page_number in args.pages:
        for panel in [p for p in script["panels"]
                      if p["page_number"] == page_number]:
            if args.panel_ids and panel["panel_id"] not in args.panel_ids:
                continue
            box = boxes[panel["panel_id"]]["box"]
            pw = int(round(box[2] * page_width))
            ph = int(round(box[3] * page_height))
            gw, gh = gen_size(pw, ph)
            specs.append(PanelResult(
                panel_id=panel["panel_id"], page=page_number,
                print_size=(pw, ph), gen_size=(gw, gh),
                prompt=plate_prompt(panel),
                seed=args.seed + len(specs) * 101,
            ))

    print(f"{'panel':22s}{'print':>13s}{'generate':>13s}{'aspect':>8s}")
    for spec in specs:
        print(f"{spec.panel_id:22s}"
              f"{spec.print_size[0]:6d}x{spec.print_size[1]:<6d}"
              f"{spec.gen_size[0]:6d}x{spec.gen_size[1]:<6d}"
              f"{spec.print_size[0] / spec.print_size[1]:8.2f}")
    if args.dry_run:
        print("\n--dry-run: nothing generated")
        return 0

    script_by_id = {p["panel_id"]: p for p in script["panels"]}

    for spec in specs:
        job_class = "cover_plate" if spec.page == 0 else "background_plate"
        print(f"\n[{spec.panel_id}] generating {spec.gen_size[0]}x"
              f"{spec.gen_size[1]} ...", flush=True)
        generate_plate(client, spec, job_class, dry_run=False)
        if spec.error:
            print(f"  FAILED: {spec.error}")
            continue
        print(f"  plate: {spec.plate.name}  ({spec.seconds:.0f}s)")

        panel = script_by_id.get(spec.panel_id)
        if panel:
            composite = stage_panel(
                panel, spec.plate, spec.gen_size, spec, boxes.get(spec.panel_id)
            )
            if composite:
                spec.composite = composite
                for record in spec.placements:
                    print(f"    {record['character_id']:14s} "
                          f"h{record['rendered_height_px']:5d}  "
                          f"likeness {record['likeness_score']:5.1f} "
                          f"{'PASS' if record['likeness_passed'] else 'FAIL'}  "
                          f"integration {record.get('integration_score', 0):5.1f}")
                for skipped in spec.skipped_characters:
                    print(f"    SKIPPED {skipped}")

    art = {s.panel_id: (s.composite or s.plate) for s in specs if s.plate}
    # A one-panel rerun must not blank the rest of the page.
    for panel_id, box in boxes.items():
        if panel_id in art:
            continue
        existing = OUT_COMPOSITES / f"{panel_id}_composite.png"
        if not existing.is_file():
            existing = OUT_PLATES / f"{panel_id}_finished.png"
        if not existing.is_file():
            takes = sorted(OUT_PLATES.glob(f"{panel_id}_take*_finished.png"))
            existing = takes[-1] if takes else None
        if existing and existing.is_file():
            art[panel_id] = existing

    OUT_PAGES.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[str, Path]] = []

    cover_spec = next((s for s in specs if s.page == 0), None)
    if cover_spec and cover_spec.plate:
        out = OUT_PAGES / "page_00_cover.png"
        paths.assert_safe_write_target(out)
        with Image.open(cover_spec.plate) as source:
            source.convert("RGB").resize((page_width, page_height),
                                         Image.LANCZOS).save(out)
        rendered.append(("cover", out))

    for page_number in args.pages:
        if page_number not in by_page:
            continue
        page = assemble_page(by_page[page_number], art, geometry,
                             layout.get("page_ground"), script_by_id)
        out = OUT_PAGES / f"page_{page_number:02d}.png"
        paths.assert_safe_write_target(out)
        page.save(out)
        rendered.append((f"page {page_number}", out))
        print(f"\nassembled {out}")

    report = {
        "run": "sample-pages",
        "workflow_version": WORKFLOW_VERSION,
        "status": "CANDIDATE - not reviewed, not approved",
        "pages": args.pages,
        "cover": bool(args.cover),
        "panels": [
            {
                "panel_id": s.panel_id, "page": s.page,
                "print_size": list(s.print_size), "gen_size": list(s.gen_size),
                "seed": s.seed, "seconds": round(s.seconds, 1),
                "plate": s.plate.as_posix() if s.plate else None,
                "raw_plate": s.raw_plate.as_posix() if s.raw_plate else None,
                "candidates": s.candidates,
                "composite": s.composite.as_posix() if s.composite else None,
                "ground_plane_estimate": s.ground_estimate,
                "placements": s.placements,
                "warnings": s.warnings,
                "skipped_characters": s.skipped_characters,
                "error": s.error,
            }
            for s in specs
        ],
    }
    OUT_EXPORT.mkdir(parents=True, exist_ok=True)
    (OUT_EXPORT / "sample-run-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    if args.pdf and rendered:
        pdf = OUT_EXPORT / "issue-001-sample-cover-p1-p2.pdf"
        paths.assert_safe_write_target(pdf)
        images = []
        for _, path in rendered:
            with Image.open(path) as source:
                images.append(source.convert("RGB"))
        images[0].save(pdf, "PDF", resolution=geometry["print_dpi"],
                       save_all=True, append_images=images[1:])
        print(f"\nPDF: {pdf}  ({len(images)} pages)")

    failures = [s for s in specs if s.error]
    print(f"\n{len(specs) - len(failures)}/{len(specs)} plates generated")
    skipped = [x for s in specs for x in s.skipped_characters]
    if skipped:
        print(f"{len(skipped)} character placements skipped for missing art")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
