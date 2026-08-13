# Visual Quality Review

**Authority: owner-mandated, 2026-08-13.**

Review each generated panel and completed page as a **comic reader and art
director**, not as a technical validator. Passing automated checks does not
mean the artwork is visually successful.

**Automated PASS does not authorize production. A human visual review must
also PASS.**

This is ADR-005 applied to pictures. The scorecard, likeness metric, layout
geometry, and `validate` can only reject. None of them can say the page is a
comic.

---

## What this is not

- It is not a likeness score against one reference crop.
- It is not an 8/8 aesthetic-scorecard result.
- It is not file existence, dimensions, or hash match.
- It is not a machine assigning `APPROVED`.

A panel can pass likeness, dimensions, safe-zone, palette, and geometry checks
and still be a bad panel. Conversely, a deliberate artistic choice may depart
slightly from a numerical target while clearly improving storytelling.
Automated measurements identify risks. Final approval considers the actual
visual result.

---

## What to look for

### Presence in the scene

Characters must feel like they **exist inside the environment**, not pasted,
floating, oversized, undersized, or disconnected. Canonical design stays
faithful. Environmental lighting, contact shadows, reflected light, atmosphere,
occlusion, and depth make the character occupy the same physical space as the
background.

Do **not** solve integration by globally recolouring or heavily grading the
character. Prefer lighting and compositing that change how the environment
meets the figure while the underlying design stays recognisable.

### Scale and perspective

Feet meet the ground plane. Size makes sense for camera distance and for nearby
people, architecture, props, and other characters. Figures at different depths
must not look independently resized.

### Lighting consistency

Ask where the dominant light comes from, what colour it is, how strong it is,
and whether the character responds. Key, rim, bounce, shadow direction, shadow
softness, nearby practicals. Not photoreal — believable.

### Composition and hierarchy

The reader should immediately understand what matters. Background supports the
beat rather than competing with it. Placement is intentional, not centred by
default. Avoid lineup compositions, identical camera distances, excessive
symmetry, and characters that only face the viewer.

### Poses and staging

Characters are doing something, reacting, looking somewhere meaningful, carrying
weight, or touching the world. A sticker pose — removable and droppable onto
any other plate unchanged — is a fail.

### Depth

When the shot calls for it: foreground, midground, background. Overlap, scale,
atmosphere, focus, light, occlusion. Characters sometimes pass *behind*
environment when that is physically right.

### Emotional readability

Pose, expression, camera, distance, light, and composition communicate the beat
**before dialogue**. If the panel needs text to explain the feeling or the
thing the reader should notice, the visual storytelling is too weak.

### Continuity

Time of day, light progression, geography, position, travel direction, props,
clothing, expression, injuries, environmental state. Individual panels can look
excellent and still fail as sequential art.

### Page rhythm

Variation in shot size, composition, density, negative space, arrangement.
Important beats get more space. Quiet moments need room. Dense pages stay
readable. Page turns keep their intended impact.

### Lettering space

Faces, hands, important objects, clues, action, and story-critical detail must
not sit in reserved balloon areas. Do not assume lettering can move later. The
art provides usable negative space.

### Style without sameness

Characters and environments may use different rendering techniques. The goal is
not one technique. The goal is that the combination feels like one comic.

### The "something is off" catch

Malformed extras, impossible architecture, inconsistent object geometry,
duplicated crowd members, nonsensical signage, strange tangencies, broken
hands, merged objects, unexplained lights — the things numerical validators
miss.

---

## Five-question final test

A human answers these of every panel and every assembled page. Any **no** is a
fail. The machine may not answer them.

1. Does my eye immediately go where the story wants it to go?
2. Do the characters look like they physically belong in this space?
3. Can I understand the action or emotion without reading the dialogue?
4. Does this panel feel connected to the panels before and after it?
5. Does anything look accidentally AI-generated, pasted together, physically
   impossible, or visually distracting?

---

## Record

Human review is written by hand to:

```
issues/<issue>/12_qa/visual-review.yaml
```

Schema: `config/schemas/visual-review.schema.yaml`.

Permitted verdicts: `not_started`, `in_progress`, `changes_required`,
`human_pass`.

`human_pass` may be written only by a named person, answering all five
questions `yes`, at print size, with the artwork in front of them.

No script in this repository writes `human_pass`. `validate` rejects:

- a `human_pass` whose `actor` is empty, `pipeline`, `validate`, `scorecard`,
  or any other machine identity
- a `human_pass` that cites only automated evidence
- a final issue approval (`approvals.approval.approved: true`) without a
  current `human_pass` whose `evidence_hash` matches the reviewed pages

A missing record means **not reviewed**. Absence is not a pass.
