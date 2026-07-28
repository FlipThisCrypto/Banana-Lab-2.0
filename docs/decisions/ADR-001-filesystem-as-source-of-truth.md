# ADR-001: The filesystem is the source of truth

**Status:** Accepted · **Date:** 2026-07-28

## Context

Banana Lab 1.0 kept production state in `.workflow-status.json`,
`.art-workspace/`, `.qa-workspace/` and similar hidden directories. For legacy
Issue 001 those records disagreed with each other and with the artwork: the
workflow file said `published`, the metadata said `draft_composite`, and four
different images existed for every panel ID.

State that lives beside the work can drift from the work.

## Decision

**The files on disk are the state.** There is no database and no status file
that a tool may write to advance the pipeline.

A stage is complete when the files that prove it exist and are non-empty
(`app/domain/pipeline.py`, `Stage.required_paths`). The CLI reads the filesystem
and reports. It cannot move work forward.

## Consequences

**Good**

- The project is legible without the tooling. Open the directory and you can see
  where it stands.
- State cannot silently disagree with the work, because state *is* the work.
- Delete `app/` and the project survives intact.
- Any tool — a script, an editor, a person — can participate.

**Costs**

- Completeness is checked structurally, not semantically. A stage with the right
  files present but poor content reads as complete. This is why human gates
  exist (ADR-005).
- Some checks are slower than a database lookup. Re-hashing 1331 imported files
  takes seconds, which is acceptable for a pre-commit check.

## Alternatives rejected

- **A status database.** Faster, and reintroduces exactly the drift that caused
  the problem.
- **Git as the state machine.** Branch and tag conventions are invisible to
  anyone who does not know them, and artwork is not tracked.
