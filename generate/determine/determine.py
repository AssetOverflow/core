"""DETERMINE (roadmap Step 4) — reason over realized structure → the honest gear.

A question (a query-bearing ``Comprehension``) is answered ONLY from what the held
self has already REALIZED (R0/R1 structural recall) — never from the field, never
from an LLM, never from absence. The verdict is **as-told, never "verified"**: every
realizable record is SPECULATIVE, and ``ADMISSIBLE_AS_EVIDENCE = {COHERENT}``, so a
determination grounded in SPECULATIVE records carries ``basis="as_told"`` — "based on
what I was told (unverified)". Until COHERENT promotion exists (out of scope), D0
produces only ``as_told`` assertions or ``Undetermined`` refusals. No estimation, no
corpus mutation (teaching stays HITL proposal-only).

wrong=0 / soundness (open-world): D0 asserts an answer ONLY when the asked relation
is DIRECTLY entailed by a realized fact. Absence of a fact never refutes it
(open-world), so D0 never asserts an answer from missing knowledge — it refuses
(``Undetermined``). It asserts only ``answer=True`` on a direct hit; it never asserts
False.

Slice D0 supports the realized, non-negated ``member`` relation (subsumption /
"Is X a Y?"). Negated questions and other query predicates are an honest
``Undetermined`` until their realized form + entailment predicate land — D0 ships no
entailment path it cannot exercise.
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.meaning_graph.reader import Comprehension, Refusal
from generate.realize import RealizedRecord, recall_realized
from session.context import SessionContext
from teaching.epistemic import ADMISSIBLE_AS_EVIDENCE, EpistemicStatus

#: The only realized relation D0 can reason over in this slice.
_SUPPORTED_PREDICATE = "member"


@dataclass(frozen=True, slots=True)
class Determined:
    """An answer reasoned from realized structure.

    ``basis`` is the epistemic standing of the grounding: ``"as_told"`` when the
    grounds are SPECULATIVE (candidate memory — the only case today), ``"verified"``
    only if every ground is admissible-as-evidence (COHERENT — not yet reachable).
    ``answer`` is the truth of the asked (possibly negated) question.
    """

    answer: bool
    basis: str
    predicate: str
    subject: str
    object: str
    grounds: tuple[RealizedRecord, ...]


@dataclass(frozen=True, slots=True)
class Undetermined:
    """No honest answer (refusal). ``reason`` is for audit, not control."""

    reason: str


def _basis(grounds: tuple[RealizedRecord, ...]) -> str:
    """Carry the grounds' epistemic standing forward — never overclaim "verified"."""
    statuses = {EpistemicStatus(g.epistemic_status) for g in grounds}
    return "verified" if statuses and statuses <= ADMISSIBLE_AS_EVIDENCE else "as_told"


def determine(
    question: Comprehension | Refusal, ctx: SessionContext
) -> Determined | Undetermined:
    """Answer a membership question from realized structure, or refuse.

    Eligibility: a query-bearing ``Comprehension`` with exactly one ``member`` query.
    The answer is asserted ONLY on direct structural entailment by a realized
    ``member`` fact; everything else is a typed ``Undetermined`` (open-world: absence
    never asserts a positive answer).
    """
    if isinstance(question, Refusal):
        return Undetermined("refusal")
    if not isinstance(question, Comprehension):
        return Undetermined("not_a_comprehension")
    if len(question.queries) != 1:
        return Undetermined("not_single_query")  # a determination answers one question

    query = question.queries[0]
    if query.predicate != _SUPPORTED_PREDICATE:
        return Undetermined("unsupported_query")  # honest: only `member` in D0
    if len(query.arguments) != 2:
        return Undetermined("malformed_query")  # member is binary by construction
    if query.negated:
        # Realized facts are all positive (R0/R1 refuse negated relations), so a
        # negated question would only ever be answered from the positive's presence.
        # D0 declines it explicitly rather than ship an entailment path the reader
        # cannot exercise (it refuses negated membership questions upstream anyway).
        return Undetermined("negated_query_unsupported")

    subject, target = query.arguments[0], query.arguments[1]

    # Structural recall: the realized member facts about this subject (R1a). Exact,
    # deterministic, versor-collision-irrelevant — never a metric call.
    facts = recall_realized(ctx, subject=subject, predicate=_SUPPORTED_PREDICATE)
    if not facts:
        return Undetermined("ungrounded")  # nothing realized about the subject

    # Direct entailment: a realized member(subject, target) holds as-told. Open-world:
    # member facts about the subject that do NOT match the asked target never refute
    # it, so a miss is a refusal (``not_entailed``), never an asserted False.
    grounding = next((f for f in facts if f.relation_arguments == (subject, target)), None)
    if grounding is None:
        return Undetermined("not_entailed")

    return Determined(
        answer=True,
        basis=_basis((grounding,)),
        predicate=_SUPPORTED_PREDICATE,
        subject=subject,
        object=target,
        grounds=(grounding,),
    )
