"""Partition test — consumption registries are math-domain only.

ADR-0167 partition: cognition ``TeachingChainProposal`` flow must not
see math composition/frame artifacts and vice versa.

The consumption registries (FrameRegistry, CompositionRegistry) read
exclusively from the en_core_math_v1 pack. They do not import from
cognition modules and cannot be reached via cognition code paths.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return out


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    while here.parent != here and not (here / "pyproject.toml").exists():
        here = here.parent
    return here


def test_frame_registry_imports_no_cognition_modules():
    repo = _repo_root()
    imports = _module_imports(
        repo / "generate" / "comprehension" / "frame_registry.py"
    )
    cognition_taints = {
        i for i in imports if i.startswith("cognition.") or i.startswith("teaching.cognition")
    }
    assert cognition_taints == set(), (
        f"frame_registry imports cognition modules: {cognition_taints}"
    )


def test_composition_registry_imports_no_cognition_modules():
    repo = _repo_root()
    imports = _module_imports(
        repo / "generate" / "comprehension" / "composition_registry.py"
    )
    cognition_taints = {
        i for i in imports if i.startswith("cognition.") or i.startswith("teaching.cognition")
    }
    # Math-side teaching imports are fine (math_composition_ratification);
    # cognition-side teaching imports are not.
    assert cognition_taints == set(), (
        f"composition_registry imports cognition modules: {cognition_taints}"
    )


def test_compile_modules_import_no_cognition():
    repo = _repo_root()
    for mod in ("compile_frames.py", "compile_compositions.py"):
        imports = _module_imports(repo / "language_packs" / mod)
        cognition_taints = {
            i for i in imports
            if i.startswith("cognition.") or i.startswith("teaching.cognition")
        }
        assert cognition_taints == set(), (
            f"{mod} imports cognition modules: {cognition_taints}"
        )
