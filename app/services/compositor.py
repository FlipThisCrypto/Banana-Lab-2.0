"""Deterministic character-into-plate compositing.

This is the stage the previous system did not have. It pasted opaque reference
cards in a row; nothing here pastes. Every character is placed against a
declared ground plane at a computed scale, then given contact shadow, cast
shadow, environmental relight and colour spill derived from the plate's own
lighting contract.

No diffusion. Everything here is deterministic and reproducible from the
staging spec, which means a defect can be diagnosed rather than re-rolled.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from app.services.likeness import (
    LikenessResult, lab_to_srgb_in_gamut, measure, srgb_to_lab,
)


@dataclass
class GroundPlane:
    """Where the floor is, and how big things are on it.

    `horizon_y` and the calibration pair let character height be computed at any
    depth: an object of known height at a known screen position fixes the scale
    of the whole plane.
    """

    horizon_y: float
    calib_foot_y: float
    calib_height_px: float
    #: Real-world height of the calibration object, in character heights.
    calib_height_in_characters: float = 1.0

    def character_height_at(self, foot_y: float) -> float:
        """Screen height, in pixels, of one character standing with feet at foot_y.

        Under a pinhole camera on a flat plane, apparent height scales linearly
        with distance below the horizon.
        """
        calib_drop = self.calib_foot_y - self.horizon_y
        target_drop = foot_y - self.horizon_y
        if calib_drop <= 0 or target_drop <= 0:
            raise ValueError("feet must sit below the horizon")
        unit = self.calib_height_px / self.calib_height_in_characters
        return unit * (target_drop / calib_drop)


@dataclass
class LightContract:
    """The plate's lighting, as declared in the panel script."""

    #: Direction the key light travels, in degrees. 0 = from frame right,
    #: 90 = from directly above, 180 = from frame left.
    key_angle_deg: float
    key_color: tuple[int, int, int]
    key_strength: float = 0.55
    fill_color: tuple[int, int, int] = (40, 46, 60)
    fill_strength: float = 0.18
    rim_strength: float = 0.0
    #: How strongly bright near-neutral pixels resist the colour cast, 0-1.
    #:
    #: In cel art the whites and pale greys are graphic elements, not physical
    #: surfaces: they carry eye whites, face fills, under-eye bags, eye rings and
    #: stitched chest panels - identity-bearing features. Tinting them the way a
    #: real white wall would tint under coloured light is physically defensible
    #: and destroys likeness.
    #:
    #: Measured: at 0.0, the exp005 relight moved NeonBlue's #F0F0F0 to #C6E3E9
    #: (dE 12.2) and Moodz's #FCFCFC to #C8ECF3 (dE 14.8), failing the likeness
    #: gate at 90.7 and 93.2. See docs/audits/LIKENESS_TUNING_REPORT.md.
    protect_neutrals: float = 0.85
    #: How far a cast shadow stretches, as a multiple of character height.
    cast_length: float = 0.6
    cast_opacity: float = 0.42
    contact_opacity: float = 0.72
    spill_strength: float = 0.20
    ambient_lift: float = 0.0


@dataclass
class Placement:
    """One character's staging record, resolved to pixels."""

    character_id: str
    layer_path: Path
    #: Screen x of the character's centre line, in pixels.
    centre_x: int
    #: Screen y where the feet meet the ground, in pixels.
    foot_y: int
    depth_plane: str = "midground"
    #: Multiplier on the computed ground-plane height. 1.0 = standing adult.
    scale_multiplier: float = 1.0
    flip: bool = False
    #: Seated, crouched and airborne characters need their contact point moved.
    contact_offset: float = 0.0
    occluder: Path | None = None
    notes: str = ""
    #: Whether this character's identity has to READ in this panel.
    #:
    #: Default True: the character must be large enough for its small
    #: identifying features to survive print. Set False only for a figure that
    #: is deliberately background presence - a silhouette in a crowd, a distant
    #: passer-by - where the script does not ask the reader to recognise them.
    #:
    #: This exists because the approved plate calibrations frame chibi
    #: characters as WIDE shots. On school-pa-zone a character standing at the
    #: very bottom of frame is 167 px in an 832 px panel, and reaching the
    #: 320 px legibility floor would need foot_y = 1185 - off the bottom of the
    #: image. Ground-plane-correct staging on these plates CANNOT produce an
    #: identity-legible character, so the choice is tighter framing or an
    #: explicit, recorded decision that this figure is not identity-bearing.
    #:
    #: It is an opt-out, per placement, recorded in the composite report. It is
    #: not a way to turn the gate off, and colour identity is still measured.
    identity_critical: bool = True


