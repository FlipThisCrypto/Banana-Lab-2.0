# MonkeyZoo Prompt Rules
**Version:** 1.0 · **Last updated:** 2026-07-02

How every art prompt is constructed. The Art Director agent follows this file
mechanically; deviation = QA rejection (Rule 7).

---

## 1. Prompt Assembly Order (every panel, no exceptions)

```
[STYLE LOCK PHRASE]                        ← visual_style_bible.md §1, verbatim
+ [CHARACTER BLOCK per character]          ← token + design reminders from character_bible.md
+ [POSE + EXPRESSION]                      ← from script's action/emotion
+ [ENVIRONMENT BLOCK]                      ← from world_bible.md canon locations
+ [CAMERA + STAGING]                       ← angle, shot size, composition note
+ [LIGHTING + PALETTE]                     ← scene mode or card mode
+ [BUBBLE SPACE NOTE]                      ← where lettering will go
```

Negative prompt = BASE NEGATIVE (visual_style_bible.md §8) + per-panel appends.

## 2. Character Blocks

- Always use bible prompt tokens (`mz_moodz`, `mz_twotone`, …) AND restate the
  3–4 identity anchors in words (LoRA/token can drift; words backstop it).
  Example: `mz_moodz, pale-faced monkey with black emo fringe and blue streak,
  grey eye rings, black studded cuffs, platform boots`
- Max 3 named characters per generated panel. Crowds are generated as separate
  background plates or use faction tokens with "faceless background" phrasing.
- NEVER describe a lead with adjectives that imply design change ("battle-worn",
  "older", "cool new jacket"). Wardrobe = bible wardrobe.

## 3. Identity Stack (Rule: never text-prompt alone for recurring characters)

Priority order per character, use the highest available tier:
1. **Character LoRA** (`MZ_<Name>_v1.safetensors`) at 0.7–0.9 weight
2. **IPAdapter** with 2–4 approved refs from `03_APPROVED_CANON/approved_characters/<name>/`
3. Token + verbal anchors only — allowed ONLY while refs are being built,
   flagged `identity_tier: "text-only"` in the prompt pack for QA scrutiny.

## 4. Composition Control

- Panels where staging matters (any panel with 2+ characters, action, or a
  specified camera angle) require ControlNet:
  - `openpose` for character poses (pose refs in `references/pose_refs/`)
  - `depth` for staging/foreground-background separation
  - `canny` or `lineart` when matching a layout sketch
- Splash pages and covers ALWAYS use a composition sketch + canny/depth.

## 5. Seed Strategy

- `per_character_base`: each lead has a base seed (Moodz 100001, TwoTone
  100002, Static 100003, Ash 100004, NeonBlue 100005, Scarline 100006) used
  for solo close-ups to stabilize faces.
- `per_panel`: multi-character/action panels use seed = issue number ×10000 +
  page×100 + panel (e.g., MZ-…-05 p3 panel 2 → 50302). Recorded in the pack.
- Reroll policy: vary seed ±1..9 only; if 10 rerolls fail QA, escalate to
  inpainting or pose-ref change instead of prompt mutation.

## 6. Resolution & Model Settings (ComfyUI defaults)

- Panel gen: 1024×1024 base (square), 1216×832 (wide), 832×1216 (tall);
  upscale 2× (real-ESRGAN or model upscaler) to print res after approval.
- Sampler defaults: 28–34 steps, CFG 5.5–7. Style consistency beats prompt
  obedience: when in conflict, lower CFG.
- Covers: generate at 1664×2432 minimum (portrait), upscale to 2480×3508.

## 7. Text in Images

- NEVER generate dialogue, captions, or SFX inside the image. All text is
  applied at lettering stage. Signage is the ONLY allowed in-image text and
  only from the approved signage list (world_bible.md §6); if the model
  mangles it, inpaint or replace in edit.

## 8. Reference Requirements (every panel lists them)

- `references_required` must name actual files/folders the operator loads:
  character refs, location ref (previous approved panel of same location if it
  exists — background continuity), pose ref if ControlNet is used.
- First appearance of a location in an issue: generate 1 establishing plate,
  get it QA-approved, then reference it for every later panel in that location.

## 9. Forbidden Prompt Language (auto-reject)

- Artist names, show names, "in the style of <IP>"
- "photorealistic", "hyperdetailed", "8k", "masterpiece" quality-spam
- Any wardrobe/feature not in the character bible (Rule 6)
- Emotion words contradicting the script's emotion field
- "and friends", "various monkeys" — every character is either a named lead,
  a faction token, or explicit "faceless background silhouettes"
