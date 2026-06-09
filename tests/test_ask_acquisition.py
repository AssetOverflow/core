"""Tests for the Stage 2 served ASK acquisition seam.

The seam is provider-gated and delegates artifact validation to
``evaluate_served_ask``. It intentionally avoids ``chat.runtime`` and does not
call ``generate.contemplation.pass_manager`` directly.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from core.config import RuntimeConfig
from core.epistemic_disclosure.ask_acquisition import acquire_served_ask_candidate
from core.epistemic_disclosure.disposition import ServedDisposition


class DummyTerminal:
    def __init__(self, value: str) -> None:
        self.value = value


class DummyContemplationResult:
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


def _write_valid_question(path: Path, text: str = "How many crates are left?") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
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
    path.write_text(json.dumps(payload), encoding="utf-8")


def _question_result(q_path: Path, p_path: Path | None = None) -> DummyContemplationResult:
    return DummyContemplationResult(
        "QUESTION_NEEDED",
        question_path=str(q_path),
        proposal_path=str(p_path) if p_path is not None else None,
    )


def test_gate_disabled_does_not_call_provider() -> None:
    calls = []

    def provider():
        calls.append("called")
        raise AssertionError("provider must not run while ASK serving gate is disabled")

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=False),
        fallback_surface="fallback",
        provider=provider,
    )

    assert calls == []
    assert acquired.provider_called is False
    assert acquired.acquired is False
    assert acquired.decision.served is False
    assert acquired.decision.surface == "fallback"
    assert acquired.decision.disposition is ServedDisposition.REFUSE


def test_gate_disabled_with_existing_result_fails_closed_without_provider(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    _write_valid_question(q_path)

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=False),
        fallback_surface="fallback",
        contemplation_result=_question_result(q_path),
        provider=lambda: (_ for _ in ()).throw(AssertionError("provider must not run")),
    )

    assert acquired.provider_called is False
    assert acquired.acquired is True
    assert acquired.decision.served is False
    assert acquired.decision.terminal == "QUESTION_NEEDED"
    assert acquired.decision.surface == "fallback"


def test_gate_enabled_provider_valid_question_serves_via_adapter(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    p_path = tmp_path / "proposals" / "p.json"
    _write_valid_question(q_path, "How many crates are left?")
    calls = []

    def provider():
        calls.append("called")
        return _question_result(q_path, p_path)

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        provider=provider,
    )

    assert calls == ["called"]
    assert acquired.provider_called is True
    assert acquired.acquired is True
    assert acquired.decision.served is True
    assert acquired.decision.terminal == "QUESTION_NEEDED"
    assert acquired.decision.surface == "How many crates are left?"
    assert acquired.decision.disposition is ServedDisposition.ASK


def test_gate_enabled_existing_result_skips_provider_and_serves(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "q.json"
    _write_valid_question(q_path)

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        contemplation_result=_question_result(q_path),
        provider=lambda: (_ for _ in ()).throw(AssertionError("provider should not run")),
    )

    assert acquired.provider_called is False
    assert acquired.acquired is True
    assert acquired.decision.served is True


def test_provider_none_fails_closed() -> None:
    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        provider=lambda: None,
    )

    assert acquired.provider_called is True
    assert acquired.acquired is False
    assert acquired.decision.served is False
    assert acquired.decision.surface == "fallback"


def test_provider_exception_fails_closed() -> None:
    def provider():
        raise RuntimeError("candidate unavailable")

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        provider=provider,
    )

    assert acquired.provider_called is True
    assert acquired.acquired is False
    assert acquired.decision.served is False
    assert acquired.decision.surface == "fallback"


def test_proposal_only_without_question_path_does_not_serve(tmp_path: Path) -> None:
    result = DummyContemplationResult(
        "PROPOSAL_EMITTED",
        question_path=None,
        proposal_path=str(tmp_path / "proposals" / "p.json"),
    )

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        contemplation_result=result,
    )

    assert acquired.acquired is True
    assert acquired.decision.served is False
    assert acquired.decision.terminal == "PROPOSAL_EMITTED"
    assert acquired.decision.disposition is ServedDisposition.PROPOSE
    assert acquired.decision.surface == "fallback"


def test_question_path_equal_to_proposal_path_fails_closed(tmp_path: Path) -> None:
    q_path = tmp_path / "shared" / "artifact.json"
    _write_valid_question(q_path)

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        contemplation_result=_question_result(q_path, q_path),
    )

    assert acquired.decision.served is False
    assert acquired.decision.surface == "fallback"


def test_malformed_artifact_fails_closed(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "bad.json"
    q_path.parent.mkdir(parents=True, exist_ok=True)
    q_path.write_text("{bad json", encoding="utf-8")

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        contemplation_result=_question_result(q_path),
    )

    assert acquired.decision.served is False
    assert acquired.decision.surface == "fallback"


def test_invalid_question_artifact_fails_closed(tmp_path: Path) -> None:
    q_path = tmp_path / "questions" / "invalid.json"
    q_path.parent.mkdir(parents=True, exist_ok=True)
    q_path.write_text(
        json.dumps(
            {
                "status": "proposal_only",
                "question": {"text": "How many crates are left?", "slot_name": "total_count"},
                "requires_review": True,
                "served": False,
            }
        ),
        encoding="utf-8",
    )

    acquired = acquire_served_ask_candidate(
        RuntimeConfig(ask_serving_enabled=True),
        fallback_surface="fallback",
        contemplation_result=_question_result(q_path),
    )

    assert acquired.decision.served is False
    assert acquired.decision.surface == "fallback"


def test_acquisition_module_does_not_import_renderer_or_pass_manager() -> None:
    path = Path(__file__).resolve().parents[1] / "core" / "epistemic_disclosure" / "ask_acquisition.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    forbidden_modules = (
        "core.epistemic_questions.render",
        "generate.contemplation.pass_manager",
        "chat",
        "chat.runtime",
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for forbidden in forbidden_modules:
                assert node.module != forbidden
                assert not node.module.startswith(forbidden + ".")
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_modules:
                    assert alias.name != forbidden
                    assert not alias.name.startswith(forbidden + ".")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "render_question"


def test_runtime_and_telemetry_public_schemas_are_not_changed_by_acquisition_slice() -> None:
    runtime_path = Path(__file__).resolve().parents[1] / "chat" / "runtime.py"
    telemetry_path = Path(__file__).resolve().parents[1] / "chat" / "telemetry.py"
    identity_path = Path(__file__).resolve().parents[1] / "core" / "physics" / "identity.py"

    runtime_tree = ast.parse(runtime_path.read_text(encoding="utf-8"), filename=str(runtime_path))

    for node in ast.walk(runtime_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "chat":
            arg_names = [arg.arg for arg in node.args.args + node.args.kwonlyargs]
            assert "contemplation_result" not in arg_names
        if isinstance(node, ast.ClassDef) and node.name == "ChatResponse":
            field_names = [
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            ]
            assert "disposition" not in field_names

    assert "disposition" not in telemetry_path.read_text(encoding="utf-8")

    identity_source = identity_path.read_text(encoding="utf-8")
    turn_event_section = identity_source[identity_source.index("class TurnEvent") :]
    assert "disposition" not in turn_event_section