DEPTH_BLUR = {"foreground": 0.0, "midground": 0.0, "background": 1.1}
DEPTH_HAZE = {"foreground": 0.0, "midground": 0.06, "background": 0.18}

#: Characters whose identity depends on a left/right asymmetry. Mirroring these
#: moves a canon feature to the wrong side, which is a canon violation, not a
#: staging choice. Caught in iteration 4: flipping Moodz put his blue accent and
#: fringe on the wrong eye.
NO_FLIP = {
    "MZ-CHAR-001": "black fringe over one eye, blue accent on the left",
    "MZ-CHAR-006": "scarlet streak on the viewer-left side",
    "MZ-CHAR-005": "left-ear silver plug earring",
    "MZ-CHAR-004": "stitched chest detail",
}

#: Below this scene-integration score a character barely responds to the panel's
#: light and starts to read as pasted on. A WARNING threshold, not a gate - see
#: app/services/integration.py for why this is reported rather than enforced.
CUTOUT_WARNING_SCORE = 25.0

#: Poses whose contact point is not the soles of the feet. Placing these with a
#: standing foot_y drops the character through the floor or floats them.
NON_STANDING_POSES = {
    "sitting": "seated - contact is the hips",
    "defeated": "slumped/seated - contact is the hips",
    "crouching": "crouched - contact is feet plus one hand",
    "jumping": "airborne - no ground contact",
    "running": "one foot contact, mid-stride",
}


def pose_slug(layer_path: Path) -> str:
    """`neonblue_27_defeated.png` -> `defeated`."""
    parts = Path(layer_path).stem.split("_", 2)
    return parts[-1] if parts else ""


def _load_rgba(path: Path) -> Image.Image:
    image = Image.open(path)
    return image.convert("RGBA")


def trim_alpha(image: Image.Image) -> Image.Image:
    """Crop to the visible pixels so height maths is about the character."""
    alpha = image.getchannel("A")
    box = alpha.getbbox()
    return image.crop(box) if box else image


def erode_alpha(image: Image.Image, pixels: int = 1) -> Image.Image:
    """Pull the matte in slightly to kill the halo left by background removal.

    The previous project's own notes record matte haloes as a recurring defect.
    A one-pixel erode costs nothing and removes the fringe.
    """
    if pixels <= 0:
        return image
    alpha = image.getchannel("A")
    alpha = alpha.filter(ImageFilter.MinFilter(2 * pixels + 1))
    out = image.copy()
    out.putalpha(alpha)
    return out


