"""Q1-D — off-serving ASK delivery: route a rendered question onto the bus.

The fourth and final Q1 rung. Given an ``ask_question``
:class:`~core.epistemic_disclosure.limitation.LimitationAssessment`, decide the
contemplation :class:`~generate.contemplation.findings.Terminal` and, when a question
can honestly be asked, produce a :class:`DeliveredQuestion` artifact for the
proposal-only ``teaching/questions`` sink. This is the ASK analogue of the
proposal-only :mod:`core.comprehension_attempt.proposal` emitter — and just as
toothless: it never serves, never mounts, always requires review.

**The rung separation (the steer).** Q1-D *consumes* the Q1-C
:class:`~core.epistemic_questions.render.EpistemicQuestion` — it does NOT render.
:func:`render_question` is called exactly once (in :func:`deliver_ask`) and its
result is wrapped verbatim; Q1-D constructs no user-facing prose of its own, so the
Q1-C grounded-rendering wrong=0 guard is never bypassed by a second surface.

    Q1-B: typed residue        (what is missing, as typed slots)
    Q1-C: renderability         (can it be asked without fabricating? → EpistemicQuestion)
    Q1-D: delivery              (route the rendered question onto the bus)   ← here

**D2 — the delivery-side wrong=0 guard.** A contentless ``QUESTION_NEEDED`` is worse
than useless: it is a *false intake surface* (the user is invited to answer a question
that names nothing). So when :func:`render_question` returns ``unrenderable``
(``renderability_gap`` / ``multi_slot_not_supported`` / ``no_missing_slot`` / the
fabrication backstop), :func:`deliver_ask` does NOT emit ``QUESTION_NEEDED``. It falls
back to the family's *standing disposition*:

    family still proposes (``proposal_allowed``) → ``PROPOSAL_EMITTED``
    otherwise                                    → ``NO_PROGRESS``

This guard is enforced twice: in :func:`deliver_ask`'s branch, and structurally — a
:class:`DeliveredQuestion` *cannot wrap an unrenderable question* (its
``__post_init__`` refuses), so ``QUESTION_NEEDED`` is unreachable without a real,
rendered question.

**D3 — the carve-out stays.** Q1-D delivery is OFF-SERVING. It does not flip the
``Q1B_ASK_CARVE_OUT`` (``missing_total_count`` / ``missing_weighted_total`` keep
``proposal_allowed = True`` in the registry, so the proposal pile keeps working). Both
signals coexist during the carve-out — the off-serving question artifact AND the
existing proposal — so no operational signal is lost. The flip to ``ask`` waits on a
future ``ask_serving_enabled`` gate, not on this rung.

**D5 — single-slot only.** Q1-C refuses multi-slot rendering, so Q1-D delivers at most
one ``DeliveredQuestion`` per assessment; a multi-slot assessment is ``unrenderable``
(``multi_slot_not_supported``) and takes the D2 fallback. No fan-out here.

**Off-serving.** Imports nothing from ``generate.derivation`` / ``core.reliability_gate``;
it cannot move the sealed GSM8K metric, and there is NO served surface — no
``ask_serving_enabled``, no ``chat/runtime.py`` wiring. The artifacts land in the
review-gated teaching sink and nowhere else.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.comprehension_attempt.failure_family import family_by_name
from core.epistemic_disclosure.limitation import LimitationAssessment
from core.epistemic_questions.render import EpistemicQuestion, render_question
from generate.contemplation.findings import Terminal

#: The sink status — the ASK analogue of the proposal emitter's ``"proposal_only"``.
#: A delivered question is review-gated intake, never a served answer.
_QUESTION_STATUS = "question_only"


@dataclass(frozen=True, slots=True)
class AnswerBinding:
    """RESERVED for Q2 — the typed seat a future answer round-trip binds into.

    Q1-D produces NO ``AnswerBinding`` (every :class:`DeliveredQuestion` carries
    ``answer_binding = None``; see that class's ``__post_init__``). The seat exists so
    the Q2 binder — which must re-enter the limitation gate with augmented input, never
    mutate the model mid-flight (scoping §4) — is wireable without reshaping the
    artifact. ``target_slot`` / ``binding_target`` mirror the
    :class:`~core.epistemic_disclosure.limitation.MissingSlot` the answer fills.
    """

    target_organ: str
    target_slot: str
    binding_target: str
    parser: str
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveredQuestion:
    """A proposal-only ASK artifact wrapping a rendered Q1-C question.

    The invariant fields are enforced in ``__post_init__`` so even a hand-constructed
    instance cannot become a contentless question, a served question, or an
    answer-bound (Q2) question — illegal states are unrepresentable:

    - it can never wrap an ``unrenderable`` question (the D2 guard, structurally) —
      so a ``QUESTION_NEEDED`` terminal always carries real, rendered text;
    - it can never be ``served`` (off-serving; ``ask_serving_enabled`` does not exist);
    - it always ``requires_review``;
    - its ``answer_binding`` is always ``None`` in Q1-D (the Q2 seat is reserved, unbound).
    """

    question: EpistemicQuestion
    owner_organ: str | None
    blocking_reason: str
    answer_binding: AnswerBinding | None = None
    status: str = _QUESTION_STATUS
    requires_review: bool = True
    served: bool = False

    def __post_init__(self) -> None:
        if self.question.unrenderable or self.question.text is None:
            raise ValueError(
                "a DeliveredQuestion cannot wrap an unrenderable question "
                f"(reason={self.question.reason!r}); the D2 fallback handles it"
            )
        if self.status != _QUESTION_STATUS:
            raise ValueError(
                f"question status must be {_QUESTION_STATUS!r}; got {self.status!r}"
            )
        if self.served:
            raise ValueError("a Q1-D delivered question is never served")
        if not self.requires_review:
            raise ValueError("a delivered question always requires review")
        if self.answer_binding is not None:
            raise ValueError("answer_binding is reserved for Q2; Q1-D emits None")

    def content_hash(self) -> str:
        """Deterministic content address: same question on the same blocking family and
        slot always yields the same hash (idempotent sink writes). No clock, no
        randomness. The rendered ``text`` is included so a template change re-addresses.
        """
        slot_name = self.question.slot.slot_name if self.question.slot else ""
        payload = f"{self.blocking_reason}:{slot_name}:{self.question.text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_json_dict(self) -> dict[str, Any]:
        slot = self.question.slot
        return {
            "status": self.status,
            "blocking_reason": self.blocking_reason,
            "owner_organ": self.owner_organ,
            "question": {
                "text": self.question.text,
                "reason": self.question.reason,
                "slot_name": slot.slot_name if slot else None,
                "expected_unit_or_type": slot.expected_unit_or_type if slot else None,
                "binding_target": slot.binding_target if slot else None,
            },
            "answer_binding": None,  # reserved (Q2)
            "requires_review": self.requires_review,
            "served": self.served,
        }


@dataclass(frozen=True, slots=True)
class DeliveryOutcome:
    """The result of routing one ``ask_question`` assessment.

    ``question`` is the artifact iff ``terminal is QUESTION_NEEDED`` (a renderable ask);
    otherwise it is ``None`` and ``fallback_reason`` carries the unrenderable reason that
    triggered the D2 standing-disposition fallback.
    """

    terminal: Terminal
    question: DeliveredQuestion | None
    fallback_reason: str | None


def _standing_disposition(blocking_reason: str) -> Terminal:
    """The D2 fallback terminal for an unrenderable ask: the family's standing move.

    A family that still proposes (``proposal_allowed``) falls back to
    ``PROPOSAL_EMITTED`` — its existing operational signal, preserved (D3). Anything
    else (an unknown reason, or a family that does not propose) falls back to
    ``NO_PROGRESS``. Never a contentless ``QUESTION_NEEDED``.
    """
    family = family_by_name(blocking_reason)
    if family is not None and family.proposal_allowed:
        return Terminal.PROPOSAL_EMITTED
    return Terminal.NO_PROGRESS


def deliver_ask(assessment: LimitationAssessment) -> DeliveryOutcome:
    """Route an ``ask_question`` assessment to a terminal — render via Q1-C, never here.

    Renderable → ``QUESTION_NEEDED`` + a :class:`DeliveredQuestion` wrapping the Q1-C
    result verbatim. Unrenderable → the D2 standing-disposition fallback (no artifact).

    Raises ``ValueError`` if called on a non-ASK assessment: the bus routes only
    ``ask_question`` resolutions here, so any other action is a wiring error, not a
    runtime input — fail loudly rather than silently mis-deliver.
    """
    if assessment.resolution_action != "ask_question":
        raise ValueError(
            "deliver_ask is only valid for ask_question assessments; got "
            f"{assessment.resolution_action!r}"
        )

    question = render_question(assessment)
    if question.unrenderable:
        return DeliveryOutcome(
            terminal=_standing_disposition(assessment.blocking_reason),
            question=None,
            fallback_reason=question.reason,
        )

    delivered = DeliveredQuestion(
        question=question,
        owner_organ=assessment.owner_organ,
        blocking_reason=assessment.blocking_reason,
    )
    return DeliveryOutcome(
        terminal=Terminal.QUESTION_NEEDED,
        question=delivered,
        fallback_reason=None,
    )


def default_question_root() -> Path:
    """``<repo>/teaching/questions`` — the write-only, review-gated ASK sink.

    A sibling of ``teaching/proposals`` (D4): questions are intake requests, not
    capability proposals, so they do not overload the proposal pile.
    """
    return Path(__file__).resolve().parents[2] / "teaching" / "questions"


def question_path(delivered: DeliveredQuestion, root: Path | None = None) -> Path:
    base = root if root is not None else default_question_root()
    return base / f"{delivered.content_hash()}.json"


def emit_question(
    assessment: LimitationAssessment, *, root: Path | None = None
) -> Path | None:
    """Deliver an ask assessment and, iff it renders, write the artifact to the sink.

    Returns the artifact path for a ``QUESTION_NEEDED`` delivery, or ``None`` when the
    ask was unrenderable and fell back (D2) — no contentless artifact is ever written.
    Idempotent: the same question writes the same content-addressed path with
    byte-identical content (``sort_keys``). Creates the sink directory on demand.
    """
    outcome = deliver_ask(assessment)
    if outcome.question is None:
        return None
    path = question_path(outcome.question, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(outcome.question.to_json_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


__all__ = [
    "AnswerBinding",
    "DeliveredQuestion",
    "DeliveryOutcome",
    "default_question_root",
    "deliver_ask",
    "emit_question",
    "question_path",
]
