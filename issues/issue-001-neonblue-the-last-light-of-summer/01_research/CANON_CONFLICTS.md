# Issue 001 — Canon Conflicts

Conflicts between sources, how each was resolved, and which ones a human must
rule on before production continues.

## Resolution order

When sources disagree, Banana Lab 2.0 applies this order, recorded in
`canon/rules/CANON_PRECEDENCE.md`:

1. **Approved canon** (`03_APPROVED_CANON` imports) — visual identity and
   approved assets.
2. **Character bibles** — who a character is, how they speak, what may never
   change about them.
3. **Story bibles** — what happens, in what order, and why.
4. **Older published issues** — supporting evidence only.
5. **Legacy production records** — evidence of what was attempted, never
   authority.

Nothing below was resolved by invention. Where the sources genuinely do not
settle the question, the conflict is marked `UNRESOLVED` and escalated.

---

## C-01 — Echo reveal timing *(BLOCKING — owner decision required)*

**Sources in conflict**
- Season bible §7 "Echo reveal": *"The relay activates **only after** NeonBlue
  chooses the unseen group over the public spotlight."*
- Legacy script panel 4.1: the control box flares cyan on page 4, at the
  midpoint, *before* the crisis and before any choice.

**Why it matters** This is not a scheduling detail. The bible's whole thesis is
that the Echo responds to a *choice*. Firing the reveal on proximity says the
system responds to NeonBlue's presence — which makes him special by default
rather than by what he does, and undercuts the answer the issue delivers
("hope is not ignorance; it becomes stronger when it makes room for risk").

**Recommended resolution** Follow the season bible. Page 4 gets a *partial,
ambiguous* reaction — a flicker that could be coincidence, that Lil Devil's
interference triggers — and the true cyan activation lands after the rescue on
page 8.

**Status** Recommended resolution applied to the rebuilt bible and script,
flagged for owner confirmation. Reversing it changes pages 4, 7 and 8.

---

## C-02 — Lil Devil's guest function *(BLOCKING — owner decision required)*

**Sources in conflict**
- Season bible §7: *"Lil Devil's impatience accidentally reveals that the
  failures are not random. The control system reacts differently when NeonBlue
  approaches."* Guest tracking §14: *"Does not cause the core problem or
  complete the rescue."*
- Legacy script: Lil Devil cracks his knuckles (1.2), grabs a gate (4.1) and
  strikes a hinge (7.2). He never causes the discovery.

**Why it matters** Without the accidental reveal, Lil Devil has no story
function — he becomes a hammer NeonBlue points at things. The bible's growth
seed for him ("learns that restraint can direct power") needs him to first act
without restraint and have it *teach the team something*.

**Recommended resolution** Restore the bible's version. Lil Devil forces the
service gate early against advice; the system's reaction to that interference —
not to NeonBlue's presence — is what exposes the pattern.

**Status** Recommended resolution applied, flagged for owner confirmation.

---

## C-03 — Ash's line

**Sources in conflict**
- Season bible §7: *"Hope can read warnings."* — offered as *"a proposed line,
  not a required catchphrase."*
- Legacy script 4.1: *"Hope reads warnings first."*

**Resolution** Use the bible's wording. The bible explicitly permits change, but
there is no reason to drift from an approved line, and "can read" carries the
meaning the scene needs — permission, not priority.

**Status** RESOLVED. No owner decision required.

---

## C-04 — "A thirteen-year-old system"

**Sources in conflict**
- Season bible §3 mystery rules: *"Do not reveal the full history of FusionZoo
  infrastructure yet."*
- Legacy script 8.2: *"Why did a thirteen-year-old system recognize me?"*

**Why it matters** A specific age dates the infrastructure and constrains five
later issues. Issue 003 is scheduled to establish that the signal belongs to an
older FusionZoo system; Issue 006 preserves its origin as the season's
remaining question. A number stated in Issue 001 forecloses both.

**Resolution** Remove the number. The line becomes a question about
recognition, not about age.

**Status** RESOLVED. No owner decision required.

---

## C-05 — Panel count: 19 versus 24

**Sources in conflict**
- Legacy `issue_script.md`: 19 panels across 8 pages.
- Legacy `page_panel_plan.json` and `metadata.json`: 24 panels.
- Season bible §18: recommends 8 pages, ~20 panels, 2–4 per page.

**Resolution** Rebuild to the season bible's recommendation. The rebuilt issue
is **8 pages, 20 panels**, with a deliberately varied distribution (see
`05_layouts/layout-spec.yaml`). Neither legacy number is authoritative because
neither was reconciled with the other.

**Status** RESOLVED.

---

