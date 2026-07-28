# ADR-002: Authoritative and generated assets are strictly separated

**Status:** Accepted · **Date:** 2026-07-28

## Context

In the legacy Issue 001, one panel ID resolved to four different images across
`selected_panels/`, `draft_composites/`, `.art-workspace/attempts/` and the
assembled page. None matched by hash. A directory named `selected_panels`
contained a character model sheet, a blurred blob and two tiled wallpaper
patterns. One of them — five off-model pink figures — reached the published
page.

There was no way to answer "which image is this panel?"

## Decision

Every asset has exactly one **authority level**, and the directory it lives in
declares it.

| Level | Location | Meaning |
|---|---|---|
| `authoritative` | `source_material/imported_canon/` | Owner-approved canon. Immutable. |
| `approved-reference` | `source_material/` | Human-reviewed derivative, usable as reference |
| `approved` | `*/approved/` | Human-approved production asset |
| `candidate` | `*/generated_candidates/` | Unapproved output. Never used in a composite. |
| `rejected` | `*/rejected/` | Reviewed and rejected. Retained with a reason. |
| `historical-reference` | `source_material/historical_issues/` | Informative, not authoritative |
| `superseded` | `source_material/legacy_reference/` | Evidence only. Never reused. |

Rules:

1. **One approved asset per slot.** If two exist, that is an
   `ASSET-AMBIGUOUS-SOURCE` BLOCKER.
2. **Promotion is a human act.** Nothing automated moves a file into
   `approved/`.
3. **Approved assets are never overwritten.** Revisions are new versioned files.
4. **`source_material/` is immutable.** `paths.assert_safe_write_target`
   refuses.
5. **Every asset is traceable** to an approved source through the migration
   manifest or a job manifest.

## Consequences

**Good**

- "Which image is this panel?" always has one answer.
- Candidates cannot leak into finished work by being in the wrong folder.
- The legacy failure mode is structurally impossible.

**Costs**

- More directories, and a promotion step that cannot be skipped.
- Reviewers must actually review, rather than letting a pipeline decide.
