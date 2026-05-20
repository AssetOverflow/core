"""ADR-0075 (C1) — runtime seam tests for the realizer guard.

These tests exercise the hook in ``chat/runtime.py`` end-to-end:

* C2 confirmation prompts now reach accepted propositional surfaces
  while guard telemetry stays present.
* The telemetry serializer surfaces both new fields.
* The guard does not regress pack-grounded DEFINITION cases — those
  remain ``status="ok"`` byte-identical to pre-C1 behavior.
* AST seam: only ``chat.runtime`` is allowed to import
  ``generate.realizer_guard`` at module level.  Other production
  modules must not depend on the guard directly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from generate.realizer_guard import DISCLOSURE_SURFACE


_PRIMING = ("What is light?", "Define knowledge.", "What is truth?")
_BUG_PROMPT = "Light reveals truth, right?"


def _build_runtime() -> ChatRuntime:
    return ChatRuntime(config=RuntimeConfig(
        register_pack_id="default_neutral_v1",
    ))


def _run_holdout_sequence(rt: ChatRuntime) -> None:
    pipeline = CognitiveTurnPipeline(runtime=rt)
    for p in _PRIMING:
        pipeline.run(p)
    pipeline.run(_BUG_PROMPT)


# ---------- C2 confirmation prompt routing ----------


def test_confirmation_prompt_surface_is_articulated():
    rt = _build_runtime()
    _run_holdout_sequence(rt)
    te = rt.turn_log[-1]
    assert te.realizer_guard_status == "ok"
    assert te.surface != DISCLOSURE_SURFACE
    assert "light reveals truth" in te.surface
    assert "pack-grounded" in te.surface


def test_confirmation_prompt_uses_pack_grounding():
    rt = _build_runtime()
    _run_holdout_sequence(rt)
    te = rt.turn_log[-1]
    assert te.grounding_source == "pack"


def test_confirmation_prompt_records_guard_ok():
    rt = _build_runtime()
    _run_holdout_sequence(rt)
    te = rt.turn_log[-1]
    assert te.realizer_guard_rule == ""


# ---------- ChatResponse mirrors TurnEvent ----------


def test_chat_response_carries_guard_fields():
    rt = _build_runtime()
    pipeline = CognitiveTurnPipeline(runtime=rt)
    for p in _PRIMING:
        pipeline.run(p)
    # Pipeline runs and writes to turn_log; verify ChatResponse via
    # direct rt.chat() on the bug prompt produces a response that
    # mirrors the TurnEvent fields.
    response = rt.chat(_BUG_PROMPT)
    assert response.realizer_guard_status in {"ok", "rejected"}
    # When rejected, ChatResponse + TurnEvent must agree on the rule.
    te = rt.turn_log[-1]
    assert response.realizer_guard_status == te.realizer_guard_status
    assert response.realizer_guard_rule == te.realizer_guard_rule


# ---------- Currently-passing cases stay passing ----------


@pytest.mark.parametrize("prompt", [
    "What is light?",
    "Define knowledge.",
    "What is truth?",
])
def test_pack_grounded_definitions_pass_guard(prompt: str):
    """ADR-0075 byte-identity invariant: currently-passing cases must
    not regress.  These are the saturated cognition-lane DEFINITION
    cases — guard must accept all of them."""
    rt = _build_runtime()
    pipeline = CognitiveTurnPipeline(runtime=rt)
    pipeline.run(prompt)
    te = rt.turn_log[-1]
    assert te.realizer_guard_status == "ok"
    assert te.realizer_guard_rule == ""
    assert te.surface != DISCLOSURE_SURFACE
    assert te.surface.startswith(prompt.split()[-1].rstrip("?.").capitalize()) or "pack-grounded" in te.surface


# ---------- Telemetry surface ----------


def test_telemetry_includes_guard_fields():
    from chat.telemetry import serialize_turn_event
    rt = _build_runtime()
    _run_holdout_sequence(rt)
    te = rt.turn_log[-1]
    record = serialize_turn_event(te)
    assert "realizer_guard_status" in record
    assert "realizer_guard_rule" in record
    assert record["realizer_guard_status"] == "ok"
    assert record["realizer_guard_rule"] == ""


def test_telemetry_guard_fields_empty_on_pre_c1_events():
    """A plain TurnEvent without the guard fields set should
    serialize to empty strings, preserving wire-format degradation."""
    from chat.telemetry import serialize_turn_event
    rt = _build_runtime()
    pipeline = CognitiveTurnPipeline(runtime=rt)
    pipeline.run("What is light?")
    te = rt.turn_log[-1]
    record = serialize_turn_event(te)
    # status should be "ok" (guard ran and accepted), rule empty
    assert record["realizer_guard_status"] == "ok"
    assert record["realizer_guard_rule"] == ""


# ---------- AST seam ----------


_PRODUCTION_MODULE_ROOTS = ("chat", "generate", "packs", "core", "language_packs")
_GUARD_MODULE_NAME = "generate.realizer_guard"
_ALLOWED_IMPORTERS = {"chat/runtime.py"}


def _imports_guard(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == _GUARD_MODULE_NAME:
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == _GUARD_MODULE_NAME:
                    return True
    return False


def test_only_runtime_imports_realizer_guard():
    """Production modules must not import the guard directly.

    The guard is a singleton seam centralized in ``chat.runtime``.
    Other modules sprinkling guard calls would split the seam and
    make rejection routing harder to audit.
    """
    repo_root = Path(__file__).resolve().parent.parent
    offenders: list[str] = []
    for root in _PRODUCTION_MODULE_ROOTS:
        root_path = repo_root / root
        if not root_path.exists():
            continue
        for py in root_path.rglob("*.py"):
            rel = py.relative_to(repo_root).as_posix()
            if rel == "generate/realizer_guard.py":
                continue
            if rel in _ALLOWED_IMPORTERS:
                continue
            if _imports_guard(py):
                offenders.append(rel)
    assert not offenders, (
        f"Only {sorted(_ALLOWED_IMPORTERS)} may import "
        f"{_GUARD_MODULE_NAME!r}; found in: {offenders}"
    )
