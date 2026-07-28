"""Schema loading and validation."""

from __future__ import annotations

import pytest
import yaml

from app.core.schema import Schema, SchemaRegistry
from app.services.validation import registry

SIMPLE = yaml.safe_load(
    """
schema_id: sample
version: 1.0.0
title: Sample
identity_field: sample_id
fields:
  sample_id:
    type: string
    required: true
    pattern: "^S-[0-9]{3}$"
    description: Identifier.
  count:
    type: integer
    required: true
    minimum: 1
    maximum: 10
    description: A number.
  mode:
    type: string
    required: false
    enum: [a, b]
    description: A choice.
  tags:
    type: list
    required: false
    item_type: string
    description: Tags.
  people:
    type: list
    required: false
    item_fields:
      name: {type: string, required: true, description: Name.}
      age: {type: integer, required: false, description: Age.}
    description: People.
  meta:
    type: map
    required: false
    fields:
      key: {type: string, required: true, description: Key.}
    description: Metadata.
"""
)


@pytest.fixture
def schema() -> Schema:
    return Schema(SIMPLE)


def test_valid_document_passes(schema):
    result = schema.validate({"sample_id": "S-001", "count": 5})
    assert result.ok
    assert not result.errors


def test_missing_required_field_is_an_error(schema):
    result = schema.validate({"count": 5})
    assert not result.ok
    assert any("required" in f.message for f in result.errors)


def test_empty_required_field_is_an_error(schema):
    result = schema.validate({"sample_id": "", "count": 5})
    assert not result.ok


def test_pattern_is_enforced(schema):
    result = schema.validate({"sample_id": "nope", "count": 5})
    assert not result.ok
    assert any("does not match" in f.message for f in result.errors)


def test_enum_is_exhaustive(schema):
    result = schema.validate({"sample_id": "S-001", "count": 5, "mode": "z"})
    assert not result.ok


def test_numeric_bounds(schema):
    assert not schema.validate({"sample_id": "S-001", "count": 0}).ok
    assert not schema.validate({"sample_id": "S-001", "count": 99}).ok


def test_boolean_does_not_satisfy_integer(schema):
    """bool subclasses int in Python; the schema must not accept True as a count."""
    result = schema.validate({"sample_id": "S-001", "count": True})
    assert not result.ok


def test_wrong_type_is_an_error(schema):
    result = schema.validate({"sample_id": "S-001", "count": "five"})
    assert not result.ok


def test_list_item_types_are_checked(schema):
    result = schema.validate({"sample_id": "S-001", "count": 1, "tags": ["ok", 3]})
    assert not result.ok


def test_nested_item_fields_are_checked(schema):
    result = schema.validate(
        {"sample_id": "S-001", "count": 1, "people": [{"age": 3}]}
    )
    assert not result.ok
    assert any("people[0].name" in f.path for f in result.errors)


def test_nested_map_fields_are_checked(schema):
    result = schema.validate({"sample_id": "S-001", "count": 1, "meta": {}})
    assert not result.ok


def test_unknown_field_warns_but_does_not_fail(schema):
    """Production notes accumulate faster than schemas; do not block on them."""
    result = schema.validate({"sample_id": "S-001", "count": 1, "note": "hello"})
    assert result.ok
    assert any(f.severity == "warning" for f in result.findings)


def test_non_mapping_document_is_an_error(schema):
    assert not schema.validate(["not", "a", "mapping"]).ok


def test_identity_uniqueness_is_detected():
    reg = SchemaRegistry.__new__(SchemaRegistry)
    reg._schemas = {"sample": Schema(SIMPLE)}
    findings = reg.check_identity_uniqueness(
        "sample",
        [("a.yaml", {"sample_id": "S-001"}), ("b.yaml", {"sample_id": "S-001"})],
    )
    assert findings
    assert "duplicate identity" in findings[0].message


# --- the project's real schemas ------------------------------------------

def test_all_project_schemas_load():
    reg = registry()
    assert reg.ids(), "no schemas found under config/schemas"
    for schema_id in reg.ids():
        schema = reg[schema_id]
        assert schema.version
        assert schema.fields, f"{schema_id} declares no fields"


def test_every_field_has_a_description():
    """A schema field without a description is a field nobody can fill in correctly."""
    reg = registry()
    missing: list[str] = []

    def walk(fields: dict, prefix: str, schema_id: str) -> None:
        for name, rule in fields.items():
            if not isinstance(rule, dict):
                continue
            if not rule.get("description"):
                missing.append(f"{schema_id}:{prefix}{name}")
            for key in ("fields", "item_fields"):
                if isinstance(rule.get(key), dict):
                    walk(rule[key], f"{prefix}{name}.", schema_id)

    for schema_id in reg.ids():
        walk(reg[schema_id].fields, "", schema_id)

    assert not missing, f"fields without a description: {missing}"


def test_every_schema_declares_an_identity_field():
    reg = registry()
    for schema_id in reg.ids():
        assert reg[schema_id].identity_field, f"{schema_id} has no identity_field"
