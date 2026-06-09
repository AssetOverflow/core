"""The epistemic question organ — render (Q1-C) and off-serving delivery (Q1-D).

Q1-C (:mod:`core.epistemic_questions.render`) turns an ASK
:class:`~core.epistemic_disclosure.limitation.LimitationAssessment` into an
:class:`~core.epistemic_questions.render.EpistemicQuestion` under the wrong=0
grounded-rendering invariant (scoping §2) — render only, no fabrication.

Q1-D (:mod:`core.epistemic_questions.delivery`) routes that rendered question onto
the contemplation bus as the ``QUESTION_NEEDED`` tenant and writes a proposal-only
artifact to the ``teaching/questions`` sink — consuming the renderer verbatim, never
rendering. Off-serving: no served surface, no ``ask_serving_enabled`` yet.
"""

from __future__ import annotations

from core.epistemic_questions.delivery import (
    AnswerBinding,
    DeliveredQuestion,
    DeliveryOutcome,
    default_question_root,
    deliver_ask,
    emit_question,
    question_path,
)
from core.epistemic_questions.render import (
    EpistemicQuestion,
    render_question,
)

__all__ = [
    "AnswerBinding",
    "DeliveredQuestion",
    "DeliveryOutcome",
    "EpistemicQuestion",
    "default_question_root",
    "deliver_ask",
    "emit_question",
    "question_path",
    "render_question",
]
