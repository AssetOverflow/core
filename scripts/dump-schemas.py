"""Dump workbench API dataclass field names for UI schema-drift tests.

Read-only helper: parses workbench/schemas.py with Python AST and writes
JSON to stdout — {class_name: [own_field, ...]}. Inherited fields belong
to the parent class entry (the TS mirrors use `extends` the same way).
Same pattern as scripts/dump-enums.py (ADR-0162 enum coverage).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "workbench" / "schemas.py"


def is_dataclass_decorated(node: ast.ClassDef) -> bool:
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name) and target.id == "dataclass":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "dataclass":
            return True
    return False


def own_fields(node: ast.ClassDef) -> list[str]:
    fields: list[str] = []
    for statement in node.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            fields.append(statement.target.id)
    return fields


def main() -> None:
    module = ast.parse(SCHEMAS.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for node in module.body:
        if isinstance(node, ast.ClassDef) and is_dataclass_decorated(node):
            out[node.name] = own_fields(node)
    if not out:
        raise SystemExit("no dataclasses found in workbench/schemas.py")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
