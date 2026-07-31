"""The cover: title treatment, collectible stamp, tagline and spine text.

Measured from `TheFusionSquad.pdf` page 1 at 200 dpi rather than invented:

  - three or four white diagonal stripes run lower-left to upper-right behind
    the title, at the same angle as the type
  - the masthead is heavy condensed caps, red, with a thick WHITE outline, a
    dark keyline outside that, and a drop shadow down-left
  - the subtitle uses the same face and treatment in pale blue-grey, set in
    decreasing sizes on two or three lines, tucked under the masthead's right
  - the Fiend Studios collectible stamp sits top-left on a white patch
  - caption boxes sit bottom-right

The stamp is the studio's real mark, used from
`source_material/visual_references/published_editions/_stamps/`. It is placed
UNMODIFIED. The edition line on the available asset reads EDITION TWO, and which
edition this issue is remains an open owner question recorded in the layout
spec, so nothing here paints a different number onto the studio's trademark.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

STAMP = Path("source_material/visual_references/published_editions/_stamps/"
             "Fiend_Studios_Stamp_2-removebg-preview.png")

_FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts")]
#: Impact is the closest available face to the published masthead: heavy,
#: condensed, all-caps. Recorded as a substitution, not a match - the studio's
#: actual display face is not in this repository.
DISPLAY_FONT = "impact.ttf"
TAGLINE_FONT = "comicbd.ttf"

MASTHEAD_RED = (206, 26, 24)
SUBTITLE_BLUE = (176, 196, 214)
OUTLINE_WHITE = (255, 255, 255)
KEYLINE_DARK = (26, 20, 22)

#: Measured off the reference: the masthead baseline rises to the right.
TITLE_ANGLE_DEG = 11.0


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in _FONT_DIRS:
        candidate = directory / name
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _display_text(text: str, height_px: int, fill, *,
                  slant: float = 0.18) -> Image.Image:
    """One line of masthead type: fill, white outline, dark keyline, shadow.

    Rendered oversized on its own layer then sheared, so the italic slant does
    not soften the outline the way rotating a finished bitmap would.
    """
    font = _font(DISPLAY_FONT, height_px)
    pad = int(height_px * 0.55)
    width = int(font.getlength(text)) + pad * 2
    layer = Image.new("RGBA", (width, int(height_px * 1.9) + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    outer = max(4, int(height_px * 0.085))
    inner = max(2, int(height_px * 0.045))
    # Dark keyline first, then the white outline over it, then the fill: the
    # published masthead reads as red inside white inside black.
    draw.text((pad, pad), text, font=font, fill=KEYLINE_DARK,
              stroke_width=outer + inner, stroke_fill=KEYLINE_DARK)
    draw.text((pad, pad), text, font=font, fill=OUTLINE_WHITE,
              stroke_width=outer, stroke_fill=OUTLINE_WHITE)
    draw.text((pad, pad), text, font=font, fill=fill)

    if slant:
        w, h = layer.size
        layer = layer.transform((w + int(h * slant), h), Image.AFFINE,
                                (1, -slant, 0, 0, 1, 0), resample=Image.BICUBIC)
    return layer


def _with_shadow(layer: Image.Image, offset: int) -> Image.Image:
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    alpha = layer.getchannel("A").filter(ImageFilter.GaussianBlur(offset * 0.5))
    dark = Image.new("RGBA", layer.size, (12, 10, 14, 165))
    dark.putalpha(alpha)
    out = Image.new("RGBA", (layer.width + offset, layer.height + offset), (0, 0, 0, 0))
    out.alpha_composite(dark, (0, offset))
    out.alpha_composite(layer, (offset // 2, 0))
    return out


def draw_stripes(page: Image.Image, top: float, band: float,
                 count: int = 4) -> None:
    """The white diagonal bands the masthead sits on."""
    width, height = page.size
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    angle = math.radians(TITLE_ANGLE_DEG)
    run = math.tan(angle) * width

    thickness = int(height * band)
    for index in range(count):
        y = int(height * top) + index * int(thickness * 2.15)
        draw.polygon(
            [(-width, y + run), (width * 2, y - run),
             (width * 2, y - run + thickness), (-width, y + run + thickness)],
            fill=(255, 255, 255, 232),
        )
    page.alpha_composite(layer)


def draw_hanging_light(page: Image.Image, at: tuple[float, float],
                       radius_frac: float = 0.055) -> None:
    """The one bulb still burning, on its flex, with a glow.

    The brief is "NeonBlue central, reaching toward a small light while the
    festival blacks out". The generated plate puts its warm pool on the GROUND,
    so there was nothing above him to reach toward and the raised arms read as
    an empty gesture. This draws the thing the reach is aimed at.
    """
    width, height = page.size
    cx, cy = int(width * at[0]), int(height * at[1])
    radius = int(width * radius_frac)

    # The glow has to carry the whole idea of "the last light", so it is not
    # subtle. The first version peaked at alpha 79 over a mid-blue sky and was
    # invisible; this reaches full opacity at the core and falls off over four
    # bulb radii.
    glow = Image.new("RGBA", page.size, (0, 0, 0, 0))
    halo = ImageDraw.Draw(glow)
    for step in range(14, 0, -1):
        r = int(radius * step * 0.55)
        alpha = int(6 + (14 - step) ** 2 * 1.5)
        halo.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=(255, 214, 142, min(235, alpha)))
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 0.5))
    page.alpha_composite(glow)

    # A few rays, so it reads as a source rather than a sticker.
    rays = Image.new("RGBA", page.size, (0, 0, 0, 0))
    pen = ImageDraw.Draw(rays)
    for index in range(12):
        angle = math.radians(index * 30 + 8)
        far = radius * 5.2
        pen.line([(cx, cy), (cx + math.cos(angle) * far, cy + math.sin(angle) * far)],
                 fill=(255, 226, 168, 46), width=max(2, int(radius * 0.10)))
    rays = rays.filter(ImageFilter.GaussianBlur(radius * 0.22))
    page.alpha_composite(rays)

    draw = ImageDraw.Draw(page)
    # Flex running up out of frame, so the bulb is hanging rather than floating.
    draw.line([(cx, 0), (cx, cy - int(radius * 0.9))],
              fill=(18, 16, 20, 255), width=max(3, int(width * 0.0035)))
    draw.ellipse([cx - int(radius * 0.30), cy - int(radius * 1.15),
                  cx + int(radius * 0.30), cy - int(radius * 0.72)],
                 fill=(38, 34, 32, 255))
    draw.ellipse([cx - radius // 2, cy - radius // 2, cx + radius // 2,
                  cy + radius // 2], fill=(255, 232, 176, 255),
                 outline=(24, 20, 18, 255), width=max(2, int(width * 0.002)))


@dataclass
class CoverText:
    masthead: str
    subtitle_lines: list[str]
    tagline: str = ""
    spine: str = ""
    captions: list[str] = field(default_factory=list)


def render_cover(plate: Image.Image, text: CoverText,
                 stamp_path: Path = STAMP) -> Image.Image:
    """Compose the full cover over an already-staged plate."""
    page = plate.convert("RGBA")
    width, height = page.size

    draw_stripes(page, top=0.055, band=0.016)

    # Masthead, spanning most of the width in the upper third.
    masthead = _display_text(text.masthead, int(height * 0.105), MASTHEAD_RED)
    # 0.90 of width starting at 0.05 ran the masthead under the stamp patch,
    # which occupies the top-left corner out to about 0.23 of width.
    scale = (width * 0.72) / masthead.width
    masthead = masthead.resize(
        (int(masthead.width * scale), int(masthead.height * scale)),
        Image.LANCZOS)
    masthead = _with_shadow(masthead, max(4, int(height * 0.006)))
    page.alpha_composite(masthead, (int(width * 0.245), int(height * 0.038)))

    # Subtitle: decreasing sizes, tucked under the masthead toward the right.
    y = int(height * 0.035 + masthead.height * 0.86)
    for index, line in enumerate(text.subtitle_lines):
        size = int(height * (0.062 - index * 0.012))
        block = _display_text(line, max(24, size), SUBTITLE_BLUE)
        target = width * (0.62 - index * 0.06)
        factor = target / block.width
        block = block.resize((int(block.width * factor), int(block.height * factor)),
                             Image.LANCZOS)
        block = _with_shadow(block, max(3, int(height * 0.004)))
        page.alpha_composite(block, (int(width - block.width - width * 0.05), y))
        y += int(block.height * 0.74)

    # The studio's own mark, placed unmodified on a white patch.
    if stamp_path.is_file():
        with Image.open(stamp_path) as source:
            stamp = source.convert("RGBA")
        edge = int(width * 0.20)
        stamp = stamp.resize((edge, edge), Image.LANCZOS)
        patch = Image.new("RGBA", (int(edge * 1.06), int(edge * 1.06)),
                          (255, 255, 255, 255))
        page.alpha_composite(patch, (int(width * 0.012), int(height * 0.010)))
        page.alpha_composite(stamp, (int(width * 0.023), int(height * 0.016)))

    draw = ImageDraw.Draw(page)

    if text.tagline:
        font = _font(TAGLINE_FONT, int(height * 0.021))
        box_w = int(draw.textlength(text.tagline, font=font) + width * 0.035)
        box_h = int(height * 0.036)
        # 0.63 put the tagline across the hero's head. The band between the
        # subtitle and the cast is clear at 0.545.
        x0, y0 = int(width * 0.06), int(height * 0.545)
        draw.rectangle([x0, y0, x0 + box_w, y0 + box_h], fill=(252, 250, 244),
                       outline=KEYLINE_DARK, width=max(2, int(height * 0.0016)))
        draw.text((x0 + width * 0.017, y0 + box_h * 0.24), text.tagline,
                  font=font, fill=(26, 24, 28))

    for index, caption in enumerate(text.captions):
        font = _font(TAGLINE_FONT, int(height * 0.019))
        # WRAP to a fixed measure. Splitting on newlines only meant a
        # one-sentence logline became a single line wider than the page, and the
        # box - positioned from its own width - started off the left edge.
        limit = int(width * 0.36)
        lines: list[str] = []
        current = ""
        for word in caption.split():
            trial = f"{current} {word}".strip()
            if draw.textlength(trial, font=font) <= limit or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        box_w = int(max(draw.textlength(l, font=font) for l in lines) + width * 0.03)
        box_h = int(len(lines) * height * 0.026 + height * 0.012)
        x0 = int(width - box_w - width * 0.06)
        y0 = int(height * (0.80 + index * 0.085))
        draw.rectangle([x0, y0, x0 + box_w, y0 + box_h], fill=(255, 255, 255),
                       outline=KEYLINE_DARK, width=max(2, int(height * 0.0016)))
        for n, line in enumerate(lines):
            draw.text((x0 + width * 0.014, y0 + box_h * 0.16 + n * height * 0.026),
                      line, font=font, fill=(24, 22, 26))

    # Spine text runs bottom-to-top up the left edge.
    if text.spine:
        font = _font(DISPLAY_FONT, int(height * 0.020))
        strip = Image.new("RGBA",
                          (int(draw.textlength(text.spine, font=font) + width * 0.02),
                           int(height * 0.030)), (0, 0, 0, 0))
        ImageDraw.Draw(strip).text((0, 0), text.spine, font=font,
                                   fill=(245, 243, 240), stroke_width=3,
                                   stroke_fill=KEYLINE_DARK)
        strip = strip.rotate(90, expand=True, resample=Image.BICUBIC)
        page.alpha_composite(strip, (int(width * 0.008),
                                     int(height * 0.52 - strip.height / 2)))

    return page.convert("RGB")
