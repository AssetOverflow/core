"""
Dump workbench/schemas.py dataclass field shapes to a JSON snapshot.

Usage (from repo root):
    uv run python scripts/dump-api-schemas.py

Output: workbench-ui/api-schema-snapshot.json

The snapshot is used by workbench-ui/src/types/api.test.ts to detect
TypeScript ↔ Python schema drift.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCHEMAS_PATH = REPO_ROOT / "workbench" / "schemas.py"
SNAPSHOT_PATH = REPO_ROOT / "workbench-ui" / "api-schema-snapshot.json"


def annotation_to_str(node: ast.expr) -> str:
    """Convert an AST annotation node to a canonical string."""
    return ast.unparse(node)


def extract_dataclasses(source: str) -> dict[str, dict[str, str]]:
    """Parse source and extract fields from @dataclass-decorated classes."""
    tree = ast.parse(source)
    result: dict[str, dict[str, str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Check for @dataclass decorator (any form)
        is_dataclass = any(
            (isinstance(d, ast.Name) and d.id == "dataclass")
            or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
            or (
                isinstance(d, ast.Call)
                and (
                    (isinstance(d.func, ast.Name) and d.func.id == "dataclass")
                    or (isinstance(d.func, ast.Attribute) and d.func.attr == "dataclass")
                )
            )
            for d in node.decorator_list
        )
        if not is_dataclass:
            continue

        fields: dict[str, str] = {}
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id
                annotation = annotation_to_str(stmt.annotation)
                fields[field_name] = annotation
        result[node.name] = fields

    return result


def main() -> None:
    if not SCHEMAS_PATH.exists():
        print(f"ERROR: {SCHEMAS_PATH} not found", file=sys.stderr)
        sys.exit(1)

    source = SCHEMAS_PATH.read_text(encoding="utf-8")
    dataclasses = extract_dataclasses(source)

    snapshot = {"dataclasses": {name: {"fields": fields} for name, fields in dataclasses.items()}}

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"Snapshot written to {SNAPSHOT_PATH}")
    print(f"Dataclasses found: {', '.join(dataclasses.keys())}")


if __name__ == "__main__":
    main()
