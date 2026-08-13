# MonkeyZoo House Style

**Authority: authoritative.** Confirmed by the project owner on 2026-07-28:
*"This is the artistic style that I want for each issue."*

The style is defined by three published Fiend Studios editions, not by any
in-house draft. Where this document and a draft-tier issue disagree, this
document wins.

## The reference editions

| Edition | Title | Pages | Source |
|---|---|---|---|
| **One** | MonkeyZoo: The Battle Against Inefficiency and Centralization | 11 | `source_material/visual_references/published_editions/edition-01-the-fusion-squad/` |
| **Two** | FusionZoo: The De-Fusion Tapes | 9 | `.../edition-02-the-defusion-tapes/` |
| **Three** | Winter edition | 8 (31 panels) | `.../edition-03-winter/` |

Rendered page images are in each edition's `_pages/` directory. The PDFs are the
untouched imported source; the page images are normalised derivatives.

**For Issue 001, Edition Two is the primary target.** It is the Emo Monkey cast,
at night, in dark interiors, with cyan and green glowing technology — the same
tonal territory as a blacked-out festival with a reacting relay.

Mango Pier (`visual_references/mango-pier/`) is **secondary reference only**. It
is a recent in-house production at a lower finish level, useful for cast
consistency but not the target.

---

## 1. Character rendering

- Chibi proportions: oversized round head, small body, roughly 1:2 head-to-body.
- Huge white oval eyes with small dark pupils. Eye ring and lid treatment carry
  most of the performance.
- Thick, uniform black outlines on characters. Slightly heavier on the outer
  silhouette than on interior detail.
- Flat colour fills with **cel shading** — hard-edged shadow shapes, not soft
  gradients on the character.
- Rim light where the environment justifies it. In Edition Two the emo cast
  picks up green and cyan rim light from screens and holograms constantly.
- Fur reads as flat colour with a small number of shape breaks, not as texture.
- Mitten hands. Simplified feet. Visible stitch seams on characters that have
  them.

**Characters are drawn into scenes.** In all three editions characters stand on
surfaces, cast shadows, are occluded by foreground objects, and pick up
environment colour. Never a cut-out on a plate.

---

## 2. Backgrounds

Backgrounds are **illustrated and detailed**, and carry more rendering than the
characters do.

- Edition One: brick, rubble, wet city streets, cosmic space, circuit-board
  green energy fields.
- Edition Two: server rooms, monitors, cable runs, desks, plants, night
  interiors with practical light sources.
- Edition Three: high-key snow, clean gradients, minimal detail, deliberately
  empty.

Common rules:

- Backgrounds are more painterly than the cast, but keep the same black outline
  language on major forms.
- Practical light sources are visible in frame and explain the lighting on the
  characters.
- Depth is real: foreground occluders, midground action, background falloff.
- Atmospheric effects — rain streaks, haze, glow bloom, floating particles — are
  used freely.

---

## 3. Panel and page architecture

This is where the published editions differ most sharply from the draft-tier
in-house work, and it is the single biggest upgrade Issue 001 needs.

- **Panels sit on a coloured page ground**, not on white. Edition One uses a
  pale blue board throughout. Edition Two changes the page-frame colour per
  page — deep red, orange, blue, dark red — as an emotional signal.
- Panels have thin black borders and consistent gutters.
- **Layouts are irregular and vary every page.** Across Edition One's 11 pages:
  a full-bleed cover, a 5-panel asymmetric grid, three stacked wides, a large
  panel over two smalls, a dense 8-panel grid, a 5-panel mixed grid, two big
  stacked wides, a full-page splash, a 5-panel grid, and two more full-page
  splashes. **No two pages repeat a grid.**
- Full-page splashes are used for genuine peaks and nothing else.
- Edition Three demonstrates extreme shot-size range: macro detail on board
  bindings, extreme close-up on goggles, and completely empty landscape panels
  used as breath.
- Panels may overlap or break their border when an element needs to escape.

---

## 4. Lettering

- Classic comic balloons: rounded, black stroke, tail pointing to the speaker.
- **Balloon fill is colour-coded by speaker** in Edition Two — pale yellow,
  orange, white, cream. This is a strong readability device for a six-character
  ensemble and should be adopted.
- Caption boxes are rectangular with a black border, distinct from balloons.
- Body lettering is comic-style: mostly upper case, with full stops. Mixed case
  appears in Edition One.

### Locked production faces (Issue 001, 2026-08-13)

The published editions do not record their lettering font. Until a licensed
comic-lettering cut (Blambot / Comicraft class) is purchased, Issue 001 is
locked to faces that exist on the production machine and sit in the right
category:

| Role | Face | File |
|---|---|---|
| Dialogue | Comic Sans MS Bold | `comicbd.ttf` |
| Captions | Comic Sans MS Regular | `comic.ttf` |
| SFX | Impact | `impact.ttf` |

This is a **category lock**, not a claim that Edition Two was lettered in Comic
Sans. Safe zones in `layout-spec.yaml` are measured against these files at
6.5 pt floor / 7.5 pt target, 300 dpi. Changing the face requires regenerating
the layout spec and re-running `validate` — the old zones are not portable.
- **SFX are large, stylised and integrated into the scene** — "KRA-KOOOM!",
  "SMASH!", "FZZZZT!", "WOOSH!", "ZAP!", "POW!!". Coloured fills with contrasting
  outlines, angled, often overlapping panel borders or passing behind
  characters. They are artwork, not typography.
- Title treatments are heavy 3D-extruded comic logos with gradient fills.

---

## 5. Covers

Every published edition cover carries:

1. A large stylised title logo.
2. A tagline or subtitle.
3. The featured character, large and central, in a mood-setting environment.
4. **The Fiend Studios collectible stamp.**
5. Often vertical spine text along the left edge ("MONKEYZOO", "Powered by
   FusionZoo — Where Art Evolves").

### The Fiend Studios stamp

A circular black-outlined stamp with distressed edges, reading
`FIEND STUDIOS` around the top arc and `EDITION <NUMBER>` around the bottom arc,
with four small stars at the compass points, `COLLECTIBLE` across the centre,
and a green-and-purple demon head in the middle.

Source: `source_material/visual_references/published_editions/_stamps/`.

**Required on every issue cover.** The edition number changes; nothing else
does.

**OWNER RULING, 2026-07-31 — Issue 001 carries `EDITION FOUR`.** The published
editions are One, Two and Three, so this is the fourth MonkeyZoo comic. This
closes what was an open question.

The stamp asset in `_stamps/` reads `EDITION TWO`. `app.services.cover
.restamp_edition` resets that one line and nothing else: the rings, the four
stars, `COLLECTIBLE`, the demon head and `FIEND STUDIOS` are untouched. The
edition number is the part of the mark that is *supposed* to change.

---

## 6. Colour

- Saturated and high contrast. The editions are not muted.
- Each edition commits to a signature palette: FusionZoo green energy,
  cyan/blue technology, red and gold impact bursts, purple cosmic.
- Radial burst and speed-line backgrounds behind characters for dramatic
  reveals — see Edition One page 2's red and gold starburst.
- Glow is used generously around energy, screens and holograms, and it spills
  onto nearby characters and surfaces.

---

## 7. What the published editions never do

These are the defects visible in the in-house draft work and absent from the
published editions:

- No characters pasted as opaque cards in a row.
- No repeated identical background plate across a page or an issue.
- No uniform grid repeated page after page.
- No panel where the story content is described in a caption but missing from
  the image.
- No baked-in logo bars, catalogue numbers or character name labels inside
  panel art.
- No featureless blob crowds.
- No panel without a shadow where a shadow belongs.

---

## 8. Production consequences

The house style is achievable with the available tooling, but not by
text-to-image alone. See `docs/workflows/COMFYUI_INTEGRATION_PLAN.md`.

| Style requirement | How it is produced |
|---|---|
| Character identity and finish | Approved character art and true-alpha layers. Never text-to-image. |
| Illustrated backgrounds | SDXL with location-bible prompting, palette-locked, then human-selected |
| Cel shading on characters | Inherited from the approved character art |
| Cast and contact shadows | Deterministic compositing from the staging spec |
| Environment colour spill and rim light | Deterministic relight from the plate's declared light direction |
| Irregular panel layouts | Layout spec, applied at page assembly — never rendered into the art |
| Coloured page ground and frames | Page assembly |
| Balloons, captions, SFX | Lettering stage, on top of frameless art |
| Fiend Studios stamp | Cover assembly, from the approved stamp asset |

**Panel art is always frameless and textless.** Borders, page ground, balloons,
captions, SFX and the stamp are all added downstream. This is what makes the
irregular layouts possible without regenerating art.

---

## Open questions for the owner

1. **Edition number for Issue 001.** The published editions are One, Two and
   Three. The new season's first issue needs a number for its stamp — is it
   Edition Four, or does the Emo Monkeys season restart at One?
2. **Page-ground colour for the new season.** Edition One uses one blue board
   throughout; Edition Two changes colour per page. Issue 001's light
   progression would suit Edition Two's approach.
3. **Balloon colour coding.** Adopt Edition Two's per-speaker balloon colours
   for the six-character ensemble, and if so, which colour belongs to whom?
