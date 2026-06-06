"""Determination-closure lane — the falsification for Step D (CLOSE).

Proves — deterministically, not by assertion — that idle consolidation makes the engine
LEARN from its determined facts: the set it can answer DIRECTLY climbs monotonically
across idle ticks to the deductive-closure fixed point, and a further tick is a no-op.

The soak seeds a deep is-a chain (``member(rex, c0)`` + ``subset(c0, c1) … subset(cₙ₋₁,
cₙ)``) through the REAL comprehend → realize path, then runs ``consolidate_once``
repeatedly. After each tick it records the directly-realized closure size. The lane also
carries the wrong=0 canary (a ``member ∘ member`` trap that must NEVER be derived) and
the provenance replay obligation (every derived record must re-verify ENTAILED from its
recorded premises — so the soundness claim can MEANINGFULLY FAIL).

Determinism: no clock, no LLM, no metric call; a pure function of the seeded chain.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from chat.runtime import ChatRuntime
from generate.determine.consolidate import consolidate_once
from generate.determine.determine import Determined, _verify_subsumption
from generate.meaning_graph.reader import comprehend
from generate.realize import RealizedRecord, realize_comprehension, recall_realized
from session.context import SessionContext

_HIGH_REPROJECT = 10**9

#: A deep is-a chain whose every ``All <plural[i]> are <plural[i+1]>`` parses as a
#: ``subset`` edge (singular lemmas: dog → mammal → … → item). The seed subject ``rex``
#: is a member of ``dog``; the chain gives 9 subset edges, so the closure reaches 10
#: classes from the one told membership.
_CHAIN_PLURALS = (
    "dogs",
    "mammals",
    "animals",
    "creatures",
    "beings",
    "mortals",
    "things",
    "entities",
    "objects",
    "items",
)
#: Singular lemmas the reader produces for the chain (what realized facts are keyed on).
_CHAIN_LEMMAS = (
    "dog",
    "mammal",
    "animal",
    "creature",
    "being",
    "mortal",
    "thing",
    "entity",
    "object",
    "item",
)
_SEED_SUBJECT = "rex"

#: The wrong=0 canary: ``member(dog, kingdom)`` is a membership ABOUT the class ``dog``.
#: With ``member(rex, dog)`` also held, an unsound ``member ∘ member`` rule would derive
#: ``member(rex, kingdom)``. The sound closure must NEVER produce it.
_CANARY_CLASS_MEMBERSHIP = ("Dog", "kingdom")  # → member(dog, kingdom)
_CANARY_FORBIDDEN = (_SEED_SUBJECT, "kingdom")  # member(rex, kingdom) must never appear


@dataclass(frozen=True, slots=True)
class TickRecord:
    """One idle consolidation tick's outcome."""

    tick: int
    member_closure_size: int  # directly-realized member(rex, ·) facts
    considered: int
    consolidated: int
    at_fixed_point: bool


def _fresh_context() -> SessionContext:
    rt = ChatRuntime(no_load_state=True)
    return SessionContext(
        vocab=rt._context.vocab,
        persona=rt._context.persona,
        vault_reproject_interval=_HIGH_REPROJECT,
    )


def _tell(ctx: SessionContext, text: str) -> None:
    realize_comprehension(comprehend(text), ctx)


def seed_chain(ctx: SessionContext, depth: int) -> None:
    """Seed ``member(rex, c0)`` + ``depth`` subset edges + the canary, via the REAL
    comprehend → realize path. ``depth`` is clamped to the available chain length."""
    depth = max(1, min(depth, len(_CHAIN_PLURALS) - 1))
    _tell(ctx, f"{_SEED_SUBJECT.capitalize()} is a {_CHAIN_LEMMAS[0]}.")
    for i in range(depth):
        _tell(ctx, f"All {_CHAIN_PLURALS[i]} are {_CHAIN_PLURALS[i + 1]}.")
    # Canary membership about the class (member ∘ member trap).
    _tell(ctx, f"{_CANARY_CLASS_MEMBERSHIP[0]} is a {_CANARY_CLASS_MEMBERSHIP[1]}.")


def _member_closure(ctx: SessionContext) -> tuple[str, ...]:
    """The objects ``rex`` is DIRECTLY realized to be a member of (sorted)."""
    return tuple(
        sorted(
            f.relation_arguments[1]
            for f in recall_realized(ctx, subject=_SEED_SUBJECT, predicate="member")
        )
    )


def _order_subset_path(
    start: str, premises: tuple[RealizedRecord, ...]
) -> tuple[RealizedRecord, ...]:
    """Order subset premise records into a path from ``start`` (forward walk)."""
    by_src: dict[str, RealizedRecord] = {
        p.relation_arguments[0]: p for p in premises if len(p.relation_arguments) == 2
    }
    path: list[RealizedRecord] = []
    cur = start
    while cur in by_src:
        edge = by_src.pop(cur)
        path.append(edge)
        cur = edge.relation_arguments[1]
    return tuple(path)


