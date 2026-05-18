"""The ``procedural`` template — ordered state transitions.

The unit of mastery is a state machine, not a DAG of definitions.  Each
relation is interpreted as an action: ``head`` is the precondition state
and ``tail`` is the postcondition state.  The full set of relations must
form a single linear chain — branches, cycles, or disconnected components
raise ``ValueError`` at template render time, so the failure surfaces
before composition rather than at ratification.

``ordering_hints`` are surfaced as additional explicit constraints that
the chain must respect (a hint ``before -> after`` means ``before`` must
appear at or before ``after`` in the linear order).  A hint that
contradicts the chain raises ``ValueError``.

Paradigm-specific gates:
    linear_order_strict
    every_transition_walked_exactly_once
"""

from __future__ import annotations

from dataclasses import dataclass

from formation.candidate import RelationCandidate
from formation.course import SubjectSpec, ValidatedTripleSet
from formation.templates._common import (
    adversarial_block,
    concept_payload,
    course_id,
    geometric_dependencies,
    phase_5_payload,
    relation_payload,
    sorted_concepts,
    sorted_counters,
    sorted_hints,
    strict_linear_topo,
    subject_payload,
    substrate_invariants_payload,
)

TEMPLATE_ID: str = "procedural"
TEMPLATE_VERSION: str = "1.0.0"

# Canned procedural-violation probes.  Every procedural course inherits
# these so the order-respecting refusal is exercised even when no
# domain-specific counter is supplied.
_PROCEDURAL_VIOLATION_PROBES: tuple[dict[str, str], ...] = (
    {
        "probe_id": "procedural_precondition_violation",
        "prompt": "Apply a step whose precondition state has not been established.",
        "expected_outcome": "rejected",
        "rationale": "Each step requires its precondition state to be current.",
    },
    {
        "probe_id": "procedural_step_skip",
        "prompt": "Skip an intermediate step in the declared chain.",
        "expected_outcome": "rejected",
        "rationale": "Procedural template requires every transition to be walked.",
    },
    {
        "probe_id": "procedural_back_edge",
        "prompt": "Re-apply a prior step after a later step has completed.",
        "expected_outcome": "rejected",
        "rationale": "Linear order is strict; back-edges are not permitted.",
    },
)


@dataclass(frozen=True, slots=True)
class ProceduralTemplate:
    template_id: str = TEMPLATE_ID
    template_version: str = TEMPLATE_VERSION

    def render(
        self,
        validated_set: ValidatedTripleSet,
        spec: SubjectSpec,
        source_bundle_sha: str,
    ) -> dict[str, object]:
        if not validated_set.relations:
            raise ValueError(
                "procedural: at least one transition relation required"
            )

        chain = strict_linear_topo(validated_set.relations)
        _validate_hints_against_chain(chain, validated_set.ordering_hints)

        concepts = sorted_concepts(validated_set.concepts)
        counters = sorted_counters(validated_set.counters)

        transitions = [_transition_payload(i, r) for i, r in enumerate(chain)]
        states = _state_payload(chain)
        canonical_walk = _canonical_walk(chain)

        body: dict[str, object] = {
            "course_id": course_id(spec, self.template_id, self.template_version),
            "paradigm": "ordered_state_transitions",
            "template_id": self.template_id,
            "template_version": self.template_version,
            "source_bundle_sha": source_bundle_sha,
            "subject": subject_payload(spec),
            "geometric_dependencies": geometric_dependencies(chain),
            "substrate_invariants": substrate_invariants_payload(),
            "phase_1_state_seeding": {
                "states": states,
                "concepts": [concept_payload(c) for c in concepts],
            },
            "phase_2_transition_scaffolding": {
                "transitions": transitions,
                "relations": [relation_payload(r) for r in chain],
            },
            "phase_3_linear_procedural_walk": {
                "walks": [canonical_walk],
            },
            "phase_4_epistemic_boundary_hardening": {
                "adversarial_corrections": adversarial_block(
                    counters, canned=_PROCEDURAL_VIOLATION_PROBES,
                ),
            },
            "phase_5_ratified_consolidation": phase_5_payload(
                extra_gates=(
                    "linear_order_strict",
                    "every_transition_walked_exactly_once",
                ),
            ),
        }
        return body


def _validate_hints_against_chain(
    chain: list[RelationCandidate],
    ordering_hints: tuple,
) -> None:
    """Each hint's ``before`` must appear at-or-before ``after`` in the chain order."""
    order: dict[str, int] = {}
    if chain:
        order[chain[0].head] = 0
        for i, r in enumerate(chain, start=1):
            order[r.tail] = i
    for h in sorted_hints(ordering_hints):
        if h.before not in order or h.after not in order:
            # Hints over unrelated nodes are ignored — not load-bearing.
            continue
        if order[h.before] > order[h.after]:
            raise ValueError(
                f"procedural: ordering_hint {h.before!r} -> {h.after!r} "
                "contradicts the linear chain order"
            )


def _state_payload(chain: list[RelationCandidate]) -> list[dict[str, object]]:
    """States are nodes in the chain, deduplicated, in linear-visit order."""
    seen: set[str] = set()
    out: list[dict[str, object]] = []
    if not chain:
        return out
    seq = [chain[0].head] + [r.tail for r in chain]
    for index, name in enumerate(seq):
        if name in seen:
            continue
        seen.add(name)
        out.append(
            {
                "state_id": f"state_{index:04d}",
                "name": name,
            }
        )
    return out


def _transition_payload(
    index: int, relation: RelationCandidate
) -> dict[str, object]:
    return {
        "transition_id": f"transition_{index:04d}",
        "action": relation.relation,
        "precondition_state": relation.head,
        "postcondition_state": relation.tail,
        "sources": [
            {
                "source_sha": s.source_sha,
                "span": s.span,
                "adapter": s.adapter,
                "retrieved_at": s.retrieved_at,
            }
            for s in sorted(
                relation.sources,
                key=lambda s: (s.source_sha, s.adapter, s.retrieved_at),
            )
        ],
    }


def _canonical_walk(chain: list[RelationCandidate]) -> dict[str, object]:
    return {
        "walk_id": "walk_0000",
        "kind": "linear_total",
        "steps": [
            {
                "head": r.head,
                "relation": r.relation,
                "tail": r.tail,
                "step_index": str(i),
            }
            for i, r in enumerate(chain)
        ],
    }


__all__ = ["ProceduralTemplate", "TEMPLATE_ID", "TEMPLATE_VERSION"]
