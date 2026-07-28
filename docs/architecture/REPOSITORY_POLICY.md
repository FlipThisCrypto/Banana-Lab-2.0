# Repository Policy

## What belongs in Git

Git tracks **decisions, specifications and provenance**. It does not track
**pixels**, with narrow exceptions.

| Tracked | Not tracked |
|---|---|
| Documentation, bibles, schemas, scripts, code, tests | Imported source binaries |
| Panel scripts, layout specs, issue bibles | Generated candidates |
| Migration manifests (path + SHA-256 for every imported file) | Model weights, checkpoints, LoRAs |
| Job manifests (prompt, seed, model, output hash) | Workspace and vault contents |
| Approval records, defect logs | Export PDFs and CBZ archives |
| Storyboard thumbnails and contact sheets | Large working files (PSD, KRA, TIFF) |

## Why the binaries stay out

The migration copied **1331 files, 1.66 GB**. Tracking that would make the
repository slow to clone for content that is fully recoverable:

```bash
python scripts/migration/import_source_material.py
```

The manifest records the original absolute path and SHA-256 of every file, so a
re-import is verifiable rather than hopeful. `python -m app.cli.main validate`
re-hashes every imported file against the manifest and reports drift.

**Provenance without payload.** The repository stays clonable; the assets stay
verifiable.

## Directory rules

| Directory | Rule |
|---|---|
| `source_material/` | **Immutable.** Written only by the migration script. `paths.assert_safe_write_target` refuses anything else. Binaries ignored; manifests tracked. |
| `canon/`, `characters/`, `locations/`, `props/` | YAML and Markdown tracked. `approved/` images tracked when small; `generated_candidates/` and `rejected/` ignored except sidecars. |
| `issues/` | All specification tracked. Rendered art ignored except storyboard thumbnails. |
| `app/`, `scripts/`, `tests/`, `config/` | Fully tracked. |
| `config/local/` | **Ignored.** Machine-specific paths and any credentials. |
| `workspace/` | **Ignored.** Disposable. |
| `vault/` | **Ignored.** Retained on disk, excluded from discovery and production. |

## Secrets

Never committed: `.env`, `*.key`, `*.pem`, `*.pfx`, `credentials.*`, `secrets.*`.

**Machine-specific absolute paths are treated as a hygiene failure** in runtime
config. `validate_hygiene()` scans `config/**/*.yaml` for drive-letter paths and
reports them. One deliberate exception: `config/defaults/import-plan.yaml`
legitimately points at the source machine, and is skipped by name.

## Large files

Anything over 25 MB outside `source_material/`, `workspace/` and `vault/` is
reported by the hygiene check. The threshold exists to catch accidents, not to
be silently raised.

## Git LFS — not enabled

Deliberately. Rationale, and the conditions that would change it, in
`ASSET_VERSIONING_POLICY.md`.

## Branch and commit

- Default branch `main`.
- Work on branches; `main` stays clean.
- Commit messages state what changed and why.
- **Never commit unreviewed generated artwork as approved.** Candidates are
  ignored by design; promoting one is a deliberate reviewed act.

## Before every commit

```bash
python -m app.cli.main validate
git status
```

Validation covers schemas, panel scripts, format standard, manifest integrity
and hygiene. It cannot approve anything — it can only stop a commit that should
not happen.
