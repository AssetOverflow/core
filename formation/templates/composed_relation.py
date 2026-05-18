"""The ``composed_relation`` template — chains as the unit of mastery.

Layer 4 of the teaching order (see ``docs/teaching_order.md``).  Where the
``definition`` template treats every relation as an independent edge, this
template treats *chains of relations* as first-class objects.  Each maximal
chain of length >= 2 produces a ``composed_relation`` entry that names the
inferred relation the chain licenses, classifies the composition kind, and
ties back to the constituent edges by triple.

Composition kinds:

* ``transitive`` — every edge in the chain shares the same ``relation``
  predicate (``A R B; B R C => A R C``).
* ``lifting`` — predicates differ but compose into a new asserted relation.

Phase 4 augments adversarial probes with one *chain-break* counter per
composed_relation (drawn from ``counters`` whose ``head`` matches the
chain's head and whose ``tail`` matches the chain's tail).  If no
chain-break counter is provided, a canned probe is emitted so the
adversarial slot is never empty for a chain.

Paradigm-specific gates:
    every_composed_relation_replayed
"""

from __future__ import annotations

from dataclasses import dataclass

from formation.candidate import CounterCandidate, RelationCandidate
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
    source_payload,
    sorted_sources,
    subject_payload,
    substrate_invariants_payload,
    topo_sorted_relations,
)

TEMPLATE_ID: str = "composed_relation"
TEMPLATE_VERSION: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class ComposedRelationTemplate:
    template_id: str = TEMPLATE_ID
    template_version: str = TEMPLATE_VERSION

    def render(
        self,
        validated_set: ValidatedTripleSet,
        spec: SubjectSpec,
        source_bundle_sha: str,
    ) -> dict[str, object]:
        if len(validated_set.relations) < 2:
            raise ValueError(
                "composed_relation: at least two relations required to form a chain"
            )

        concepts = sorted_concepts(validated_set.concepts)
        relations = topo_sorted_relations(validated_set.relations)
        counters = sorted_counters(validated_set.counters)

        chains = _build_chains(relations)
        composed = [_composed_relation_payload(chain) for chain in chains]
        walks = _composed_walks(chains)
        chain_break_probes = _chain_break_probes(chains, counters)

        body: dict[str, object] = {
            "course_id": course_id(spec, self.template_id, self.template_version),
            "paradigm": "chained_relation_composition",
            "template_id": self.template_id,
            "template_version": self.template_version,
            "source_bundle_sha": source_bundle_sha,
            "subject": subject_payload(spec),
            "geometric_dependencies": geometric_dependencies(relations),
            "substrate_invariants": substrate_invariants_payload(),
            "phase_1_ontological_seeding": {
                "concepts": [concept_payload(c) for c in concepts],
            },
            "phase_2_axiomatic_rotor_scaffolding": {
                "relations": [relation_payload(r) for r in relations],
            },
            "phase_3_holonomic_syllabus_walk": {
                "walks": walks,
                "composed_relations": composed,
            },
            "phase_4_epistemic_boundary_hardening": {
                "adversarial_corrections": adversarial_block(counters),
                "chain_break_probes": chain_break_probes,
            },
            "phase_5_ratified_consolidation": phase_5_payload(
                extra_gates=("every_composed_relation_replayed",)
            ),
        }
        return body


# ---------- chain building ----------


def _build_chains(
    relations: list[RelationCandidate],
) -> list[list[RelationCandidate]]:
    """Greedily extract maximal chains.  Only chains of length >= 2 are returned.

    Length-1 stragglers still appear in Phase 2's full relation list (so they
    are not silently dropped), but they do not produce composed_relation
    entries since they form no composition.
    """
    used: set[int] = set()
    chains: list[list[RelationCandidate]] = []
    while len(used) < len(relations):
        seed: int | None = None
        for i in range(len(relations)):
            if i not in used:
                seed = i
                break
        if seed is None:
            break
        chain: list[RelationCandidate] = [relations[seed]]
        used.add(seed)
        while True:
            tail = chain[-1].tail
            extended = False
            for j, r in enumerate(relations):
                if j in used:
                    continue
                if r.head == tail:
                    used.add(j)
                    chain.append(r)
                    extended = True
                    break
            if not extended:
                break
        if len(chain) >= 2:
            chains.append(chain)
    return chains


def _composition_kind(chain: list[RelationCandidate]) -> str:
    preds = {r.relation for r in chain}
    return "transitive" if len(preds) == 1 else "lifting"


def _composed_relation_payload(
    chain: list[RelationCandidate],
) -> dict[str, object]:
    kind = _composition_kind(chain)
    inferred_relation = chain[0].relation if kind == "transitive" else "composes_to"
    return {
        "chain_id": f"chain_{chain[0].head}_to_{chain[-1].tail}",
        "head": chain[0].head,
        "tail": chain[-1].tail,
        "inferred_relation": inferred_relation,
        "composition_kind": kind,
        "verified": "by_walk_only",
        "constituent_edges": [
            {"head": r.head, "relation": r.relation, "tail": r.tail}
            for r in chain
        ],
    }


def _composed_walks(
    chains: list[list[RelationCandidate]],
) -> list[dict[str, object]]:
    walks: list[dict[str, object]] = []
    for i, chain in enumerate(chains):
        walks.append(
            {
                "walk_id": f"walk_{i:04d}",
                "steps": [
                    {"head": r.head, "relation": r.relation, "tail": r.tail}
                    for r in chain
                ],
            }
        )
    return walks


def _chain_break_probes(
    chains: list[list[RelationCandidate]],
    counters: list[CounterCandidate],
) -> list[dict[str, object]]:
    """One probe per chain.  Prefer a matching counter; else emit a canned probe.

    A "matching counter" is one whose head equals the chain head and whose
    tail equals the chain tail — i.e. directly contradicts the inferred
    relation the chain produces.
    """
    probes: list[dict[str, object]] = []
    for i, chain in enumerate(chains):
        head = chain[0].head
        tail = chain[-1].tail
        matched: CounterCandidate | None = None
        for c in counters:
            if c.head == head and c.tail == tail:
                matched = c
                break
        if matched is not None:
            probes.append(
                {
                    "probe_id": f"chain_break_{i:04d}",
                    "head": head,
                    "tail": tail,
                    "counter_relation": matched.relation,
                    "expected_outcome": "rejected",
                    "sources": [
                        source_payload(s) for s in sorted_sources(matched.sources)
                    ],
                }
            )
        else:
            probes.append(
                {
                    "probe_id": f"chain_break_{i:04d}",
                    "head": head,
                    "tail": tail,
                    "counter_relation": "spurious_inference",
                    "expected_outcome": "rejected",
                    "sources": [],
                }
            )
    return probes


__all__ = ["ComposedRelationTemplate", "TEMPLATE_ID", "TEMPLATE_VERSION"]
