# ADR-005: Human approval gates, and machines that can only reject

**Status:** Accepted · **Date:** 2026-07-28

## Context

The legacy Issue 001 QA report reads `VERDICT: PASS`, `Evidence blockers: None`.
Its entire per-panel check was, twenty-four times:

```
- MZ-2026-08-01_P01_PANEL01: present; PNG; 1280x960; no file error
```

It tested file existence, format and dimensions. A tiled wallpaper pattern
passes that test. So do five off-model pink figures. Both shipped, and the
workflow file recorded owner approvals at every stage.

The gate could not see a picture, and it was allowed to say yes.

## Decision

**A machine gate may only reject. It may never approve.**

Automated validation checks the mechanical subset: schemas, panel scripts,
format standard, manifest integrity, hygiene, layout geometry. Every one of them
can fail an issue. None of them can pass one.

Approval lives in `issues/<issue>/13_approved/approval-record.yaml`, written by
hand, referencing evidence and naming the person. Nothing in this repository
writes that file. `app/services/issue_status.py` reads it; the CLI reports it;
neither can create it.

Five stages require it: Issue Bible, Script, Layouts, Controlled generation
test, Final approval. The rest are gated on evidence existing.

## Consequences

**Good**

- An issue cannot be released because the files are the right size.
- Accountability is recorded — who approved what, when, against which hash.
- Approval can be withdrawn, and the pipeline immediately reflects it.
- Automated checks stay honest about their scope: they catch what they can
  measure and make no claim about the rest.

**Costs**

- The pipeline cannot run unattended to completion. This is the point.
- Approval is hand-edited YAML. The friction is deliberate.
- A determined person can write `approved: true` without looking. The record
  makes that a traceable act rather than an emergent property of the tooling.

## Alternatives rejected

- **Numeric quality scoring as an approval gate.** A score is a machine saying
  yes in a different font.
- **Automatic approval when all checks pass.** Exactly the failure being fixed.
- **Approval inside the workflow status file.** Puts the record under the
  control of the thing being approved.
