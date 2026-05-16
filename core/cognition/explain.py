"""Deterministic introspection — produce a natural-language account of a turn.

``explain(result)`` returns a canonical re-statement of the turn that, when
fed back through a fresh ``CognitiveTurnPipeline``, re-routes to the same
intent classification and proposition graph, and produces a surface whose
token coverage of the original is high.

This is the ADR-0018 typed-deterministic-operator companion to the
inference walk: it inverts the articulation path back to a canonical
prompt that re-instantiates the turn.  Pure dispatch on the intent tag;
no learned model; no external IO; replay-safe by construction.

Per ADR-0017 (Responsive-with-Axiology), this is a per-turn operation
invoked on a turn-id (here: directly on the CognitiveTurnResult);
introspection never runs autonomously between turns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from generate.intent import IntentTag

if TYPE_CHECKING:
    from core.cognition.result import CognitiveTurnResult


# Reverse map of generate.intent._RELATION_NORMALIZE — picks one surface
# form per canonical relation so the canonical prompt re-classifies under
# the same TRANSITIVE_QUERY shape.
_CANONICAL_RELATION_SURFACE: dict[str, str] = {
    "precedes": "precede",
    "causes": "cause",
    "grounds": "ground",
    "reveals": "reveal",
    "means": "mean",
    "follows": "follow",
    "contrasts_with": "contrast with",
    "produces": "produce",
}


def _explain_definition(subject: str) -> str:
    return f"What is {subject.strip()}?"


def _explain_transitive_query(subject: str, relation: str | None) -> str:
    subject = subject.strip()
    relation = (relation or "").strip()
    if relation == "belongs_to":
        return f"Where does {subject} belong?"
    surface = _CANONICAL_RELATION_SURFACE.get(relation, relation)
    if not surface:
        return f"What is {subject}?"
    return f"What does {subject} {surface}?"


def _explain_cause(subject: str) -> str:
    return f"Why {subject.strip()}?"


def _explain_procedure(subject: str) -> str:
    subject = subject.strip()
    return f"How do I {subject}?"


def _explain_comparison(subject: str, secondary: str | None) -> str:
    secondary = (secondary or "").strip() or "<missing>"
    return f"Compare {subject.strip()} and {secondary}."


def _explain_correction(subject: str, correction_text: str) -> str:
    # Corrections store the full proposition in ``subject`` (e.g. "wisdom
    # is judgment.") so the canonical form is the discourse-marked surface
    # of that proposition.  Fall back to the original correction_text when
    # the candidate carried it, which is the strict identity case.
    body = correction_text.strip() or f"Actually {subject.strip()}"
    return body


def _explain_verification(subject: str) -> str:
    return f"Is {subject.strip()}?"


def _explain_recall(subject: str) -> str:
    return f"Remember {subject.strip()}."


def explain(result: "CognitiveTurnResult") -> str:
    """Return a canonical natural-language account of the turn.

    The returned string is the introspection round-trip's input: feeding
    it back through a fresh pipeline reproduces the original turn's intent
    classification and (modulo identical initial pipeline state) its
    surface.  Empty intent or UNKNOWN intent returns an empty string,
    which the introspection lane scores as M2 failure.
    """
    intent = result.intent
    if intent is None:
        return ""

    tag = intent.tag
    subject = intent.subject or ""

    if tag is IntentTag.DEFINITION:
        return _explain_definition(subject)
    if tag is IntentTag.TRANSITIVE_QUERY:
        return _explain_transitive_query(subject, intent.relation)
    if tag is IntentTag.CAUSE:
        return _explain_cause(subject)
    if tag is IntentTag.PROCEDURE:
        return _explain_procedure(subject)
    if tag is IntentTag.COMPARISON:
        return _explain_comparison(subject, intent.secondary_subject)
    if tag is IntentTag.CORRECTION:
        correction_text = ""
        if result.teaching_candidate is not None:
            correction_text = result.teaching_candidate.correction_text
        return _explain_correction(subject, correction_text)
    if tag is IntentTag.VERIFICATION:
        return _explain_verification(subject)
    if tag is IntentTag.RECALL:
        return _explain_recall(subject)
    return ""
