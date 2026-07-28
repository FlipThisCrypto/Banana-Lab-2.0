# Incident — imported source material mutated

**Date:** 2026-07-28 · **Severity:** `BLOCKER` · **Code:** `PROC-SOURCE-MUTATED`
**Status:** Resolved, cause closed.

---

## What happened

81 files under `source_material/imported_canon/approved_characters/` were
modified in place. The affected files were the numbered turnaround and
expression sets for the six Emo Monkeys:

| Character | Files changed |
|---|---:|
| Ash | 14 |
| NeonBlue | 14 |
| Scarline | 14 |
| Moodz | 13 |
| Static | 13 |
| TwoTone | 13 |

`source_material/` is declared immutable in ADR-002 and enforced by
`app/core/paths.assert_safe_write_target()`. This is the exact defect class the
rule exists to prevent, and it is listed as a `BLOCKER` in
`docs/quality/DEFECT_TAXONOMY.md`.

## How it was found

`python -m app.cli.main validate` re-hashes all 1331 imported files against
`source_material/manifests/source-migration.csv` on every run. It reported:

```
== imported source integrity ==
  1331 files re-hashed against the manifest
      CHANGED  source_material/imported_canon/approved_characters/ash/ash_01_neutral.png
      CHANGED  source_material/imported_canon/approved_characters/ash/ash_02_threeqtr.png
      ...
```

The gate worked. This is the one part of the story that went right: a machine
check that can only reject caught a violation that no human had noticed, before
it reached a commit.

Note that `git status` showed nothing — the imported binaries are git-ignored by
design, so version control could not have caught this. The manifest is the only
thing that could.

## Cause

A subagent, tasked with writing character identity packages, read the approved
character art and wrote back to those paths.

`assert_safe_write_target()` refuses writes into `source_material/` — but only
for code that calls it. Anything writing files directly — an editor, a
`PIL.Image.save()`, a coding agent using a file-write tool — never touches that
function and was never stopped by it.

**The guard was advisory, and advisory guards only bind the people who already
intended to comply.**

## Resolution

1. **Restored.** All 81 files re-copied from the read-only factory at
   `I:\MonkeyZoo Comic Strip\Fusion Squad\MonkeyZoo_Comic_Factory`. Before
   overwriting, each source file was itself hash-checked against the manifest,
   so a corrupted source could not have been propagated.

   ```
   restored 81 files from the read-only factory
   remaining mismatches: 0
   ```

2. **Factory verified untouched.** The external source of truth was
   fingerprinted before the very first migration and again after this incident:

   ```
   factory files=6997 fingerprint match=True
   ```

   Nothing outside this repository was ever at risk.

3. **Cause closed.** `scripts/migration/protect_source_material.py` now sets the
   OS read-only bit on every imported file:

   ```
   protected 1359 of 1359 imported files
   0 of 1359 imported files are writable
   ```

   Verified by attempting an append and confirming `PermissionError`.

## Why this matters beyond the incident

The whole premise of Banana Lab 2.0 is that the previous system could not tell
you which asset was authoritative. `source_material/` being provably unchanged
is what makes every provenance claim in this repository worth anything. Had the
mutation gone unnoticed, every downstream statement of the form "traceable to
approved source" would have been quietly false.

## Follow-up

| Action | Status |
|---|---|
| Restore the 81 files | Done |
| Verify the external factory | Done — fingerprint match |
| OS-level read-only protection | Done, verified |
| Run protection after every migration | Documented in the script and in `AGENTS.md` |
| Regression test for the protection | **Open** — a test asserting imported files are not writable |

## Note on the agent brief

The subagent brief said, verbatim: *"Do NOT modify anything under
`source_material/` or the `I:\MonkeyZoo...` source tree."* It did anyway.

That is the lesson worth keeping: **an instruction is not a control.** The rule
was stated, understood in principle, and violated in practice. What actually
prevented recurrence was a read-only bit and a hash check — neither of which
requires anyone to remember anything.