## C-06 — Scarline's role

**Sources in conflict**
- Season bible §7: Scarline *"warns the team not to assume the crowd's panic is
  the real danger."* §5 requires every supporting character to have a purposeful
  function.
- Legacy script: one line on page 2, then nothing.

**Resolution** Give Scarline a second, load-bearing beat. Her season function is
*validation* — helping others recognise their own correct choice. Placing that
at NeonBlue's decision point serves both characters and costs no extra panel.

**Status** RESOLVED.

---

## C-07 — Who is trapped in the corridor

**Sources in conflict**
- Season bible §7: *"A younger character or small group is trapped in a dark
  service corridor."* Deliberately unspecified.
- Legacy script 6.2: "trapped fairgoers", unnamed and unrendered.
- Legacy art: nobody is depicted at all.

**Why it matters** The rescue is the climax. If the trapped group is anonymous,
the reader has nothing to care about, and NeonBlue's choice costs him nothing
emotionally. But naming a *character* risks inventing canon.

**Resolution** Use a small group of unnamed young festival-goers — no new named
character, no new canon — but make them **specific and visible**: three
individuals with distinct silhouettes and readable faces, established in one
panel before the rescue so the payoff has someone in it. This satisfies the
bible without adding to canon.

**Status** RESOLVED, with a production requirement: these extras do not exist as
art and must be created. Recorded in `07_character_staging/missing-assets.md`.

---

## C-08 — Panel density exceeds the season bible's per-page guidance

**Sources in conflict**
- Season bible §18: *"Recommended standard: 8 pages, 20 panels, 2 to 4 panels
  per page."*
- Rebuilt script: 8 pages, **27 panels**, distributed 3 / 3 / **5** / 3 / 3 / 3 /
  **4** / 3.
- Owner-designated house style (2026-07-28): the published editions run denser
  and far more varied. Edition One page 5 carries roughly eight panels; its
  eleven pages never repeat a grid.

**Why it matters** The brief's central visual complaint about the previous issue
is uniformity — one grid repeated on six of eight pages. Holding to 2.5 panels
per page would flatten the rhythm in exactly the direction that caused the
problem. The published editions demonstrate that the house style tolerates, and
benefits from, dense pages next to sparse ones.

**Resolution** Adopt 27 panels. Page 3 (five panels) is the issue's fastest
page and its density is the point — four quick observations before a wide
anchor. Page 7 (four panels) is the action page. Everything else sits at three.
The season bible describes this as a *recommended standard* and explicitly
states it "should remain compatible with adjustable issue lengths."

**Cost accepted** Page 3 exceeds the stated 2–4 range by one panel.

**Status** RESOLVED as a recorded, deliberate deviation. Flagged for owner
awareness rather than owner decision — reverting to 20 panels is possible but
would require cutting four beats that currently have stated jobs.

---

## Note — no full-page splash

The season bible asks for *"one splash or large reveal panel per issue"*, and
the published editions use full-page splashes freely.

This issue uses **large anchor panels** rather than a full-page splash:
`ISSUE001-P03-05` (the pattern from above), `ISSUE001-P06-03` (the decision),
`ISSUE001-P07-04` (the rescue) and `ISSUE001-P08-03` (the final image).

**Reasoning** On an 8-page issue a full-page splash costs an eighth of the page
budget, and this issue's peak is a quiet decision rather than a spectacle. A
full page given to a character standing still between two lights would read as
a poster, not a beat. The season bible's requirement is satisfied by the "large
reveal panel" alternative it explicitly offers.

This is an art-directed choice, recorded so it is visible rather than
accidental. If the owner wants a true splash, `ISSUE001-P06-03` is the panel
that would carry it.

---

## Summary

| ID | Conflict | Status | Owner decision |
|---|---|---|---|
| C-01 | Echo reveal timing | Recommended resolution applied | **Required** |
| C-02 | Lil Devil's guest function | Recommended resolution applied | **Required** |
| C-03 | Ash's line wording | Resolved | No |
| C-04 | "Thirteen-year-old system" | Resolved | No |
| C-05 | Panel count 19 vs 24 | Resolved | No |
| C-06 | Scarline's role | Resolved | No |
| C-07 | Identity of the trapped group | Resolved | No |
| C-08 | 27 panels vs the recommended 20 | Resolved as a recorded deviation | No |

**Two conflicts require an owner ruling before art production begins.** Both are
recorded in the rebuilt issue bible under `canon_conflicts` with
`requires_owner_decision: true`. Work on research, bible, script, layouts and
background production can proceed while they are open; character staging for
pages 4, 7 and 8 cannot be finalised until they are settled.
