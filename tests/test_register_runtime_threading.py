"""Runtime-threading lint test (ADR-0069 amendment).

The ADR-0069 amendment relaxed the original "required keyword-only
register parameter" rule to "default = unregistered sentinel," because
the original rule landed on 167 call sites across 15 test files.

The relaxation introduces a seam risk: an R3 site could call
``teaching_grounded_surface(lemma, intent)`` without ``register=``, and
the call would silently fall through to ``UNREGISTERED`` even though
the runtime has a non-neutral register loaded.

This lint test AST-parses ``chat/runtime.py`` and asserts that every
call to a register-aware composer passes ``register=`` explicitly. The
seam guarantee originally provided by a required parameter now lives
here.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = REPO_ROOT / "chat" / "runtime.py"

#: Composer functions that accept ``register=`` at R2.  Every call to
#: any of these from ``chat/runtime.py`` must pass ``register=``
#: explicitly.  When R3 widens composer logic, add new entries here.
REGISTER_AWARE_COMPOSERS: frozenset[str] = frozenset(
    {
        "pack_grounded_surface",
        "pack_grounded_correction_surface",
        "pack_grounded_procedure_surface",
        "pack_grounded_comparison_surface",
        "teaching_grounded_surface",
        "teaching_grounded_surface_composed",
        "cross_pack_grounded_surface",
        "narrative_grounded_surface",
        "example_grounded_surface",
        # ADR-0070 (R3) — internal selector-ready builder that
        # pack_grounded_surface delegates to.  Carries register= so
        # the disclosure_domain_count override threads through. Not
        # called from chat/runtime.py directly, so the
        # runtime-threading lint passes trivially.
        "build_pack_surface_candidate",
        "gloss_aware_cause_surface",
        "pack_grounded_unknown_surface",
        "teaching_grounded_surface_transitive",
    }
)


def _called_function_name(call: ast.Call) -> str | None:
    """Return the bare name of a Call's target, or ``None`` if not a name."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _has_register_kwarg(call: ast.Call) -> bool:
    return any(kw.arg == "register" for kw in call.keywords)


def _find_unthreaded_calls(text: str) -> list[tuple[str, int]]:
    """Return ``[(function_name, line_number), ...]`` for any call to a
    register-aware composer that does not pass ``register=``.
    """
    tree = ast.parse(text)
    bad: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _called_function_name(node)
        if name is None or name not in REGISTER_AWARE_COMPOSERS:
            continue
        if not _has_register_kwarg(node):
            bad.append((name, node.lineno))
    return bad


def test_runtime_threads_register_to_every_composer_call():
    if not RUNTIME_PATH.is_file():
        pytest.skip("chat/runtime.py missing — environment issue")
    text = RUNTIME_PATH.read_text(encoding="utf-8")
    unthreaded = _find_unthreaded_calls(text)
    assert not unthreaded, (
        "ADR-0069 amendment violation: chat/runtime.py calls "
        "register-aware composer(s) without passing register= "
        "explicitly. Every site below must thread "
        "register=self.register_pack. R3 cannot silently fall through "
        "to UNREGISTERED.\n\n"
        + "\n".join(
            f"  - {name} at chat/runtime.py:{lineno}"
            for name, lineno in unthreaded
        )
    )


def test_register_aware_composer_set_is_synced():
    """Guard: every composer with a ``register=`` parameter in chat/*
    must appear in REGISTER_AWARE_COMPOSERS.  If a new composer is
    added and forgotten here, this test fails so the lint stays
    complete.
    """
    composer_files = (
        REPO_ROOT / "chat" / "pack_grounding.py",
        REPO_ROOT / "chat" / "teaching_grounding.py",
        REPO_ROOT / "chat" / "cross_pack_grounding.py",
        REPO_ROOT / "chat" / "narrative_surface.py",
        REPO_ROOT / "chat" / "example_surface.py",
    )
    discovered: set[str] = set()
    for path in composer_files:
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith("_"):
                continue
            param_names = [a.arg for a in node.args.kwonlyargs] + [
                a.arg for a in node.args.args
            ]
            if "register" in param_names:
                discovered.add(node.name)
    missing = discovered - REGISTER_AWARE_COMPOSERS
    extra = REGISTER_AWARE_COMPOSERS - discovered
    assert not missing, (
        "Register-aware composer not in REGISTER_AWARE_COMPOSERS — add "
        f"these names to the set in this test file: {sorted(missing)}"
    )
    assert not extra, (
        "REGISTER_AWARE_COMPOSERS lists composers that no longer accept "
        f"register= — remove them: {sorted(extra)}"
    )
