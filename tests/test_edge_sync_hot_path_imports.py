from __future__ import annotations

import ast
from pathlib import Path

HOT_PATH_DIRS = (
    "algebra",
    "chat",
    "generate",
    "vault",
    "core/physics",
)

FORBIDDEN_IMPORTS = (
    "boto3",
    "botocore",
    "core.sync.object_store",
    "core.sync.s3_store",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in HOT_PATH_DIRS:
        base = root / rel
        if base.exists():
            files.extend(base.rglob("*.py"))
    return files


def _imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_hot_path_has_no_object_store_imports() -> None:
    offenders: list[str] = []
    root = _repo_root()
    for path in _python_files(root):
        imports = _imports_for(path)
        for forbidden in FORBIDDEN_IMPORTS:
            if forbidden in imports or any(name.startswith(forbidden + ".") for name in imports):
                offenders.append(f"{path.relative_to(root)} imports {forbidden}")

    assert offenders == []