def reverify_derived(ctx: SessionContext, record: RealizedRecord) -> bool:
    """Re-verify a derived record ENTAILED from its RECORDED premises (the provenance
    replay obligation). Re-fetches each premise by ``structure_key`` and re-runs the
    SAME sound+complete decider — so a record whose stored premises do not actually
    entail it fails loudly."""
    if not record.derived or record.derivation is None:
        return False
    premises: list[RealizedRecord] = []
    for key in record.derivation.premise_structure_keys:
        hits = recall_realized(ctx, structure_key=key)
        if len(hits) != 1:
            return False  # a premise vanished or is ambiguous → cannot stand
        premises.append(hits[0])
    subject, target = record.relation_arguments
    member_premises = tuple(p for p in premises if p.relation_predicate == "member")
    subset_premises = tuple(p for p in premises if p.relation_predicate == "subset")
    if record.relation_predicate == "member":
        if len(member_premises) != 1:
            return False
        member_fact = member_premises[0]
        path = _order_subset_path(member_fact.relation_arguments[1], subset_premises)
        verdict = _verify_subsumption(
            "member", subject, target, member_fact=member_fact, subset_path=path
        )
    else:
        path = _order_subset_path(subject, subset_premises)
        verdict = _verify_subsumption(
            "subset", subject, target, member_fact=None, subset_path=path
        )
    return isinstance(verdict, Determined)


def run(depth: int = 9) -> dict[str, Any]:
    """Soak the closure and return the falsification report.

    Runs to the fixed point (bounded by ``depth + 2`` ticks — a safety backstop, never
    reached by a converging closure), then computes the falsification verdicts.
    """
    ctx = _fresh_context()
    seed_chain(ctx, depth)
    effective_depth = max(1, min(depth, len(_CHAIN_PLURALS) - 1))

    trajectory: list[TickRecord] = []
    pre = len(_member_closure(ctx))
    trajectory.append(TickRecord(0, pre, 0, 0, False))
    max_ticks = effective_depth + 2
    tick = 0
    while tick < max_ticks:
        tick += 1
        result = consolidate_once(ctx)
        trajectory.append(
            TickRecord(
                tick=tick,
                member_closure_size=len(_member_closure(ctx)),
                considered=result.considered,
                consolidated=result.consolidated,
                at_fixed_point=result.at_fixed_point,
            )
        )
        if result.at_fixed_point:
            break

    sizes = [t.member_closure_size for t in trajectory]
    # Monotone non-decreasing across all ticks; strictly increasing on every tick that
    # consolidated something (a real layer must enlarge the directly-answerable set).
    monotone = all(b >= a for a, b in zip(sizes, sizes[1:]))
    strict_on_work = all(
        t.member_closure_size > trajectory[i].member_closure_size
        for i, t in enumerate(trajectory[1:])
        if t.consolidated > 0
    )
    converged = trajectory[-1].at_fixed_point
    # rex reaches every class on the chain it was seeded into (c0 told + c1..c_depth).
    final_closure = list(_member_closure(ctx))
    expected_closure = sorted(_CHAIN_LEMMAS[: effective_depth + 1])
    closure_complete = final_closure == expected_closure

    # wrong=0: the member ∘ member canary is never derived, and no class outside the
    # chain ever appears in rex's closure.
    forbidden_present = _CANARY_FORBIDDEN[1] in final_closure
    chain_set = set(_CHAIN_LEMMAS[: effective_depth + 1])
    no_fabricated = set(final_closure) <= chain_set

    # Provenance replay: every derived record re-verifies ENTAILED from its premises.
    derived_records = [
        r
        for r in recall_realized(ctx)
        if r.derived and r.relation_predicate in ("member", "subset")
    ]
    provenance_replay_ok = all(reverify_derived(ctx, r) for r in derived_records)
    all_derived_speculative = all(
        r.epistemic_status == "speculative" for r in derived_records
    )

    falsification_met = (
        monotone
        and strict_on_work
        and converged
        and closure_complete
        and not forbidden_present
        and no_fabricated
        and provenance_replay_ok
        and all_derived_speculative
    )

    return {
        "depth": effective_depth,
        "trajectory": [asdict(t) for t in trajectory],
        "member_closure_sizes": sizes,
        "final_member_closure": final_closure,
        "expected_member_closure": expected_closure,
        "derived_record_count": len(derived_records),
        "verdicts": {
            "monotone": monotone,
            "strict_increase_on_consolidating_tick": strict_on_work,
            "converged_to_fixed_point": converged,
            "closure_complete": closure_complete,
            "canary_member_member_never_derived": not forbidden_present,
            "no_fabricated_membership": no_fabricated,
            "provenance_replay_ok": provenance_replay_ok,
            "all_derived_speculative": all_derived_speculative,
        },
        "falsification_met": falsification_met,
    }
