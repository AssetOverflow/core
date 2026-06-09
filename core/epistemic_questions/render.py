"""The grounded-only question renderer (Q1-C) — wrong=0-safe by construction.

This is the renderer rung of the Epistemic Disclosure ASK spine: given a
:class:`~core.epistemic_disclosure.limitation.LimitationAssessment` whose
``resolution_action == "ask_question"`` and which carries at least one typed
:class:`~core.epistemic_disclosure.limitation.MissingSlot`, produce an
:class:`EpistemicQuestion` — a rendered user-facing question, or an explicit
``question_unrenderable`` verdict. Nothing here delivers, serves, or chooses a
disposition (that is Q1-D); this is *only* surface realization of the residue.

**The wrong=0 invariant (scoping §2 / session §1.5.7) — the whole point.**

    A question may name an entity, slot, unit, or relation only if it appears
    *verbatim* in the assessment's ``grounded_terms``. When the grounded terms
    lack what a question needs, degrade to a generic question or emit
    ``question_unrenderable`` — never a named guess.

Two substrate facts force the conservative policy below:

1. ``grounded_terms`` is empty for every assessment produced today — the readers
   do not yet emit verbatim evidence on refusal (scoping §3, the substrate gap
   Q1 must close first). So there is no grounded problem-entity to name.
2. A *missing* slot's referent is, by definition, absent from the comprehension
   trace — the missing thing can never appear in ``grounded_terms`` even once
   readers do emit evidence. ``grounded_terms`` can only supply *context*
   entities, and binding a slot to its context entity needs an alignment step
   that Q1-C does not have (a later rung).

**Chosen rendering policy — generic-structural, names zero problem entities.**

Because Q1-C can neither (today) read grounded context nor (ever, for the slot
itself) name the missing referent from grounded text, the only wrong=0-safe
artifact it can render is a *generic* question whose sole variable content is a
controlled English phrase for the slot's structural *type*
(``expected_unit_or_type``), drawn from the closed, audited
:data:`_CLOSED_TYPE_PHRASES` map below. Concretely the renderer:

- NEVER surfaces ``slot_name`` or ``binding_target`` — these are snake_case
  structural identifiers, and user-facing prose must never come from them
  (limitation.py ``MissingSlot`` docstring; session §1.5.7). ``slot_name`` is
  also the field most likely to *read* like a fabricated entity (``ben_rate`` →
  the forbidden "Ben"), so it is never touched.
- NEVER prettifies a snake_case identifier into a natural-language entity — no
  capitalization, no possessive, no splitting on underscores.
- Translates ``expected_unit_or_type`` through the closed map only; an unmapped
  type degrades to ``question_unrenderable`` (a ``renderability_gap``) rather
  than dumping raw snake_case or guessing.
- Names no problem-specific entity at all. The closed type phrases ("a
  whole-number count") are generic structural descriptors that assert nothing
  about *this* problem — distinct from problem-specific names, which would need
  grounding. This is the line scoping §2 draws ("generic, all terms grounded"
  vs. the fabricated "Ben").

A post-render fabrication guard (:func:`_names_only_grounded`) re-checks that
every word in the rendered text is closed-vocabulary scaffold or appears in
``grounded_terms`` — defense in depth so a fabricated token can never escape even
if the template were later edited carelessly.

**Off-serving.** Imports nothing from ``generate.derivation`` or
``core.reliability_gate``; it cannot move the sealed GSM8K metric.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.epistemic_disclosure.limitation import (
    LimitationAssessment,
    MissingSlot,
)

#: Closed, audited map from a family-pinned ``expected_unit_or_type`` to a
#: controlled English phrase. Keys are exactly the slot types that ship today
#: (``core.epistemic_disclosure.limitation._FAMILY_TO_MISSING_SLOTS``). A slot
#: whose type is absent here is NOT rendered — the renderer refuses with a
#: ``renderability_gap`` rather than surfacing raw snake_case. New slot types
#: earn a phrase here (with a test) when their family lands, never by guessing.
_CLOSED_TYPE_PHRASES: dict[str, str] = {
    "count_int": "a whole-number count",
    "measured_unit_int": "a whole-number quantity",
}

#: The fixed question scaffold. The only hole is the closed type phrase; every
#: other word is constant, problem-independent English. It names no entity.
_TEMPLATE = (
    "To answer this, one more value is still needed — {phrase} — that the "
    "problem does not state. What is it?"
)

#: Machine reasons for an :class:`EpistemicQuestion`. Closed set.
_REASON_RENDERED = "rendered"
_REASON_NOT_ASK = "not_ask"
_REASON_NO_SLOT = "no_missing_slot"
_REASON_RENDERABILITY_GAP = "renderability_gap"
_REASON_FABRICATION_GUARD = "fabrication_guard"


def _tokens(text: str) -> set[str]:
    """Lowercased maximal alphabetic runs — the unit the fabrication guard checks."""
    return set(re.findall(r"[a-z]+", text.lower()))


#: Every word the renderer is allowed to emit *without* grounding: the scaffold
#: words plus the words of every closed type phrase. Built once at import.
_ALLOWED_SCAFFOLD_WORDS: frozenset[str] = frozenset(
    _tokens(_TEMPLATE.replace("{phrase}", " "))
    | {w for phrase in _CLOSED_TYPE_PHRASES.values() for w in _tokens(phrase)}
)


@dataclass(frozen=True, slots=True)
class EpistemicQuestion:
    """The rendered ASK artifact, or an explicit unrenderable verdict.

    ``slot`` is the bound :class:`MissingSlot` the question is about — present
    whenever a slot was selected, ``None`` when the assessment carried no slot to
    bind (non-ASK, or zero slots). ``text`` is the rendered question, or ``None``
    when ``unrenderable``. ``reason`` is a closed-set machine string (one of the
    ``_REASON_*`` constants) explaining the verdict; for a renderable question it
    is :data:`_REASON_RENDERED`.
    """

    slot: MissingSlot | None
    text: str | None
    unrenderable: bool
    reason: str


def _unrenderable(reason: str, slot: MissingSlot | None = None) -> EpistemicQuestion:
    """A ``question_unrenderable`` verdict with no text."""
    return EpistemicQuestion(slot=slot, text=None, unrenderable=True, reason=reason)


def _names_only_grounded(text: str, grounded_terms: tuple[str, ...]) -> bool:
    """True iff every word in ``text`` is closed-vocab scaffold or grounded.

    The wrong=0 guard, enforced post-render as defense in depth: a fabricated
    entity (a word neither in the closed scaffold/phrase vocabulary nor verbatim
    in ``grounded_terms``) makes this return ``False``, and the renderer refuses.
    With today's empty ``grounded_terms`` and a fully closed-vocab template this
    holds by construction; the guard exists so that can never silently change.
    """
    allowed = _ALLOWED_SCAFFOLD_WORDS | _tokens(" ".join(grounded_terms))
    return _tokens(text) <= allowed


def render_question(assessment: LimitationAssessment) -> EpistemicQuestion:
    """Render a single-slot generic ASK question, or refuse to render.

    Single-slot only: the *first* missing slot is rendered; any others are
    ignored (later rungs may emit one question per slot). The renderer refuses
    (``question_unrenderable``) when the assessment is not an ASK, carries no
    slot, or the slot's structural type is outside the closed phrase map. It
    NEVER fabricates a natural-language entity name — see the module docstring
    for the policy and the wrong=0 rationale.
    """
    if assessment.resolution_action != "ask_question":
        return _unrenderable(_REASON_NOT_ASK)
    if not assessment.missing_slots:
        return _unrenderable(_REASON_NO_SLOT)

    slot = assessment.missing_slots[0]
    phrase = _CLOSED_TYPE_PHRASES.get(slot.expected_unit_or_type)
    if phrase is None:
        # Unknown structural type: refuse rather than surface raw snake_case.
        return _unrenderable(_REASON_RENDERABILITY_GAP, slot=slot)

    text = _TEMPLATE.format(phrase=phrase)
    if not _names_only_grounded(text, assessment.grounded_terms):
        # Unreachable by construction; the guard is the wrong=0 backstop.
        return _unrenderable(_REASON_FABRICATION_GUARD, slot=slot)

    return EpistemicQuestion(
        slot=slot, text=text, unrenderable=False, reason=_REASON_RENDERED
    )


__all__ = [
    "EpistemicQuestion",
    "render_question",
]
