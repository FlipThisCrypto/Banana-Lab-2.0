# ADR-004: Backgrounds first, characters composited into them

**Status:** Accepted · **Date:** 2026-07-28

## Context

Two facts drove this.

**One:** there is no MonkeyZoo style LoRA, and the two installed checkpoints are
photorealistic and anime. Text-to-image cannot reliably produce the house style,
and certainly cannot hold a character across 103 panels.

**Two:** legacy Issue 001 generated background plates, then pasted opaque
character reference cards in a row near the bottom. No ground contact, no
shadow, no perspective, no light match. The characters were displayed beside the
scene, not in it.

Meanwhile the source project's own integration track had already built the
alternative — true-alpha layers, calibrated ground planes, contact shadows,
relighting, occlusion — and proven it on 96 panels of Issue 02. It was never
applied to Issue 001.

## Decision

Panels are assembled in this order:

1. **Calibrate the plate.** Horizon, a named scale reference object, light
   direction and colour, ground surface, traced occluders.
2. **Produce the background plate.** Frameless, textless, no characters.
3. **Select the character layer.** From approved true-alpha art. Generate a new
   candidate only when nothing covers the beat.
4. **Stage.** Position, depth plane, scale against the named reference, ground
   contact, eye line, hands, occlusion.
5. **Integrate.** Contact shadow, cast shadow, relight to the plate's key,
   environmental colour spill, edge treatment, depth softness.
6. **Assemble.** Panel art into the layout box. Borders, balloons, captions,
   SFX and page furniture are added downstream, never rendered into the art.

The panel schema makes steps 1, 3 and 5 mandatory: `character_blocking` requires
`ground_contact`, `eye_line` and `scale_note` per character, and `lighting`
requires `key_direction`, `key_color`, `fill` and `contact_shadow`.

## Consequences

**Good**

- Character identity comes from art the owner approved.
- QA has something specific to check against, rather than an impression.
- Layers and masks are retained, so defects are repaired without regenerating.
- Frameless art makes irregular page layouts possible without new renders.

**Costs**

- More steps than one prompt per panel.
- Every location plate needs calibrating before any character stands in it. No
  festival plate is calibrated yet — this is the first production task.
- Scenes where a character must physically interact with the environment need
  inpainting on top of compositing.

## Alternatives rejected

- **Monolithic single-prompt panels.** How legacy Issue 001 was made.
- **img2img edge unification.** Tested and rejected by the source project with
  measured identity drift and hallucination at cfg 1.0. Do not retry.
