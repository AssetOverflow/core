"""Architectural seam test (ADR-0073b).

Pins the load-bearing commitment of ADR-0073 / ADR-0073b:

    Anchor lens is a composer-side concept, not a property of the
    proposition graph or trace hash function.

At L1.3 the lens is loaded by ``chat/runtime.py`` and consumed by
``chat/pack_grounding.py`` (the composer-side allowlist).  The
truth-path modules (cognition / trace / pipeline / intent
classification / propagation / vault / algebra) must NOT import
``packs.anchor_lens``.

This test fails the moment anchor lens leaks into the truth path.

Mirror of ``tests/test_register_pack_seam.py`` for the substantive-axis
sibling.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Modules that must remain anchor-lens-free.  These compute the
#: proposition graph, intent classification, grounding source, trace
#: hash, propagation, vault recall, and algebra.  None of them should
#: ever read or branch on the lens.
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


def _imports_anchor_lens(path: Path) -> list[str]:
    """Return import strings in ``path`` that reference ``packs.anchor_lens``."""
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
                if alias.name.startswith("packs.anchor_lens"):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("packs.anchor_lens"):
                found.append(f"from {node.module} import ...")
    return found


@pytest.mark.parametrize(
    "upstream",
    [
        pytest.param(p, id=str(p.relative_to(REPO_ROOT)))
        for p in TRUTH_PATH_FILES
    ],
)
def test_truth_path_does_not_import_anchor_lens(upstream: Path):
    leaks = _imports_anchor_lens(upstream)
    assert not leaks, (
        f"Seam violation: {upstream.relative_to(REPO_ROOT)} imports "
        f"packs.anchor_lens ({leaks}). Anchor lens is a composer-side "
        "concept (ADR-0073 / ADR-0073b). It must not leak into intent "
        "classification, propagation, trace hashing, or any module "
        "that decides what is true."
    )


def test_anchor_lens_loader_imports_only_safe_modules():
    """The loader itself must not pull in truth-path dependencies."""
    loader = REPO_ROOT / "packs" / "anchor_lens" / "loader.py"
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
            f"Seam violation: packs/anchor_lens/loader.py imports {needle!r}. "
            "The substantive axis must not depend on the truth path."
        )
