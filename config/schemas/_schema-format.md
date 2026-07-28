# Banana Lab 2.0 schema format

Schemas live in `config/schemas/*.schema.yaml`. They are deliberately a small,
readable dialect rather than full JSON Schema, so that a comic owner can read and
edit them without learning a spec, and so the toolchain needs no extra
dependency beyond PyYAML.

`app/core/schema.py` interprets them. `python -m app.cli.main validate` runs them.

## File shape

```yaml
schema_id: character          # unique id
version: 1.0.0                # bump on any breaking field change
title: Character Bible
description: >-
  What this document is for.
identity_field: character_id  # the field that must be unique across the library
fields:
  <field_name>:
    type: string | integer | number | boolean | list | map | date
    required: true | false    # default false
    description: ...          # always required in practice; explains intent
    enum: [a, b, c]           # allowed values
    pattern: "^regex$"        # for type: string
    minimum: 0                # for numbers
    maximum: 100
    item_type: string         # for type: list of scalars
    item_fields:              # for type: list of objects — recursive `fields`
      <field_name>: {...}
    fields:                   # for type: map — recursive
      <field_name>: {...}
```

## Rules the validator enforces

1. Every `required: true` field must be present and non-empty.
2. Declared types must match.
3. `enum` values are exhaustive — anything else fails.
4. `pattern` must match in full.
5. Unknown fields are reported as warnings, never silently dropped. A schema
   change is a deliberate act; a typo is not.
6. `identity_field` values must be unique across every document validated
   against the same schema.

## Why warnings and not failures for unknown fields

Production notes accumulate faster than schemas. Blocking on an unrecognised key
would push people to stop writing notes. Surfacing it keeps the schema honest
without making the schema an obstacle to the work it exists to serve.

## Approval fields

Every schema carries `canon_status`, `approval` and `last_reviewed`. These are
never set by a generation step. Only a human review action may move a document
to `approved`. See `docs/quality/APPROVAL_WORKFLOW.md`.
