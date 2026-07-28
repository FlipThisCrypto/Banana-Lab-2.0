# MonkeyZoo Master Bible
**Version:** 1.0 · **Last updated:** 2026-07-02 · **Owner:** Fiend Studios

This is the top-level source of truth for the MonkeyZoo monthly comic system.
If any document conflicts with this one, THIS ONE WINS. If this one is silent,
the specialized bibles win in this order:

1. `continuity_ledger.md` — what has already happened (events beat everything)
2. `character_bible.md` — who the characters are
3. `world_bible.md` — how the world works
4. `visual_style_bible.md` — how everything looks
5. `prompt_rules.md` — how prompts are written

---

## 1. What MonkeyZoo Is

MonkeyZoo is a comic / NFT / IP project by **Fiend Studios** featuring recurring
cartoon monkeys in a dark cartoon sci-fi / cyberpunk world. Tone: humor, satire,
serialized storytelling, real emotional character arcs underneath the jokes.

- **Publisher / studio:** Fiend Studios (Twitter/X: `@fiendstudios`)
- **Comic collection:** FlipThisComics (collection id `f532c517-15b7-4b4a-ae2c-b714e6067de8`)
- **Chain / marketplace:** Chia blockchain · MintGarden (`https://mintgarden.io/TheWardedOnes`)
- **NFT metadata format:** CHIP-0015 (older issues used CHIP-0007)
- **File hosting:** IPFS via Filebase (`defiant-black-skink.myfilebase.com`)
- **Watermark/signature:** "MonkeyZoo" script logo, bottom of art; Fiend Studios stamp on covers

## 2. Series Format

- One issue per month. Default **8 story pages** (range 6–16), plus:
  front outside cover, front inside cover, rear inside cover, rear outside cover (teaser).
- Every issue ends with a **teaser for the next issue** on the rear outside cover.
- Issues are educational-adjacent satire: the story works on its own, and the
  world's tech (FusionZoo) mirrors real blockchain/NFT concepts without ever
  turning into a lecture.

## 3. The Cast (Fusion Squad — Emo Faction core)

Six recurring leads. Full specs in `character_bible.md`.

| Character | Role | One-line personality |
|---|---|---|
| **Moodz** | Protagonist | Emotionally expressive, guarded, skeptical, observant |
| **TwoTone** | Support | Balanced, analytical, emotionally split but controlled |
| **Static** | Support | Anxious, overstimulated, talks fast, reacts strongly |
| **Ash** | Support | Quiet, emotionally drained, speaks rarely |
| **NeonBlue** | Support | Optimistic on the surface, insecure underneath |
| **Scarline** | Observer | Grounded, experienced, speaks with clarity and restraint |

The wider MonkeyZoo universe contains **factions/archetypes** seen in the PFP
collection: Emo, Zombie, Super, Clever, Cheeky, Lil Devil. Factions may appear
in issues, but the six leads above carry the monthly book.

## 4. Canon Timeline (published editions)

| # | Title | What happened (canon) |
|---|---|---|
| 1 | *The Battle Against Inefficiency and Centralization* | Introduced FusionZoo technology: dynamic combining, upgrading, and safe reversal (de-fusion) of assets. Squad breaks the static/expensive old world. |
| 2 | *The De-Fusion Tapes* | Set in **The Annex**, a forgotten corner of the Fusion Lab. The Emo Faction dissects the hype: singletons, provenance, nesting, offer files, security, Chialisp. Climax: a clean, surgical de-fusion restoring every asset. Establishes the faction's creed: trust the undo button. |
| 3 | *The First Run of the Year* | Winter edition. Five riders, one slope, no resets, no shortcuts. FusionZoo logs the run and powers down without judgment. Theme: progress is a direction, not a moment. |
| 4 | *STILL ME* (Emo Monkey Edition 4) | The squad enters the public FusionZoo facility ("UPGRADE YOURSELF"). Fusion sync overwhelms Moodz ("I don't feel like me") — he shouts STOP and aborts the fusion. Everyone leaves unchanged, by choice. Scarline validates him: "You stopped it in time." Moodz: "Maybe later." TwoTone: "Your terms." **Rear-cover teaser: Zombie Monkey — "Not everyone walks away." Green light leaks from a cracked fusion chamber.** |

**Open threads** (must be honored or explicitly deferred each month) are tracked
in `continuity_ledger.md` → *Open Threads*.

## 5. Themes the Series Keeps Returning To

- Identity vs. optimization: you don't have to become *more* to matter.
- Consent and reversibility: "Fusion is optional. Until it isn't."
- Satire of hype, FOMO, upgrade culture, and systems that monetize insecurity.
- Found-family loyalty inside a cold, glowing, corporate world.

## 6. Hard Rules of the Franchise

1. Never redesign a main character without an explicit redesign issue.
2. Never change a character's core color palette.
3. Never change the visual style lock phrase (see `visual_style_bible.md`).
4. Never introduce new lore without writing it into `continuity_ledger.md`.
5. Never use a generated image as canon until it passes Art QA.
6. Never let the art model invent costumes, props, tattoos, scars, or facial features.
7. Never use one-off prompt language that conflicts with the visual bible.
8. Every panel prompt must reference the character bible tokens.
9. Every issue must update the continuity ledger before release.
10. Every final package must include source files, exports, prompts, and QA notes.

## 7. Production Pipeline (summary)

Idea → Intake → Continuity → Showrunner → Script → Art Director → Art Generation
(ComfyUI) → Art QA → Layout & Lettering → Final QA → Release → Archive.
Full operation manual: `../README.md`. Agent prompts: `agents/stage_01…stage_10`.

## 8. Expansion Paths (design for these, don't block them)

Daily strips · short-form video · NFT metadata · collector editions ·
character cards · social campaigns · animated shorts · music tie-ins.
Every issue's `page_panel_plan.json` and `art_prompt_pack.json` must stay
machine-readable so these can be generated from the same source.
