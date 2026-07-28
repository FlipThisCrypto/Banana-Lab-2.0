# Approval Workflow

## The single rule

**Only a human can approve. Nothing else may write an approval record.**

Approval lives in one place per issue:

```
issues/<issue>/13_approved/approval-record.yaml
```

No script in this repository writes that file. `app/services/issue_status.py`
reads it. The CLI reports it. Neither can create it.

---

## Why the rule is written this way

The legacy Issue 001 workflow file records five approvals — canon review,
script, art production, QA and release — each with
`"actor": "project_owner"`, on artwork that was self-labelled
`DRAFT COMPOSITE` and included five images that were not comic panels.

Whether a human clicked something is now unknowable. What is knowable is that
the record could be written by the pipeline that produced the work, and that
the QA gate feeding it could not see a picture.

So: approval is a separate file, written by hand, referencing evidence.

---

## The record

```yaml
issue_id: issue-001
approvals:
  issue_bible:
    approved: true
    actor: <name>
    date: 2026-08-01
    evidence_hash: <sha256 of the approved artefact>
    note: Confirmed C-01 and C-02 resolutions.
  script:
    approved: false
    actor: ""
    date: ""
    note: Awaiting owner.
```

A stage is approved only when its key exists **and** `approved: true`. Absence
means not approved. There is no default-approve path.

---

## Gates requiring human approval

| Stage | What is being approved |
|---|---|
| Issue Bible | The story is right, and canon conflicts are resolved |
| Script | Every panel has a job, dialogue is final |
| Layouts | Page geometry and reading order. **No final art before this.** |
| Controlled generation test | The production method preserves identity and integrates scenes |
| Final approval | The issue is releasable |

Research, backgrounds, staging, rendering, compositing, lettering, effects and
QA are gated on **evidence**, not approval — their files must exist and be
non-empty. See `app/domain/pipeline.py`.

---

## The approval sequence

### 1. Automated validation must pass first

```bash
python -m app.cli.main validate
```

It cannot approve. It can only stop an approval that should not happen.

### 2. Human review against the standard

The reviewer works through `QUALITY_STANDARD.md` with the artwork in front of
them, at final print size. Every defect found is recorded in
`12_qa/defects.csv` with a code from `DEFECT_TAXONOMY.md`.

### 3. Defect resolution

Every BLOCKER, CRITICAL and MAJOR defect must be `fixed` or `accepted`.

**Accepting a defect is a human decision that must record a reason.** An
accepted MAJOR defect with the reason field empty is not accepted.

### 4. Sign-off

The reviewer writes the approval entry with their name, the date, and the hash
of what they approved. The hash matters: it makes "the file changed after
approval" detectable.

---

## Promotion into approved libraries

Generated output starts in `generated_candidates/`. It reaches `approved/` only
by review.

```
generated_candidates/  ->  [human review]  ->  approved/
                                   |
                                   +-------->  rejected/
```

Rules:

1. **Never overwrite an existing approved asset.** A revision is a new file with
   a new version, and the old one stays.
2. **Never write into `source_material/`.** It is immutable; `paths.py` refuses.
3. **Every promoted asset carries its provenance sidecar** — prompt, seed,
   model, workflow, source references, reviewer, date.
4. **Rejected candidates are kept**, with the reason. Knowing what was rejected
   and why is worth more than the disk space.

---

## What is never automatic

- Setting `approval_status: approved` on any document.
- Moving a file into an `approved/` directory.
- Marking a pipeline stage complete when its evidence is missing.
- Advancing past a human gate.
- Marking an issue production-ready.
- Deciding an issue is finished because the files exist.

---

## Reversal

Approval can be withdrawn. Set `approved: false`, add a `withdrawn` note and the
reason, and keep the history in the file. The pipeline immediately reports the
stage as awaiting approval again.

Approval is a statement about a specific artefact, not a permanent property of a
stage.
