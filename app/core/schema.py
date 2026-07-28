"""Schema loading and validation for Banana Lab 2.0 documents.

Implements the small readable schema dialect documented in
`config/schemas/_schema-format.md`. Deliberately dependency-light: PyYAML only.

Design note: unknown fields produce warnings rather than errors. Production
notes accumulate faster than schemas do, and refusing a document because
somebody wrote down something useful would train people to stop writing things
down. Missing required fields, wrong types and out-of-enum values are errors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

SCALARS = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


@dataclass
class Finding:
    """One validation result."""

    severity: str  # "error" | "warning"
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper():7s}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    document: str
    schema_id: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


class Schema:
    """A parsed schema document."""

    def __init__(self, data: dict, source: Path | None = None):
        self.data = data
        self.source = source
        self.schema_id: str = data["schema_id"]
        self.version: str = data.get("version", "0.0.0")
        self.title: str = data.get("title", self.schema_id)
        self.identity_field: str | None = data.get("identity_field")
        self.fields: dict = data.get("fields", {})

    @classmethod
    def load(cls, path: Path) -> Schema:
        return cls(yaml.safe_load(path.read_text(encoding="utf-8")), path)

    # -- validation ---------------------------------------------------------
    def validate(self, doc: dict, document_name: str = "<doc>") -> ValidationResult:
        result = ValidationResult(document=document_name, schema_id=self.schema_id)
        if not isinstance(doc, dict):
            result.findings.append(Finding("error", "<root>", "document is not a mapping"))
            return result
        self._check_fields(doc, self.fields, "", result)
        return result

    def _check_fields(self, doc: dict, spec: dict, prefix: str, result: ValidationResult) -> None:
        for name, rule in spec.items():
            path = f"{prefix}{name}"
            present = name in doc and doc[name] is not None
            empty = present and doc[name] == "" or (present and doc[name] == [])

            if rule.get("required") and (not present or empty):
                result.findings.append(Finding("error", path, "required field is missing or empty"))
                continue
            if not present:
                continue
            self._check_value(doc[name], rule, path, result)

        for name in doc:
            if name not in spec:
                result.findings.append(
                    Finding("warning", f"{prefix}{name}", "field is not declared in the schema")
                )

    def _check_value(self, value: Any, rule: dict, path: str, result: ValidationResult) -> None:
        declared = rule.get("type", "string")

        if declared in SCALARS:
            expected = SCALARS[declared]
            # bool is a subclass of int; do not let True satisfy `integer`.
            if declared in ("integer", "number") and isinstance(value, bool):
                result.findings.append(Finding("error", path, f"expected {declared}, got boolean"))
                return
            if not isinstance(value, expected):
                result.findings.append(
                    Finding("error", path, f"expected {declared}, got {type(value).__name__}")
                )
                return
            self._check_constraints(value, rule, path, result)
            return

        if declared == "date":
            if isinstance(value, (date, datetime)):
                return
            try:
                datetime.fromisoformat(str(value))
            except ValueError:
                result.findings.append(Finding("error", path, f"not an ISO date: {value!r}"))
            return

        if declared == "list":
            if not isinstance(value, list):
                result.findings.append(Finding("error", path, f"expected list, got {type(value).__name__}"))
                return
            item_type = rule.get("item_type")
            item_fields = rule.get("item_fields")
            allowed = rule.get("enum_items")
            for index, item in enumerate(value):
                item_path = f"{path}[{index}]"
                if item_fields:
                    if not isinstance(item, dict):
                        result.findings.append(Finding("error", item_path, "expected a mapping"))
                        continue
                    self._check_fields(item, item_fields, f"{item_path}.", result)
                elif item_type:
                    self._check_value(item, {"type": item_type}, item_path, result)
                if allowed and item not in allowed:
                    result.findings.append(
                        Finding("error", item_path, f"{item!r} not in {allowed}")
                    )
            return

        if declared == "map":
            if not isinstance(value, dict):
                result.findings.append(Finding("error", path, f"expected mapping, got {type(value).__name__}"))
                return
            if rule.get("fields"):
                self._check_fields(value, rule["fields"], f"{path}.", result)
            return

        result.findings.append(Finding("warning", path, f"unknown declared type {declared!r}"))

    @staticmethod
    def _check_constraints(value: Any, rule: dict, path: str, result: ValidationResult) -> None:
        if "enum" in rule and value not in rule["enum"]:
            result.findings.append(Finding("error", path, f"{value!r} not in {rule['enum']}"))
        if "pattern" in rule and isinstance(value, str):
            if not re.fullmatch(rule["pattern"], value):
                result.findings.append(
                    Finding("error", path, f"{value!r} does not match {rule['pattern']}")
                )
        if "minimum" in rule and isinstance(value, (int, float)) and value < rule["minimum"]:
            result.findings.append(Finding("error", path, f"{value} < minimum {rule['minimum']}"))
        if "maximum" in rule and isinstance(value, (int, float)) and value > rule["maximum"]:
            result.findings.append(Finding("error", path, f"{value} > maximum {rule['maximum']}"))


class SchemaRegistry:
    """All schemas under config/schemas."""

    def __init__(self, schema_dir: Path):
        self.schema_dir = schema_dir
        self._schemas: dict[str, Schema] = {}
        for path in sorted(schema_dir.glob("*.schema.yaml")):
            schema = Schema.load(path)
            self._schemas[schema.schema_id] = schema

    def __contains__(self, schema_id: str) -> bool:
        return schema_id in self._schemas

    def __getitem__(self, schema_id: str) -> Schema:
        return self._schemas[schema_id]

    def ids(self) -> list[str]:
        return sorted(self._schemas)

    def check_identity_uniqueness(
        self, schema_id: str, documents: list[tuple[str, dict]]
    ) -> list[Finding]:
        """Report duplicate identity values across a set of documents."""
        schema = self._schemas[schema_id]
        if not schema.identity_field:
            return []
        seen: dict[Any, str] = {}
        findings: list[Finding] = []
        for name, doc in documents:
            if not isinstance(doc, dict):
                continue
            value = doc.get(schema.identity_field)
            if value is None:
                continue
            if value in seen:
                findings.append(
                    Finding(
                        "error",
                        f"{name}:{schema.identity_field}",
                        f"duplicate identity {value!r}, already used by {seen[value]}",
                    )
                )
            else:
                seen[value] = name
        return findings
