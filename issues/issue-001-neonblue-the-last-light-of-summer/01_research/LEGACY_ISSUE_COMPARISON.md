# Issue 001 — Legacy Issue Comparison

How the previous Issue 001 compares to the season bible that specified it, to
the Mango Pier issue that is the approved aesthetic reference, and to the
GENESIS material.

---

## 1. Legacy Issue 001 against the season bible

The legacy script is **substantially faithful** to section 7 of the season
bible. This is the good news, and it is why the script is the most reusable
legacy artefact.

| Season bible requirement | Legacy script | Verdict |
|---|---|---|
| Opening: six arrive, NeonBlue over-volunteers | Panel 1.1 | Met |
| Inciting: first blackout, NeonBlue promises backup, it fails | Panels 2.1–2.3 | Met |
| Escalation: outages travel, screens show fractured cyan, Static hears a pattern | Panels 3.1–3.2 | Met |
| Lil Devil pushes for direct attack | Panel 1.2, 4.1 | Partially met — see conflict C-02 |
| Midpoint: NeonBlue sees a marker associated with Patch | Panel 5.1 | Met |
| Moodz tells him he does not have to pretend | Panel 5.2 | Met |
| Crisis: group trapped in dark corridor during the countdown | Panels 6.1–6.2 | Met |
| NeonBlue chooses the overlooked group | Panel 6.2 | Weakly met — the choice is stated, not dramatised |
| Climax: honest plan, directs Lil Devil / Static / TwoTone | Panels 7.1–7.2 | Met for Lil Devil; Static and TwoTone do not act |
| Resolution: reduced festival, no overselling | Panel 8.1 | Met |
| Echo reveal *after* the choice | Panel 8.2 | Met in script |
| Ash's line "Hope can read warnings." | "Hope reads warnings first." | Drifted — conflict C-03 |

### Where the legacy script departs from the bible

1. **The Echo reveal fires early.** The bible is explicit: the relay activates
   *only after* NeonBlue chooses the unseen group. The legacy script puts the
   cyan flare at page 4 panel 1 — before the crisis, before the choice. This
   inverts the issue's causal logic: the system appears to reward NeonBlue for
   showing up rather than for choosing well. **Conflict C-01.**
2. **Lil Devil does not cause the discovery.** The bible gives him the
   accidental reveal. In the legacy script the control box reacts to NeonBlue
   directly, and Lil Devil is reduced to a knuckle-crack and a hinge strike.
   **Conflict C-02.**
3. **Static and TwoTone drop out of the climax.** The bible has NeonBlue direct
   "Lil Devil's force, Static's warning, and TwoTone's route analysis." The
   legacy climax uses only Lil Devil.
4. **Scarline gets one line in the whole issue** (panel 2.3) and no function
   after it. The bible asks for two meaningful secondary actions, two functional
   beats and one observational role.