def relight(
    image: Image.Image,
    light: LightContract,
    *,
    spill_color: tuple[int, int, int] | None = None,
) -> Image.Image:
    """Apply directional key, fill and environmental spill to a character layer.

    Deliberately gentle. The approved art already carries the house style's cel
    shading; this nudges it toward the scene rather than repainting it.
    """
    rgba = np.asarray(image.convert("RGBA")).astype(np.float32)
    rgb, alpha = rgba[..., :3], rgba[..., 3:4] / 255.0
    height, width = rgb.shape[:2]

    # Cut-out layers carry arbitrary colour under alpha=0 - whatever the matte
    # left behind. It never renders (alpha is passed through untouched below),
    # but the Lab work still pays for it, and that colour is often wildly
    # out of gamut once darkened. Measured on the layer library: ~63% of pixels
    # are fully transparent and 67.6% go out of gamut, but only 4.1% are BOTH
    # visible and out of gamut. Neutralising the invisible ones is free.
    # Anti-aliased edge pixels have alpha > 0 and are untouched.
    rgb = np.where(alpha > 0.0, rgb, 0.0)

    # A soft linear gradient standing in for a distant directional source.
    angle = math.radians(light.key_angle_deg)
    xs = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
    ys = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
    gradient = xs * math.cos(angle) - ys * math.sin(angle)
    gradient = (gradient + 1.0) / 2.0
    lit = gradient[..., None]

    key = np.array(light.key_color, dtype=np.float32) / 255.0
    fill = np.array(light.fill_color, dtype=np.float32) / 255.0

    base = rgb / 255.0

    # Light changes VALUE. In cel art it must barely change HUE, because the
    # flat fills are graphic identity - Scarline's scarlet streak, Zombie's pale
    # green, NeonBlue's cyan crown - not physical surfaces.
    #
    # So compute the fully-tinted result, then keep only its luminance and
    # restore the original hue, blending a controlled amount of tint back in.
    #
    # Measured: tinting freely moved saturated canon swatches by dE 14-20
    # (#B44236 -> dE 20, #A8C09C -> dE 14) and failed 74 of 417 library
    # measurements. See docs/audits/LIKENESS_TUNING_REPORT.md.
    tinted = base
    tinted = tinted * (1.0 - light.key_strength
                       + light.key_strength * lit * key * 1.6)
    tinted = (tinted * (1.0 - light.fill_strength)
              + tinted * light.fill_strength * fill * 1.4)
    if spill_color is not None and light.spill_strength > 0:
        spill = np.array(spill_color, dtype=np.float32) / 255.0
        tinted = (tinted * (1.0 - light.spill_strength)
                  + tinted * spill * light.spill_strength * 2.0)

    # Take the light's LIGHTNESS and the art's HUE AND CHROMA, recombined in
    # Lab. Doing this by scaling RGB ratios instead - the obvious approach - is
    # not the same thing: uniform RGB scaling preserves hue in RGB terms but
    # still moves a* and b*, leaving an irreducible ~10 dE on saturated colours
    # even at full protection. Measured on a flat #B94235 patch under a cyan
    # key: 10.2 dE at protect=1.0, where it should be ~0.
    base_lab = srgb_to_lab(base * 255.0)
    tinted_lab = srgb_to_lab(np.clip(tinted, 0.0, 1.0) * 255.0)
    recombined = np.stack(
        [tinted_lab[..., 0], base_lab[..., 1], base_lab[..., 2]], axis=-1
    )
    hue_safe = (lab_to_srgb_in_gamut(recombined) / 255.0).astype(np.float32)

    # Then allow a limited amount of real tint back, so the character still
    # belongs to the scene rather than looking cut out of a different one.
    tint = np.clip(1.0 - light.protect_neutrals, 0.0, 1.0)
    out = hue_safe * (1.0 - tint) + tinted * tint

    if light.ambient_lift:
        out = out + light.ambient_lift

    if light.rim_strength > 0:
        edge = image.getchannel("A").filter(ImageFilter.FIND_EDGES).filter(
            ImageFilter.GaussianBlur(2)
        )
        edge_arr = np.asarray(edge).astype(np.float32)[..., None] / 255.0
        out = out + edge_arr * key * light.rim_strength

    out = np.clip(out * 255.0, 0, 255)
    merged = np.concatenate([out, alpha * 255.0], axis=-1).astype(np.uint8)
    return Image.fromarray(merged, "RGBA")


def contact_shadow(size: tuple[int, int], light: LightContract) -> Image.Image:
    """A tight dark pool directly under the character's contact point."""
    width, height = size
    shadow_w = int(width * 0.82)
    shadow_h = max(6, int(height * 0.055))
    layer = Image.new("L", (shadow_w, shadow_h), 0)
    draw = ImageDraw.Draw(layer)
    draw.ellipse([0, 0, shadow_w - 1, shadow_h - 1], fill=int(255 * light.contact_opacity))
    layer = layer.filter(ImageFilter.GaussianBlur(max(2, shadow_h * 0.35)))
    return layer


def cast_shadow(character: Image.Image, light: LightContract) -> tuple[Image.Image, int]:
    """A skewed silhouette thrown away from the key light along the ground.

    Returns the shadow layer and the x offset its top-left should be placed at,
    relative to the character's own top-left.
    """
    alpha = character.getchannel("A")
    width, height = alpha.size

    squash = max(0.12, light.cast_length)
    shadow_h = max(4, int(height * squash))
    silhouette = alpha.resize((width, shadow_h), Image.LANCZOS)

    # Lean away from the light. Positive key_angle from frame right pushes left.
    lean = -math.cos(math.radians(light.key_angle_deg))
    shift = int(width * 0.85 * lean)

    canvas_w = width + abs(shift) * 2
    canvas = Image.new("L", (canvas_w, shadow_h), 0)
    canvas.paste(silhouette, (abs(shift), 0))

    sheared = canvas.transform(
        (canvas_w, shadow_h), Image.AFFINE,
        (1, shift / max(1, shadow_h), 0, 0, 1, 0),
        resample=Image.BILINEAR,
    )
    sheared = sheared.filter(ImageFilter.GaussianBlur(max(3, shadow_h * 0.18)))
    sheared = sheared.point(lambda v: int(v * light.cast_opacity))
    return sheared, -abs(shift)


