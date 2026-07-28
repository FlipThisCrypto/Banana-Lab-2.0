# Issue 001 — Location and Prop Requirements

What the issue needs, what exists, and what has to be made.

---

## Locations

Four approved locations, all 1280×720, each with a `bible.md`, all imported to
`source_material/imported_canon/approved_locations/`.

| Location ID | Plate | Pages | Panels |
|---|---|---|---|
| `LOC-festival-grounds` | `festival-grounds/primary-reference.png` | 1, 2, 3, 8 | 9 |
| `LOC-festival-main-stage` | `festival-main-stage/primary-reference.png` | 1, 6 | 2 |
| `LOC-festival-control-node` | `festival-control-node/primary-reference.png` | 4, 7 | 5 |
| `LOC-festival-service-corridor` | `festival-service-corridor/primary-reference.png` | 5, 6, 7 | 4 |

### The problem

**Four plates cannot carry twenty panels.** The legacy issue tried and produced
eight pixel-identical uses of the festival-grounds plate — including page 1 and
page 8, so the closing "reduced festival" looked exactly like the opening
arrival.

### The requirement

**Twelve distinct camera setups**, derived from the four approved locations.
New plates extend the *camera*, not the *place*: same architecture, same
landmarks, same palette, different vantage.

| Location | Setups needed | Purpose |
|---|---|---|
| Festival grounds | 4 | Wide arrival (warm), mid booth row (failing), high angle over the darkening grounds, closing wide (half-lit) |
| Main stage | 2 | Distant establishing, and a low angle from the crowd during the countdown |
| Control node | 3 | Wide on the gate, close on the control box, reverse over the team |
| Service corridor | 3 | Deep one-point down the corridor, close on the relay marker, low angle at the shutter |

Deliberate reuse is fine where a scene should read as one continuous place —
page 4's three panels share a location and should feel like it. Reuse across
pages 1 and 8 is not fine, because the story says the lighting changed.

### Calibration gap

`imported_canon/plate_calibrations/` contains ground-plane and horizon data for
four locations — **none of them festival locations**. They are
`old-relay-junction`, `school-pa-zone`, `storm-routines` and
`transit-announcement-hub`.

Every festival plate needs a calibration built to the same format before any
character can be staged into it with defensible scale. **This is the first
unblocked production task.**

Each calibration must record: horizon Y, a named reference object with its pixel
height and foot position, the resulting character-height factor, the primary
light direction and colour, ground surface type (for reflection behaviour), and
any traced occluders characters can stand behind.

---

## Props

Six props are load-bearing. All exist as approved single primary views.

| Prop ID | Panels | Role | Continuity lock |
|---|---|---|---|
| `PROP-festival-backup-panel` | P2-02 | The thing NeonBlue guarantees | Must look capable, so its failure lands |
| `PROP-service-gate` | P2-03, P4-01, P7-03 | Lil Devil forces it; later struck at the hinge | Same gate all three times. The hinge NeonBlue marks must be visible in P7-03 |
| `PROP-control-box` | P4-01, P4-02 | Reacts to interference | Amber status light normally. The page-4 flicker is ambiguous, not a full cyan flare |
| `PROP-cyan-relay-marker` | P5-01 | Carries Patch's frequency | The most important object in the issue. Must be readable at panel size and legible as *old* without being dated |
| `PROP-public-projection-screen` | P3-02 | Shows fractured cyan | The fracture must be visible in the art, not only in the caption |
| `PROP-echo-symbol` | P8-02 | One segment lights | **Exactly one segment. Partial, off-centre, unmistakably incomplete.** |

### Prop gaps

| Need | Status |
|---|---|
| Service gate, damaged state | Only the intact view exists. P7-03 needs it struck open |
| Control box, ambiguous-flicker state | Only the neutral view exists |
| Relay marker, close-up detail | Primary view may not hold up at close shot size |
| Echo symbol, single-segment-lit state | Only the full symbol reference exists. **A single-segment version must be authored, and the full symbol must never appear** |

---

## Extras and crowd

The festival is a crowded event and the issue has no crowd assets.

| Need | Panels | Requirement |
|---|---|---|
| Background festival crowd | P1-01, P3-01, P6-01, P8-01 | Simplified silhouettes and distant figures. **Not** the blob shapes used in Mango Pier — readable as people, clearly not cast |
| Main stage audience | P6-01 | Mass, from behind, backlit by the stage |
| **Three trapped young festival-goers** | P6-02, P7-03 | Distinct silhouettes, readable faces, no new named canon. Established in P6-02 so the P7-03 payoff has someone in it |

The three trapped figures are the highest-value new asset in the issue. Without
them, the climax is a rescue of nobody.

---

## Character asset requirements

Full analysis in `../07_character_staging/`.

| Character | Alpha layers available | Gap |
|---|---|---|
| NeonBlue | 17 | Needs at least one honest-plan pose and one close reaction |
| Moodz | 18 | Adequate |
| TwoTone | 19 | Adequate |
| Static | 19 | Adequate |
| Ash | 18 | Adequate |
| Scarline | 17 | Adequate |
| **Lil Devil** | **0** | **Blocker.** The guest has no alpha layer at all |

Lil Devil has approved character art (31 files) but no background-removed layer.
Producing his layer set is the second unblocked production task.

---

## Summary of what must be made

| Item | Count | Priority | Blocked by |
|---|---|---|---|
| Festival plate calibrations | 4 | 1 | Nothing |
| Lil Devil alpha layer set | ~8 poses | 1 | Nothing |
| New camera-angle plates | 8 (to reach 12) | 2 | Layout approval |
| Three trapped festival-goers | 3 figures | 2 | Layout approval |
| Crowd silhouette set | 1 set | 3 | Layout approval |
| Prop state variants | 4 | 3 | Layout approval |
| Echo single-segment art | 1 | 3 | Owner ruling on C-01 |
| NeonBlue gap poses | ~2 | 3 | Staging plans |
