# Local machine configuration

**Everything in this directory except this file and `.gitkeep` is git-ignored.**

Machine-specific paths, endpoints and any credentials live here. Nothing here is
committed, and nothing outside here may hard-code a drive-letter path — the
hygiene check in `python -m app.cli.main validate` scans `config/**/*.yaml` and
reports absolute paths as a failure.

## Expected files

### `comfyui.yaml`

```yaml
host: http://127.0.0.1:8188
input_directory:  I:\ai\nft\input
output_directory: I:\ai\nft\output
temp_directory:   I:\ai\cache\temp
```

Discover the running instance's actual values with:

```bash
python -m app.cli.main comfy
```

### `paths.yaml`

Only if this checkout needs source roots different from
`config/defaults/import-plan.yaml`.

```yaml
source_root:    "I:/MonkeyZoo Comic Strip/Fusion Squad/MonkeyZoo_Comic_Factory"
published_root: "I:/MonkeyZoo Comic Strip/Fusion Squad"
```

## The one exception

`config/defaults/import-plan.yaml` legitimately contains absolute source paths —
it is the record of where the material came from, and the migration script needs
it. It is skipped by name in the hygiene check. It is also the only file in
`config/defaults/` allowed to do this.