def _sample_environment(plate: Image.Image, x: int, y: int, radius: int = 90) -> tuple[int, int, int]:
    """Average colour around a point, used as the local spill colour."""
    left = max(0, x - radius)
    top = max(0, y - radius)
    right = min(plate.width, x + radius)
    bottom = min(plate.height, y + radius)
    if right <= left or bottom <= top:
        return (128, 128, 128)
    region = plate.convert("RGB").crop((left, top, right, bottom))
    arr = np.asarray(region).reshape(-1, 3).mean(axis=0)
    return tuple(int(v) for v in arr)


@dataclass
class CompositeReport:
    placements: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def likeness_passed(self) -> bool:
        """True only if every staged character cleared the likeness gate.

        A panel with an uncertain character identity is not approvable, so the
        compositor records a number for every placement rather than leaving it
        to a later manual check that may not happen.
        """
        return all(p.get("likeness_passed", False) for p in self.placements)

    @property
    def worst_likeness(self) -> float:
        return min((p.get("likeness_score", 0.0) for p in self.placements),
                   default=100.0)


def composite_panel(
    plate_path: Path,
    ground: GroundPlane,
    light: LightContract,
    placements: list[Placement],
    *,
    output_size: tuple[int, int] | None = None,
) -> tuple[Image.Image, CompositeReport]:
    """Stage every character into the plate and return the finished panel art.

    Characters are drawn back to front so nearer figures occlude further ones.
    """
    plate = _load_rgba(plate_path)
    canvas = plate.copy()
    shadow_layer = Image.new("L", canvas.size, 0)
    report = CompositeReport()

    order = {"background": 0, "midground": 1, "foreground": 2}
    ordered = sorted(placements, key=lambda p: order.get(p.depth_plane, 1))

    prepared: list[tuple[Placement, Image.Image, int, int, LikenessResult, object]] = []

    for place in ordered:
        if place.flip and place.character_id in NO_FLIP:
            report.warnings.append(
                f"CANON: refused to mirror {place.character_id} - "
                f"{NO_FLIP[place.character_id]}"
            )
            place.flip = False

        slug = pose_slug(place.layer_path)
        if slug in NON_STANDING_POSES and place.contact_offset == 0.0:
            report.warnings.append(
                f"STAGING: {place.character_id} uses pose '{slug}' "
                f"({NON_STANDING_POSES[slug]}) but contact_offset is 0 - "
                f"the figure will not sit on the ground correctly"
            )

        layer = trim_alpha(_load_rgba(place.layer_path))
        layer = erode_alpha(layer, 1)

        try:
            target_h = ground.character_height_at(place.foot_y) * place.scale_multiplier
        except ValueError as exc:
            report.warnings.append(f"{place.character_id}: {exc}")
            continue

        scale = target_h / layer.height
        new_size = (max(1, int(layer.width * scale)), max(1, int(layer.height * scale)))
        layer = layer.resize(new_size, Image.LANCZOS)

        if place.flip:
            layer = layer.transpose(Image.FLIP_LEFT_RIGHT)

        blur = DEPTH_BLUR.get(place.depth_plane, 0.0)
        if blur:
            layer = layer.filter(ImageFilter.GaussianBlur(blur))

        left = place.centre_x - layer.width // 2
        top = int(place.foot_y - layer.height + place.contact_offset)

        # The identity reference for this placement: the approved layer as it
        # will appear in the panel, before any lighting touches it. Captured
        # after flip and depth blur (both legitimate staging) and before relight
        # and haze (both of which can move colour), so the measurement isolates
        # what the lighting did to the character.
        canon_reference = layer.copy()

        spill = _sample_environment(plate, place.centre_x, int(place.foot_y - layer.height * 0.5))
        layer = relight(layer, light, spill_color=spill)

        haze = DEPTH_HAZE.get(place.depth_plane, 0.0)
        if haze:
            veil = Image.new("RGBA", layer.size, spill + (int(255 * haze),))
            veil.putalpha(
                ImageChops.multiply(veil.getchannel("A"), layer.getchannel("A"))
            )
            layer = Image.alpha_composite(layer, veil)

        # Shadows go down first, under everything.
        contact = contact_shadow(layer.size, light)
        cx = place.centre_x - contact.width // 2
        cy = int(place.foot_y + place.contact_offset - contact.height * 0.55)
        shadow_layer.paste(
            ImageChops.lighter(
                shadow_layer.crop((cx, cy, cx + contact.width, cy + contact.height)), contact
            ),
            (cx, cy),
        )

        cast, cast_dx = cast_shadow(layer, light)
        gx = left + cast_dx
        gy = int(place.foot_y + place.contact_offset - cast.height * 0.5)
        region = shadow_layer.crop((gx, gy, gx + cast.width, gy + cast.height))
        shadow_layer.paste(ImageChops.lighter(region, cast), (gx, gy))

        # Measure identity now, while the reference is still aligned. Once the
        # character is composited onto the plate it cannot be separated from the
        # background, and the number would no longer be recoverable.
        likeness = measure(
            layer, canon_reference, place.character_id,
            layer_name=Path(place.layer_path).name,
            identity_critical=place.identity_critical,
        )
        if not likeness.passed:
            report.warnings.append(
                f"LIKENESS: {place.character_id} scored {likeness.score:.1f} "
                f"(gate 95.0) from {Path(place.layer_path).name}"
                + (f" - {likeness.notes[0]}" if likeness.notes else "")
            )

        # Scene integration: the opposing axis. Likeness alone is maximised by
        # not lighting the character at all, so a panel that reports only
        # likeness cannot tell a well-lit character from a cut-out.
        #
        # Imported here, not at module scope: integration imports LightContract
        # and relight from this module, so a top-level import is a cycle.
        from app.services.integration import measure_integration

        integration = measure_integration(
            layer, canon_reference, plate,
            (left, top, left + layer.width, top + layer.height),
            light, spill_color=spill,
        )
        # REPORTED, NOT GATED. Likeness has 1089 adversarial controls behind it;
        # this has ~400. It warns loudly and leaves the verdict to likeness.
        if integration.score < CUTOUT_WARNING_SCORE and integration.score > 0.0:
            report.warnings.append(
                f"INTEGRATION: {place.character_id} scored "
                f"{integration.score:.1f} - barely responds to the panel's "
                f"light and may read as pasted on"
            )

        prepared.append((place, layer, left, top, likeness, integration))

    # Burn shadows into the plate before the characters land on top.
    shadow_rgba = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_rgba.putalpha(shadow_layer)
    canvas = Image.alpha_composite(canvas, shadow_rgba)

    for place, layer, left, top, likeness, integration in prepared:
        canvas.alpha_composite(layer, (left, top))
        if place.occluder and Path(place.occluder).is_file():
            occ = _load_rgba(Path(place.occluder)).resize(canvas.size, Image.LANCZOS)
            canvas = Image.alpha_composite(canvas, occ)
        report.placements.append(
            {
                "character_id": place.character_id,
                "layer": Path(place.layer_path).name,
                "centre_x": place.centre_x,
                "foot_y": place.foot_y,
                "rendered_height_px": layer.height,
                "rendered_width_px": layer.width,
                "depth_plane": place.depth_plane,
                "scale_multiplier": place.scale_multiplier,
                "top_left": [left, top],
                "likeness_score": likeness.score,
                "likeness_passed": likeness.passed,
                "likeness_palette_de": round(likeness.palette_delta_e, 2),
                "likeness_pixel_drift_de": round(likeness.pixel_drift_de, 2),
                "likeness_notes": likeness.notes,
                "likeness_legibility_exempt": likeness.legibility_exempt,
                "identity_critical": place.identity_critical,
                "integration_score": integration.score,
                "integration_notes": integration.notes,
            }
        )

    if output_size and canvas.size != output_size:
        canvas = canvas.resize(output_size, Image.LANCZOS)

    return canvas.convert("RGB"), report
