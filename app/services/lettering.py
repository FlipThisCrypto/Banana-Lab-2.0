"""Balloons, caption boxes and sound effects.

Stage 10 of the pipeline. Until this existed the sample pages measured
`lettering_pct` 0.0 against a published median of 5.16 - the single largest gap
on the aesthetic scorecard, and the reason the pages read as illustrated
backgrounds rather than as comics.

Everything here is deterministic: the same script and the same layout produce
the same lettering, so a defect can be diagnosed rather than re-rolled.

Placement comes from the layout spec's `bubble_zones`, which already declare
where a balloon may go and who it belongs to. Nothing here invents a position,
and nothing here invents text - the words are the script's.

Observed in the published editions and reproduced:

  - balloons are white or a per-speaker colour, with a thin dark outline and a
    straight tail pointing at the speaker
  - captions are rectangles with a thin border, set apart from balloons
  - sound effects are large display type with a heavy outline, allowed to break
    the panel edge
  - lettering is ALL CAPS in edition two, mixed case in edition one; mixed case
    is used here because Issue 001's script is written that way
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

#: Comic Sans Bold for dialogue and Impact for sound effects. Neither is the
#: studio's actual lettering font - that is not in the repository - but both are
#: the right CATEGORY: a rounded informal hand for speech, a heavy condensed
#: display face for impact. Recorded as a substitution, not a match.
_FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts")]
DIALOGUE_FONT = "comicbd.ttf"
CAPTION_FONT = "comic.ttf"
SFX_FONT = "impact.ttf"

#: Speaker -> balloon fill. Edition two gives major speakers their own colour;
#: this assignment is a PLACEHOLDER pending the owner ruling recorded as an open
#: question in the issue bible, and is deliberately conservative - white for
#: everyone except the two leads.
BALLOON_FILL = {
    "MZ-CHAR-005": (255, 255, 255),
    "MZ-CHAR-001": (255, 255, 255),
}
DEFAULT_FILL = (255, 255, 255)
BALLOON_OUTLINE = (16, 16, 20)
CAPTION_FILL = (252, 250, 244)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in _FONT_DIRS:
        candidate = directory / name
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit(draw: ImageDraw.ImageDraw, text: str, name: str, box: tuple[int, int, int, int],
         start: int, floor: int = 13) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """The largest size at which the text fits the zone the layout allotted it."""
    _, _, width, height = box
    size = start
    while size > floor:
        font = _font(name, size)
        lines = _wrap(draw, text, font, int(width * 0.86))
        needed = len(lines) * (size * 1.22)
        if needed <= height * 0.86:
            return font, lines
        size -= 2
    font = _font(name, floor)
    return font, _wrap(draw, text, font, int(width * 0.86))


@dataclass
class Balloon:
    text: str
    zone: tuple[int, int, int, int]
    speaker: str = ""
    #: Where the tail points, in page pixels. None draws no tail - used for
    #: captions and for a speaker who is out of frame.
    tail_to: tuple[int, int] | None = None
    kind: str = "speech"


def draw_balloon(page: Image.Image, balloon: Balloon) -> None:
    """One balloon or caption, drawn into the zone the layout declared for it."""
    draw = ImageDraw.Draw(page)
    x, y, width, height = balloon.zone

    if balloon.kind == "caption":
        font, lines = _fit(draw, balloon.text, CAPTION_FONT, balloon.zone,
                           max(16, int(height * 0.30)))
        line_h = font.size * 1.22
        used_h = int(len(lines) * line_h + height * 0.16)
        used_w = int(max(draw.textlength(l, font=font) for l in lines)
                     + width * 0.10)
        box = [x, y, x + used_w, y + used_h]
        draw.rectangle(box, fill=CAPTION_FILL, outline=BALLOON_OUTLINE,
                       width=max(2, int(height * 0.018)))
        for index, line in enumerate(lines):
            draw.text((x + width * 0.05, y + height * 0.07 + index * line_h),
                      line, font=font, fill=(24, 24, 28))
        return

    font, lines = _fit(draw, balloon.text, DIALOGUE_FONT, balloon.zone,
                       max(16, int(height * 0.26)))
    line_h = font.size * 1.20
    text_w = max(draw.textlength(l, font=font) for l in lines)
    body_w = int(min(width, text_w + width * 0.26))
    # Keep the balloon from becoming a letterbox slot: at least 46% as
    # tall as it is wide, which is roughly the published proportion.
    body_h = int(min(height, max(len(lines) * line_h + height * 0.30,
                                body_w * 0.46)))
    cx, cy = x + body_w / 2, y + body_h / 2

    fill = BALLOON_FILL.get(balloon.speaker, DEFAULT_FILL)
    rule = max(2, int(body_h * 0.028))

    # The tail is drawn first as a filled triangle from the body toward the
    # speaker, then the body goes over it, so the join needs no masking.
    if balloon.tail_to is not None:
        tx, ty = balloon.tail_to
        angle = math.atan2(ty - cy, tx - cx)
        # A tail is a WEDGE. At spread 0.16 rad off a narrow base this drew a
        # hairline that read as a wire running from the balloon to the floor.
        # The base has to be a real fraction of the balloon so the tail is
        # visibly part of it.
        spread = 0.30
        base = max(body_w, body_h) * 0.40

        # The tail is a SHORT stub, not a wedge stretching to the speaker.
        # Drawing the polygon out to a distant target made the triangle scale
        # with the distance: a speaker across the panel produced a white wedge
        # covering the middle of the frame. Published tails extend roughly half a
        # balloon height and let the reader's eye finish the line.
        reach = min(math.hypot(tx - cx, ty - cy), body_h * 1.15)
        tip = (cx + math.cos(angle) * reach, cy + math.sin(angle) * reach)

        p1 = (cx + math.cos(angle - spread) * base,
              cy + math.sin(angle - spread) * base)
        p2 = (cx + math.cos(angle + spread) * base,
              cy + math.sin(angle + spread) * base)
        draw.polygon([p1, p2, tip], fill=fill,
                     outline=BALLOON_OUTLINE, width=rule)

    draw.ellipse([x, y, x + body_w, y + body_h], fill=fill,
                 outline=BALLOON_OUTLINE, width=rule)

    total = len(lines) * line_h
    for index, line in enumerate(lines):
        line_w = draw.textlength(line, font=font)
        draw.text((cx - line_w / 2, cy - total / 2 + index * line_h),
                  line, font=font, fill=(20, 20, 24))


def draw_sfx(page: Image.Image, text: str, centre: tuple[int, int],
             height_px: int, colour=(214, 38, 34)) -> None:
    """A sound effect as heavy outlined display type.

    Drawn on its own layer and rotated, so it can sit at an angle and overlap
    the panel rule the way the published editions do.
    """
    font = _font(SFX_FONT, max(24, height_px))
    pad = int(height_px * 0.5)
    tmp = Image.new("RGBA", (int(font.getlength(text)) + pad * 2,
                             int(height_px * 1.7) + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    stroke = max(3, int(height_px * 0.10))
    # White keyline outside a dark keyline, which is what gives the published
    # SFX its punch against any background.
    d.text((pad, pad), text, font=font, fill=colour,
           stroke_width=stroke, stroke_fill=(255, 255, 255))
    d.text((pad, pad), text, font=font, fill=colour,
           stroke_width=max(1, stroke // 3), stroke_fill=(16, 16, 20))
    tmp = tmp.rotate(-8, expand=True, resample=Image.BICUBIC)
    shadow = tmp.getchannel("A").filter(ImageFilter.GaussianBlur(stroke * 0.8))
    dark = Image.new("RGBA", tmp.size, (0, 0, 0, 110))
    dark.putalpha(shadow)
    page.alpha_composite(dark, (int(centre[0] - tmp.width / 2) + stroke,
                                int(centre[1] - tmp.height / 2) + stroke))
    page.alpha_composite(tmp, (int(centre[0] - tmp.width / 2),
                               int(centre[1] - tmp.height / 2)))