5. **Invented specifics not in any bible:** "five thousand people",
   "three main zones, eight rides", "a thirteen-year-old system". The last is
   the most serious — it dates the FusionZoo infrastructure, which the bible
   explicitly reserves ("Do not reveal the full history of FusionZoo
   infrastructure yet"). **Conflict C-04.**

### Script versus page plan

The script has **19 panels**. `page_panel_plan.json` and `metadata.json` have
**24**. Three panels in the art (P01_PANEL03, P06_PANEL03, P08_PANEL03) have no
script entry at all, and the script's page 4 full-bleed splash was expanded into
three equal standard panels. Nothing in the record reconciles the two.

The practical consequence: **there was no single authoritative panel list**, so
the art could not be checked against the writing.

---

## 2a. Legacy Issue 001 against the published editions *(the real target)*

The owner designated the three published Fiend Studios editions as the style
target on 2026-07-28. Measured against those, the legacy issue is not a weak
comic — it is not a comic.

| Dimension | Published editions | Legacy Issue 001 |
|---|---|---|
| Page architecture | Irregular grid, different every page, panels on a coloured board | One grid repeated on six of eight pages |
| Character integration | Drawn into scenes with cast shadows, occlusion, colour spill | Opaque cards in a row |
| Backgrounds | Illustrated interiors and exteriors with visible practical lights | Four plates, 19 reuses |
| SFX | Large, coloured, angled, overlapping borders | Small flat labels |
| Balloons | Colour-coded per speaker (Edition Two) | Uniform white |
| Splash usage | Reserved for genuine peaks | Specified, never produced |
| Cover | Title logo, tagline, featured character, Fiend Studios stamp | Draft-tier, no stamp |

**Edition Two is the closest analogue**: the Emo Monkey cast, at night, in dark
interiors, lit by cyan and green technology, with per-page coloured frames
carrying the emotional register. That is precisely the register Issue 001 needs.

---

## 2b. Legacy Issue 001 against Mango Pier *(secondary reference)*

| Dimension | Mango Pier | Legacy Issue 001 |
|---|---|---|
| Art tier | Finished house-style illustration | `draft_composite` — plates with pasted reference cards |
| Character rendering | Drawn into the scene | Opaque 220 px square cards in a row |
| Ground contact | Present, imperfect | **Absent** — cards float in a band |
| Backgrounds | ~14 distinct settings across 20 panels | **4 plates across 24 panels** |
| Style consistency | Consistent flat vector cartoon | Painterly neon plates + flat cartoon cards: two incompatible styles in one panel |
| Panel shapes | Mixed 1280×720, 1024×1024, 880×1184 | 22 of 24 at one aspect |
| Readable as a comic | Yes | No |

Mango Pier is a finished comic at a lower level than the published editions.
Legacy Issue 001 is a storyboard that was labelled, approved and published as if
it were finished. They are not the same kind of object, and the gap between them
is the whole problem.

### What Mango Pier gets wrong, and must not be copied

Mango Pier is a cast-consistency reference, not the style target and not a
staging reference. Its own defects, visible in
`source_material/visual_references/mango-pier/panels/`:

- **Front-facing row staging.** The dominant composition is two or three
  characters standing side by side, front on, feet on the same line, at the same
  scale, filling the lower half of frame. It recurs in roughly two thirds of the
  panels.
- **Baked-in furniture.** `P05_PANEL01`, `P07_PANEL01` and `P07_PANEL02` have a
  white "MonkeyZoo" logo bar rendered *inside* the panel art. `P07_PANEL01` has
  character name labels — "Moodz", "Emo", "NeonBlue" — baked into the
  illustration. Panel art must be frameless and textless.
- **White frames baked into the image** on several panels, which then sit inside
  the page's own frame.
- **Crowd extras rendered as featureless blobs** (`P03_PANEL01`, `P05_PANEL03`).
- **Very little camera variety.** Almost everything is eye level.

So: take the colour, line weight, character finish, palette and mood from Mango
Pier. Take nothing about how it stages a scene.

---

## 3. GENESIS and the integration upgrade

`GENESIS/` in the source factory holds a later issue (`MZ-2026-09-02`) with a
`panel_native` art directory and a collected PDF. More importantly,
`00_SYSTEM/integration_upgrade/` records the track that actually solved staging
— for Issue 02.

That track reports 96 integrated Issue 02 panels passing an integration
validator, built on true-alpha layers, calibrated ground planes, contact
shadows, reflections, relighting, depth haze and occlusion.

**None of it was ever applied to Issue 001.** Issue 001 was produced in July
2026 at draft-composite tier, published, and then superseded by a technique
improvement that was never back-applied. That is the single clearest
explanation for why Issue 001 looks the way it does, and it is good news: the
method exists and is proven on this cast.

---

## 4. The provenance failure

For every one of the 24 legacy panel IDs, **four different images exist**, none
matching by SHA-256:

| Location | Content |
|---|---|
| `.art-workspace/attempts/<panel>/attempt-*.png` | A draft composite, marked `"status": "preferred"`, `"actor": "project_owner"` |
| `generated_art/draft_composites/<panel>.png` | A *different* draft composite |
| `generated_art/selected_panels/<panel>.png` | Sometimes a draft composite, sometimes a raw generation artefact |
| `layout/print_layout/page_NN.png` | Built from something else again |

Measured: `selected == draft` 0/24, `selected == attempt` 0/24,
`draft == attempt` 0/24.

The clearest case is `MZ-2026-08-01_P01_PANEL02`:

- `.art-workspace` attempt: a competent draft composite of the festival grounds.
- `selected_panels`: a character model sheet of eight chibi figures on grey.
- The published page: **five off-model pink figures with tails and blue tube
  tops**, carrying Lil Devil's dialogue.

A directory named `selected_panels` contained unselected material, and the page
assembler drew from a fourth source. Banana Lab 2.0 answers this with ADR-002
and a single approved-asset path per panel.

---

## 5. What the comparison establishes

1. The **writing is largely sound** and the legacy script is worth rebuilding
   from rather than replacing.
2. The **art was never made.** There is nothing to salvage at panel level.
3. The **method to make it exists** and is proven on this cast — it was simply
   never applied here.
4. The **failure was a process failure**, not a talent or tooling failure: no
   single panel list, no single approved asset per panel, and a QA gate that
   could not see any of it.
