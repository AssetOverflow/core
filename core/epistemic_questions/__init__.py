"""Q1-C — the grounded-only epistemic question renderer (off-serving).

Turns an ASK :class:`~core.epistemic_disclosure.limitation.LimitationAssessment`
into an :class:`~core.epistemic_questions.render.EpistemicQuestion` under the
wrong=0 grounded-rendering invariant (scoping §2). Render only; no bus delivery,
no served disposition, no serving — that is Q1-D.
"""

from __future__ import annotations

from core.epistemic_questions.render import (
    EpistemicQuestion,
    render_question,
)

__all__ = [
    "EpistemicQuestion",
    "render_question",
]
