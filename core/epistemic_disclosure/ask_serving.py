"""Stage 2 ASK served-surface artifact adapter.

This module is intentionally narrow: it validates a pre-rendered Q1-D
``DeliveredQuestion`` artifact and decides whether that artifact is eligible to
be exposed as a served ASK/QUESTION_NEEDED surface. It does not acquire
contemplation results from runtime and does not render question prose.

Validation enforces the Q1-D artifact contract:

- top-level JSON object only;
- ``status == "question_only"``;
- ``requires_review is True``;
- ``served is False``;
- ``answer_binding`` is absent or ``None``;
- ``question`` is an object;
- ``question.text`` is a non-empty string;
- ``question.slot_name`` is a non-empty string;
- ``question_path`` exists on disk and differs from ``proposal_path``.

Any validation failure fails closed to the caller's fallback surface and
standing disposition. The served text is consumed from the artifact exactly; no
runtime prose construction or mutation happens here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.epistemic_disclosure.disposition import ServedDisposition, choose_served_disposition
from core.epistemic_disclosure.limitation import LimitationAssessment
from core.epistemic_questions.serving_gate import ask_serving_enabled
from core.epistemic_state import EpistemicState

_MISSING = object()


@dataclass(frozen=True, slots=True)
class ServedAskDecision:
    """The adapter's served-ASK decision."""

    served: bool
    terminal: str
    surface: str
    disposition: ServedDisposition


def _terminal_value(contemplation_result: Any) -> str:
    terminal = getattr(contemplation_result, "terminal", None)
    if terminal is None:
        return "NO_PROGRESS"
    return str(getattr(terminal, "value", terminal))


def _fallback_disposition(terminal: str) -> ServedDisposition:
    if terminal == "PROPOSAL_EMITTED":
        return ServedDisposition.PROPOSE
    if terminal == "SOLVED_VERIFIED":
        return ServedDisposition.COMMIT
    return ServedDisposition.REFUSE


def _fallback_decision(contemplation_result: Any, fallback_surface: str) -> ServedAskDecision:
    terminal = _terminal_value(contemplation_result)
    return ServedAskDecision(
        served=False,
        terminal=terminal,
        surface=fallback_surface,
        disposition=_fallback_disposition(terminal),
    )


def _validate_question_artifact(data: Any, *, question_path: Path, proposal_path: Any) -> str | None:
    """Return the valid question text, or ``None`` for any contract violation."""

    if not isinstance(data, dict):
        return None
    if data.get("status") != "question_only":
        return None
    if data.get("requires_review") is not True:
        return None
    served = data.get("served", _MISSING)
    if served is _MISSING or served is not False:
        return None
    answer_binding = data.get("answer_binding", _MISSING)
    if answer_binding is not _MISSING and answer_binding is not None:
        return None

    question = data.get("question")
    if not isinstance(question, dict):
        return None

    text = question.get("text")
    if not isinstance(text, str) or not text.strip():
        return None

    slot_name = question.get("slot_name")
    if not isinstance(slot_name, str) or not slot_name.strip():
        return None

    if proposal_path is not None and str(question_path) == str(proposal_path):
        return None

    return text.strip()


def evaluate_served_ask(
    config: Any,
    contemplation_result: Any,
    fallback_surface: str,
) -> ServedAskDecision:
    """Evaluate whether a Q1-D question artifact may be surfaced as ASK.

    This is a bus/disposition adapter, not a renderer and not the runtime
    acquisition path. The caller supplies a contemplation result that already
    points to a delivered question artifact. When the gate is disabled or any
    artifact invariant fails, the adapter returns the fallback surface and the
    standing fallback disposition.
    """

    if not ask_serving_enabled(config):
        return _fallback_decision(contemplation_result, fallback_surface)

    if _terminal_value(contemplation_result) != "QUESTION_NEEDED":
        return _fallback_decision(contemplation_result, fallback_surface)

    question_path_value = getattr(contemplation_result, "question_path", None)
    proposal_path_value = getattr(contemplation_result, "proposal_path", None)
    if not question_path_value or question_path_value == proposal_path_value:
        return _fallback_decision(contemplation_result, fallback_surface)

    question_path = Path(question_path_value)
    if not question_path.is_file():
        return _fallback_decision(contemplation_result, fallback_surface)

    try:
        payload = json.loads(question_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _fallback_decision(contemplation_result, fallback_surface)

    question_text = _validate_question_artifact(
        payload,
        question_path=question_path,
        proposal_path=proposal_path_value,
    )
    if question_text is None:
        return _fallback_decision(contemplation_result, fallback_surface)

    limitation = LimitationAssessment(
        limitation_kind="missing_information",
        resolution_action="ask_question",
        epistemic_state=EpistemicState.UNDETERMINED,
        owner_organ=payload.get("owner_organ"),
        blocking_reason=str(payload.get("blocking_reason", "")),
    )
    disposition = choose_served_disposition(
        epistemic_state=EpistemicState.UNDETERMINED,
        limitation=limitation,
    )

    return ServedAskDecision(
        served=True,
        terminal="QUESTION_NEEDED",
        surface=question_text,
        disposition=disposition,
    )


__all__ = ["ServedAskDecision", "evaluate_served_ask"]
