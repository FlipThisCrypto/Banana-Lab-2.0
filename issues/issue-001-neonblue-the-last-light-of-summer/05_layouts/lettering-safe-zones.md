# Issue 001 — Lettering Safe Zones

Where balloons and captions may go, and what they must never cover.

Machine-readable zones are in `layout-spec.yaml` under each panel's
`bubble_zones`, expressed as fractions of the panel box.

---

## The rule

**Lettering is placed in space the artwork reserves for it.** A balloon is never
moved to avoid a face after the fact — the panel is composed with the balloon
zone empty from the start.

Every panel in the script declares a `bubble_placement_zone`. That declaration
is an instruction to the background and compositing stages, not a note for the
letterer.

---

## Never covered

- **Faces.** Any part of any character's face.
- **Hands**, and anything a character is holding.
- **The panel's story content.** If the beat is a relay marker, the balloon does
  not touch the relay marker.
- **Contact points.** Where a character meets the ground, an object or another
  character.
- **The Echo segment**, in every panel where it appears.

---

## Page margins

| Measure | Value |
|---|---|
| Trim | 210 × 297 mm |
| Bleed | 3 mm |
| Safe margin | 10 mm from trim |
| Live margin | 14 mm from trim |
| Gutter | 4 mm |

No lettering crosses the safe margin. Balloon tails may extend toward the panel
edge; balloon bodies may not.

---

## Balloon budget

From the generated `dialogue-only.md`:

| Measure | Value |
|---|---|
| Balloons in the issue | 103 script panels, 66 carrying dialogue |
| Maximum balloons per panel | 2 |
| Maximum words per balloon | 15 |
| Typical balloon | 7–11 words |

The 15-word ceiling exists so a balloon occupies roughly a fifth of a panel
rather than a third. The legacy script ran 18–25 words per line, which is a
large part of why its panels had no room for staging.

---

## Colour coding

Adopted from Edition Two, per `canon/style/HOUSE_STYLE.md`. Six Emo Monkeys plus
a guest is exactly the ensemble size that needs it.

**Assignment is an open owner decision.** The proposal:

| Character | Balloon fill | Rationale |
|---|---|---|
| NeonBlue | Pale cream | Warmest, most frequent speaker |
| Moodz | Soft grey-blue | Cool and quiet |
| TwoTone | White | Neutral, analytical |
| Static | Pale yellow | Highest energy |
| Ash | Pale grey | Speaks once; should look different |
| Scarline | Pale rose | Ties to her scarlet streak without shouting |
| Lil Devil | Warm orange | Hot, matches his red |
| Caption | Rectangular, off-white, black border | Distinct from all balloons |

Fills must stay pale enough that black lettering holds contrast at print size.

---

## Zone placement by panel type

| Panel type | Default zone | Note |
|---|---|---|
| Wide establishing | Upper band, over sky or open ground | Never over the horizon line |
| Two-shot | Upper left and upper right, one per speaker | Reading order left to right |
| Close-up | Upper corner opposite the character's gaze | Uses the space the gaze leaves |
| Insert | One corner, over the darkest area | Insert content is small; the balloon must not compete |
| Silent panel | **No zone** | 19 panels have none and must stay clear |
| Splash (page 11) | **No zone** | Entirely silent |

---

## Panels needing special care

| Panel | Issue |
|---|---|
| `ISSUE001-P13-01` | Balloon and a large SFX share the frame. SFX takes the left, balloon the upper right. |
| `ISSUE001-P18-06` | Balloon must clear the grating and all three trapped faces. Upper left only. |
| `ISSUE001-P19-01` | Two light sources and a small distant Scarline. Balloon sits upper right with a long tail to her — the tail must not cross NeonBlue's face. |
| `ISSUE001-P20-01` | Five characters, two stacked balloons. Zone must clear all five faces. |
| `ISSUE001-P21-01` | Impact SFX may break the panel border. Balloon goes lower left, well clear. |
| `ISSUE001-P22-05` | Balloon over open sky. Must not touch the tower or the lit Echo segment. |

---

## SFX

SFX are artwork, not lettering, and are placed at the effects stage.

- They may overlap panel borders where the house style supports it —
  `ISSUE001-P21-01` is flagged for this in the layout spec.
- They may pass behind characters.
- They must not obscure a face or the panel's story content.
- They are never rendered into the panel art. Like balloons, they are a
  downstream layer.

---

## Open items for layout approval

1. Balloon colour assignment per speaker — owner decision.
2. Lettering font — not yet specified anywhere in the project, including the
   published editions' records. Needs to be chosen and recorded in the house
   style.
3. Caption box treatment — rectangular with a black border is proposed from the
   published editions; confirm.
