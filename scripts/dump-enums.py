"""Dump ratified engine enum values for Workbench UI coverage tests.

Read-only helper: parses source with Python AST and writes JSON to stdout.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def enum_values(path: Path, class_name: str) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            values: list[str] = []
            for statement in node.body:
                if (
                    isinstance(statement, ast.Assign)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                ):
                    values.append(statement.value.value)
            return values
    raise SystemExit(f"enum class not found: {class_name}")


def literal_values(path: Path, name: str) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                continue
            value = node.value
            if (
                isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Name)
                and value.value.id == "Literal"
            ):
                items = value.slice.elts if isinstance(value.slice, ast.Tuple) else [value.slice]
                return [
                    item.value
                    for item in items
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                ]
    raise SystemExit(f"literal alias not found: {name}")


snapshot = {
    "EpistemicState": enum_values(ROOT / "core" / "epistemic_state.py", "EpistemicState"),
    "GroundingSource": literal_values(ROOT / "core" / "epistemic_state.py", "GroundingSource"),
    "NormativeClearance": enum_values(ROOT / "core" / "epistemic_state.py", "NormativeClearance"),
    "ReviewState": literal_values(ROOT / "teaching" / "proposals.py", "ReviewState"),
}

print(json.dumps(snapshot, indent=2, sort_keys=True))
