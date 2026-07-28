# Issue 001 — Script Continuity Check

Checks run against the completed script, before it goes to the owner.

Measured values come from `python -m app.cli.main validate` and from the
generated `dialogue-only.md` summary. Judgement calls are marked as such.

---

## 1. Structure

| Check | Required | Actual | Result |
|---|---|---|---|
| Page count | 8 | 8 | PASS |
| Panel count | 27 (per C-08) | 27 | PASS |
| Panels per page | Varied | 3 / 3 / 5 / 3 / 3 / 3 / 4 / 3 | PASS |
| Panel IDs unique | Yes | 27 unique | PASS |
| Schema validation | All panels | 27/27 | PASS |
| Every character in frame has a staging record | Yes | 27/27 | PASS |

---

## 2. Panel rhythm

| Dimension | Distribution |
|---|---|
| Panel sizes | small 11, medium 9, large 7 |
| Panel shapes | wide 11, rectangle 9, tall 4, inset 2, square 1 |
| Camera shots | wide 7, medium 5, extreme_wide 3, medium_close 3, insert 2, close 2, extreme_close 2, medium_wide 2, two_shot 1 |
| Camera angles | eye_level 15, low_angle 9, high_angle 2, birds_eye 1 |
| Silent panels | 5 — P03-04, P03-05, P05-03, P06-01, P08-02 |

**Assessment** Nine distinct shot sizes across 27 panels, ranging from
extreme_close on a relay marker to birds_eye over the whole festival. No two
consecutive pages share a grid. Five silent panels, where the legacy version had
none.

**Deliberate absence** No full-page splash. Reasoning recorded in
`../01_research/CANON_CONFLICTS.md`.

---

## 3. Dialogue

| Check | Required | Actual | Result |
|---|---|---|---|
| Balloons over 15 words | 0 | 0 | PASS |
| Average balloon length | ≤ 15 | 7.1 | PASS |
| Max balloons per panel | 2 | 2 | PASS |
| Total balloons | — | 27 | — |

Compare with the legacy script, whose lines ran 18–25 words.

### Speaking distribution

| Character | Balloons | Bible expectation | Result |
|---|---|---|---|
| NeonBlue | 9 | Featured — decision, reveal, closing beat | PASS |
| Lil Devil | 3 | Guest — pressure, no resolution | PASS |
| Static | 3 | Functional beat | PASS |
| TwoTone | 2 | Meaningful secondary | PASS |
| Scarline | 2 | Observational | PASS |
| Moodz | 2 | Meaningful secondary | PASS |
| Ash | 1 | Functional beat | PASS |

Ash speaks once, which is correct for him. The season bible warns against making
him talkative to carry exposition; he carries none.

---

## 4. Canon compliance

| Rule | Result |
|---|---|
| Patch named but not resolved | PASS — named once, P05-01, never discussed |
| Exactly one Echo segment lit | PASS — P08-02, explicitly one, full symbol never shown |
| No FusionZoo dating | PASS — "thirteen-year-old" removed |
| No glasses on any character | PASS — Clever does not appear |
| Scarline has no facial scar | PASS |
| Echo activates after the choice | PASS *(subject to owner ruling C-01)* |
| Guest does not solve the problem | PASS — Lil Devil causes a discovery and applies directed force |
| Guest does not complete the rescue | PASS — NeonBlue counts them out, P07-04 |
| Static's alarm is real | PASS — correct in all three beats |
| No injury to the trapped group | PASS |
| One running gag maximum | PASS — over-volunteering, twice, then dropped |
| No catchphrases | PASS |
| Wardrobe unchanged throughout | PASS |
| Single continuous evening | PASS |

---

## 5. Season setup

| Requirement | Where | Result |
|---|---|---|
| Six-part pulse for Issue 002 | P03-02 | PASS — six countable elements required in the art |
| Cyan frequency recognisable again | P03-02, P05-01, P08-02 | PASS |
| "Why did it recognise NeonBlue?" left open | P08-03 | PASS |
| Patch thread opened, unresolved | P05-01 | PASS |
| Five segments remain dark | P08-02 | PASS |
| System never speaks or commands | Throughout | PASS |

---

## 6. Light progression

The title is a lighting instruction. Verified panel by panel:

| Page | Required | Script |
|---|---|---|
| 1 | Low warm sun, festival lights coming on | Deep amber key, long shadows toward camera |
| 2 | Sun gone, artificial and patchy | Amber dying left to right; first cyan at the gate |
| 3 | Cooling, cyan taking over | Cyan dominant by P03-02 |
| 4 | Full night, hard sources | Cyan underlight dominates the page |
| 5 | Darkest, isolated | Near-black with two small sources |
| 6 | Near-monochrome, one red practical | Single red source; dual-source only at the decision |
| 7 | Working light returning | Torchlight from floor level, warm |
| 8 | Restored but reduced | Warm and cyan coexisting, neither winning |

**PASS.** No literal sunset appears after page 1, which is correct — pages 4
through 7 are interior or after dark.

---

## 7. Cyan discipline

Cyan is reserved for the system. Verified: cyan appears in P02-03 (gate
worklight, deliberately unremarkable), P03-02, P04-01, P04-02, P04-03, P05-01,
P08-02, P08-03. It does **not** appear in the festival's own decorative palette,
which is amber, magenta and warm white.

**PASS**, with a production note: the location plates must be generated with
cyan excluded from festival decoration, or this discipline is lost at the
background stage.

---

## 8. Known open items

| Item | Type | Blocks |
|---|---|---|
| C-01 Echo reveal timing | Owner ruling | Final art on pages 4 and 8 |
| C-02 Lil Devil's guest function | Owner ruling | Final art on pages 2, 4 and 7 |
| Edition number for the cover stamp | Owner decision | Cover only |
| Balloon colour assignment per speaker | Owner decision | Lettering only |
| Lil Devil has no alpha layer | Asset gap | Any panel with Lil Devil |
| Three trapped festival-goers do not exist as art | Asset gap | P06-02, P07-04 |
| No festival plate is calibrated | Asset gap | All character staging |
| Crowd silhouette set does not exist | Asset gap | P01-01, P02-01, P03-03, P06-01, P08-01 |

None of these blocks storyboarding or layout.

---

## 9. Verdict

The script is **structurally complete and canon-compliant**, subject to two
owner rulings that change specific panels rather than the story.

It has not been approved. `13_approved/approval-record.yaml` does not exist, and
the script gate remains open.
