"""Tests for the runtime-facing ASK helper module."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import Mock

from chat.ask_runtime import maybe_apply_served_ask
from core.config import RuntimeConfig


class DummyTerminal:
    def __init__(self, value: str) -> None:
        self.value = value


class DummyResult:
    def __init__(
        self,
        terminal: str,
        *,
        question_path: str | None = None,
        proposal_path: str | None = None,
    ) -> None:
        self.terminal = DummyTerminal(terminal)
        self.question_path = question_path
        self.proposal_path = proposal_path


def _write_question(path: Path, text: str = "How many crates are left?") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "question_only",
                "requires_review": True,
                "served": False,
                "answer_binding": None,
                "question": {"text": text, "slot_name": "total_count"},
            }
        ),
        encoding="utf-8",
    )


def test_gate_disabled_returns_fallback_and_does_not_call_provider() -> None:
    provider = Mock()
    result = maybe_apply_served_ask(
        RuntimeConfig(ask_serving_enabled=False),
        "fallback",
        provider=provider,
    )

    assert result == "fallback"
    provider.assert_not_called()


def test_valid_question_candidate_returns_artifact_surface(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    _write_question(q_path, "How many crates are left?")

    result = maybe_apply_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        "fallback",
        contemplation_result=DummyResult("QUESTION_NEEDED", question_path=str(q_path)),
    )

    assert result == "How many crates are left?"


def test_proposal_only_candidate_returns_fallback(tmp_path: Path) -> None:
    p_path = tmp_path / "proposals" / "p.json"

    result = maybe_apply_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        "fallback",
        contemplation_result=DummyResult("PROPOSAL_EMITTED", proposal_path=str(p_path)),
    )

    assert result == "fallback"


def test_missing_question_artifact_returns_fallback(tmp_path: Path) -> None:
    missing = tmp_path / "questions" / "missing.json"

    result = maybe_apply_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        "fallback",
        contemplation_result=DummyResult("QUESTION_NEEDED", question_path=str(missing)),
    )

    assert result == "fallback"


def test_provider_path_uses_honest_contemplation_result_keyword(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    _write_question(q_path)

    result = maybe_apply_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        "fallback",
        provider=lambda: DummyResult("QUESTION_NEEDED", question_path=str(q_path)),
    )

    assert result == "How many crates are left?"


def test_helper_does_not_import_renderer_or_pass_manager() -> None:
    path = Path(__file__).resolve().parents[1] / "chat" / "ask_runtime.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = (
        "core.epistemic_questions.render",
        "generate.contemplation.pass_manager",
        "chat.runtime",
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for name in forbidden:
                assert node.module != name
                assert not node.module.startswith(name + ".")
        if isinstance(node, ast.Import):
            for alias in node.names:
                for name in forbidden:
                    assert alias.name != name
                    assert not alias.name.startswith(name + ".")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "render_question"


def test_public_runtime_schema_stays_unchanged() -> None:
    runtime_path = Path(__file__).resolve().parents[1] / "chat" / "runtime.py"
    tree = ast.parse(runtime_path.read_text(encoding="utf-8"), filename=str(runtime_path))

    saw_chat = False
    saw_response = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "chat":
            saw_chat = True
            args = [arg.arg for arg in node.args.args + node.args.kwonlyargs]
            assert "contemplation_result" not in args
        if isinstance(node, ast.ClassDef) and node.name == "ChatResponse":
            saw_response = True
            fields = [
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            ]
            assert "disposition" not in fields

    assert saw_chat
    assert saw_response
