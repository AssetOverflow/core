"""Focused tests for the Stage 2 served ASK artifact adapter.

These tests intentionally avoid ``chat.runtime``. This slice is adapter-only:
it validates Q1-D question artifacts and returns a typed decision, but does not
wire runtime acquisition of ``ContemplationResult``.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from core.config import RuntimeConfig
from core.epistemic_disclosure import ServedAskDecision, evaluate_served_ask
from core.epistemic_disclosure.disposition import ServedDisposition, choose_served_disposition


class DummyTerminal:
    def __init__(self, value: str):
        self.value = value


class DummyContemplationResult:
    def __init__(
        self,
        terminal: str,
        *,
        question_path: str | None = None,
        proposal_path: str | None = None,
        family: str | None = None,
    ) -> None:
        self.terminal = DummyTerminal(terminal)
        self.question_path = question_path
        self.proposal_path = proposal_path
        self.family = family


def _write_artifact(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _valid_payload(text: str = "How many crates are left?") -> dict:
    return {
        "status": "question_only",
        "blocking_reason": "missing_total_count",
        "owner_organ": "r2_constraint",
        "question": {
            "text": text,
            "reason": "missing_total_count",
            "slot_name": "total_count",
            "expected_unit_or_type": "count_int",
            "binding_target": "collective_unit_total",
        },
        "answer_binding": None,
        "requires_review": True,
        "served": False,
    }


def _question_result(q_path: Path, p_path: Path | None = None) -> DummyContemplationResult:
    return DummyContemplationResult(
        "QUESTION_NEEDED",
        question_path=str(q_path),
        proposal_path=str(p_path) if p_path is not None else None,
    )


def test_ask_serving_disabled_preserves_existing_fallback_surface(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    _write_artifact(q_path, _valid_payload())

    decision = evaluate_served_ask(
        RuntimeConfig(ask_serving_enabled=False),
        _question_result(q_path),
        "fallback",
    )

    assert isinstance(decision, ServedAskDecision)
    assert decision.served is False
    assert decision.terminal == "QUESTION_NEEDED"
    assert decision.surface == "fallback"
    assert decision.disposition is ServedDisposition.REFUSE


def test_ask_serving_enabled_surfaces_question_needed_from_artifact(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    p_path = tmp_path / "proposals" / "p.json"
    _write_artifact(q_path, _valid_payload("How many crates are left?"))

    decision = evaluate_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        _question_result(q_path, p_path),
        "fallback",
    )

    assert decision.served is True
    assert decision.terminal == "QUESTION_NEEDED"
    assert decision.surface == "How many crates are left?"
    assert decision.disposition is ServedDisposition.ASK


def test_served_ask_uses_governance_disposition_bus(monkeypatch, tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    _write_artifact(q_path, _valid_payload())
    calls = []

    def traced_choose_served_disposition(*args, **kwargs):
        calls.append((args, kwargs))
        return choose_served_disposition(*args, **kwargs)

    monkeypatch.setattr(
        "core.epistemic_disclosure.ask_serving.choose_served_disposition",
        traced_choose_served_disposition,
    )

    decision = evaluate_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        _question_result(q_path),
        "fallback",
    )

    assert decision.served is True
    assert decision.disposition is ServedDisposition.ASK
    assert len(calls) == 1
    assert calls[0][1]["limitation"].resolution_action == "ask_question"


def test_question_path_must_not_equal_proposal_path(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "same.json"
    _write_artifact(q_path, _valid_payload())

    decision = evaluate_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        _question_result(q_path, q_path),
        "fallback",
    )

    assert decision.served is False
    assert decision.surface == "fallback"


def test_non_question_needed_terminal_preserves_proposal_signal(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    _write_artifact(q_path, _valid_payload())
    result = DummyContemplationResult(
        "PROPOSAL_EMITTED",
        question_path=str(q_path),
        proposal_path=str(tmp_path / "proposals" / "p.json"),
    )

    decision = evaluate_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        result,
        "fallback",
    )

    assert decision.served is False
    assert decision.terminal == "PROPOSAL_EMITTED"
    assert decision.surface == "fallback"
    assert decision.disposition is ServedDisposition.PROPOSE


def test_missing_or_unreadable_question_artifact_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "questions" / "missing.json"

    decision = evaluate_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        _question_result(missing),
        "fallback",
    )

    assert decision.served is False
    assert decision.surface == "fallback"


def test_malformed_question_artifact_fails_closed(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    q_path.parent.mkdir(parents=True, exist_ok=True)
    q_path.write_text("{bad json", encoding="utf-8")

    decision = evaluate_served_ask(
        RuntimeConfig(ask_serving_enabled=True),
        _question_result(q_path),
        "fallback",
    )

    assert decision.served is False
    assert decision.surface == "fallback"


def test_rejects_artifact_status_proposal_only(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    data = _valid_payload()
    data["status"] = "proposal_only"
    _write_artifact(q_path, data)

    decision = evaluate_served_ask(RuntimeConfig(ask_serving_enabled=True), _question_result(q_path), "fallback")

    assert decision.served is False
    assert decision.surface == "fallback"


def test_rejects_artifact_served_true(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    data = _valid_payload()
    data["served"] = True
    _write_artifact(q_path, data)

    decision = evaluate_served_ask(RuntimeConfig(ask_serving_enabled=True), _question_result(q_path), "fallback")

    assert decision.served is False


def test_rejects_artifact_requires_review_false(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    data = _valid_payload()
    data["requires_review"] = False
    _write_artifact(q_path, data)

    decision = evaluate_served_ask(RuntimeConfig(ask_serving_enabled=True), _question_result(q_path), "fallback")

    assert decision.served is False


def test_rejects_artifact_non_null_answer_binding(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    data = _valid_payload()
    data["answer_binding"] = {"slot": "total_count", "value": 12}
    _write_artifact(q_path, data)

    decision = evaluate_served_ask(RuntimeConfig(ask_serving_enabled=True), _question_result(q_path), "fallback")

    assert decision.served is False


def test_rejects_missing_or_blank_question_text(tmp_path: Path) -> None:
    for value in (None, ""):
        q_path = tmp_path / f"questions_{value!r}" / "q.json"
        data = _valid_payload()
        if value is None:
            del data["question"]["text"]
        else:
            data["question"]["text"] = "   "
        _write_artifact(q_path, data)

        decision = evaluate_served_ask(RuntimeConfig(ask_serving_enabled=True), _question_result(q_path), "fallback")

        assert decision.served is False
        assert decision.surface == "fallback"


def test_rejects_missing_or_blank_slot_name(tmp_path: Path) -> None:
    for value in (None, ""):
        q_path = tmp_path / f"questions_slot_{value!r}" / "q.json"
        data = _valid_payload()
        if value is None:
            del data["question"]["slot_name"]
        else:
            data["question"]["slot_name"] = "   "
        _write_artifact(q_path, data)

        decision = evaluate_served_ask(RuntimeConfig(ask_serving_enabled=True), _question_result(q_path), "fallback")

        assert decision.served is False
        assert decision.surface == "fallback"


def test_adapter_does_not_import_question_renderer_or_construct_prose() -> None:
    path = Path(__file__).resolve().parents[1] / "core" / "epistemic_disclosure" / "ask_serving.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module != "core.epistemic_questions.render"
            assert not node.module.startswith("core.epistemic_questions.render.")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "core.epistemic_questions.render"
                assert not alias.name.startswith("core.epistemic_questions.render.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "render_question"

    for forbidden_template in ("How many", "What ", "Which ", "Please provide"):
        assert forbidden_template not in source
