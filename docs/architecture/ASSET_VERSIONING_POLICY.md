# Asset Versioning Policy

## Git LFS is not enabled

### Decision

Binary assets are **not** tracked, by LFS or otherwise. Provenance is carried by
the migration manifest and by job manifests.

### Why

**The imported corpus is 1.66 GB across 1331 files.** Under LFS that is 1.66 GB
of LFS storage, paid for and pulled on clone, for content that is a script run
away from being rebuilt — with hash verification.

**It is imported, not authored.** `source_material/` is a read-only copy of the
MonkeyZoo Comic Factory. The original still exists and is untouched. Versioning
a copy of an immutable source adds no history that the source does not already
have.

**Generated candidates should not have history.** They are proposals. Most are
rejected. Versioning every rejected candidate makes the repository large in
proportion to how much was thrown away, which is exactly backwards.

**Approved assets change rarely, and by replacement.** The approval workflow
forbids overwriting an approved asset; a revision is a new versioned file. That
gives history through naming, without a binary diff engine.

### What replaces it

| Need | Mechanism |
|---|---|
| Know what an imported file was | `source_material/manifests/source-migration.csv` — original path, size, SHA-256, classification, authority |
| Detect an imported file changing | `python -m app.cli.main validate` re-hashes all 1331 |
| Rebuild the corpus | `python scripts/migration/import_source_material.py` |
| Know how a generated image was made | Job manifest — prompt, negative, seed, model, sampler, steps, cfg, dimensions, control images, output hash |
| Know why an asset was approved | `13_approved/approval-record.yaml` — actor, date, evidence hash |
| Know what was rejected | `rejected/` on disk with reason files |

### Repository impact

| Metric | With this policy | With LFS on everything |
|---|---|---|
| Clone size | Single-digit MB | ~1.7 GB plus generated output |
| Clone time | Seconds | Minutes |
| LFS storage cost | None | Grows with every candidate |
| Provenance | Manifest + hash | Manifest + hash + object store |
| Rebuild | One command | Not needed, but you carry the weight always |

### When to revisit

Enable LFS if **any** of these becomes true:

1. **Approved final artwork is authored here rather than imported.** Original
   work with no external source of truth deserves real version control.
2. **The approved libraries exceed ~500 MB** and are actively edited rather than
   replaced.
3. **The source project is retired**, making `source_material/` the only copy.
   At that point it stops being a cache and becomes an archive.
4. **Multiple people edit binary assets concurrently** and need locking.

If enabled, do it deliberately:

- Track only `characters/approved/**`, `locations/approved/**`,
  `props/approved/**` and `issues/*/13_approved/**`.
- **Never** track `generated_candidates/`, `workspace/` or `vault/`.
- Document the patterns, the storage estimate and the clone impact here before
  the first `git lfs track`.

## Asset naming and versioning

Approved assets are versioned by name, not by overwrite:

```
characters/approved/neonblue/poses/neonblue_determined_v1.png
characters/approved/neonblue/poses/neonblue_determined_v2.png
```

`v1` stays. Anything referencing `v1` keeps working, and the reason `v2` exists
is recorded in the approval record. A panel script pins the version it was
approved against.

## Sidecar metadata

Every approved asset carries a `.yaml` sidecar alongside it — source, method,
job manifest reference, reviewer, date, and what it supersedes. Sidecars are
tracked even when the image is not, so provenance survives a fresh clone.
