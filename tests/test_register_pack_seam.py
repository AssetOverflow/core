"""Architectural seam test (ADR-0068 → ADR-0069 narrowed).

Pins the load-bearing commitment of ADR-0068:

    Register is a property of the realizer, not the proposition graph.

At R2 the realizer-side modules (chat/runtime.py, composers in chat/*)
legitimately import ``packs.register``. The truth-path modules
(cognition / trace / pipeline / intent classification / propagation /
vault / algebra) must NOT.

This test fails the moment register leaks into the truth path.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Modules that must remain register-free.  These compute the
#: proposition graph, intent classification, grounding source, trace
#: hash, propagation, vault recall, and algebra.  None of them should
#: ever read or branch on register.
TRUTH_PATH_FILES: tuple[Path, ...] = (
    REPO_ROOT / "core" / "cognition" / "trace.py",
    REPO_ROOT / "core" / "cognition" / "pipeline.py",
    REPO_ROOT / "core" / "cognition" / "result.py",
    REPO_ROOT / "generate" / "graph_planner.py",
    REPO_ROOT / "generate" / "intent.py",
    REPO_ROOT / "field" / "propagate.py",
    REPO_ROOT / "vault" / "store.py",
    REPO_ROOT / "algebra" / "versor.py",
)


def _imports_register_pack(path: Path) -> list[str]:
    """Return import strings in ``path`` that reference ``packs.register``."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("packs.register"):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("packs.register"):
                found.append(f"from {node.module} import ...")
    return found


@pytest.mark.parametrize(
    "upstream",
    [
        pytest.param(p, id=str(p.relative_to(REPO_ROOT)))
        for p in TRUTH_PATH_FILES
    ],
)
def test_truth_path_does_not_import_register_pack(upstream: Path):
    leaks = _imports_register_pack(upstream)
    assert not leaks, (
        f"Seam violation: {upstream.relative_to(REPO_ROOT)} imports "
        f"packs.register ({leaks}). Register is a realizer-side concept "
        "(ADR-0068 / ADR-0069). It must not leak into intent "
        "classification, propagation, trace hashing, or any module that "
        "decides what is true."
    )


def test_register_loader_imports_only_safe_modules():
    """The loader itself must not pull in truth-path dependencies."""
    loader = REPO_ROOT / "packs" / "register" / "loader.py"
    text = loader.read_text(encoding="utf-8")
    forbidden_imports = (
        "from generate.",
        "from chat.",
        "from field.",
        "from algebra.",
        "from vault.",
        "from core.cognition.",
        "import generate",
        "import chat",
        "import field",
        "import algebra",
        "import vault",
    )
    for needle in forbidden_imports:
        assert needle not in text, (
            f"Seam violation: packs/register/loader.py imports {needle!r}. "
            "The presentation axis must not depend on the truth path."
        )
