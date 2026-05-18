"""The ``falsification`` template — counter-example-driven mastery.

The unit of mastery is the rejected claim plus the coherent alternative.
Where ``definition`` makes ``relations`` load-bearing and ``counters``
adversarial, this template reverses the polarity: ``counters`` are the
primary content of Phase 2 and each counter must be paired with a
``coherent_alternative`` drawn from ``relations`` that share the same
``head``.

Pairing rule:
* A counter is *paired* if at least one relation has ``head == counter.head``.
  The lexically-smallest such relation by ``(relation, tail)`` is its
  coherent alternative.
* A counter with no matching relation is recorded under
  ``unmatched_counters`` in Phase 2.  This is allowed (the template still
  succeeds), but the ratifier should treat unmatched counters as a flag
  for follow-up curation.

Phase 4 emits a *false-coherent* probe per pair: a near-miss that looks
like the alternative but is itself a counter (the same ``head`` with a
different ``tail`` — drawn from the remaining counters if available, else
a canned generic probe).

Paradigm-specific gates:
    counter_rejection_rate_eq_1
    alternative_acceptance_rate_eq_1
"""

from __future__ import annotations

from dataclasses import dataclass

from formation.candidate import CounterCandidate, RelationCandidate
from formation.course import SubjectSpec, ValidatedTripleSet
from formation.templates._common import (
    IDENTITY_OVERRIDE_PROBES,
    concept_payload,
    counter_payload,
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

TEMPLATE_ID: str = "falsification"
TEMPLATE_VERSION: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class FalsificationTemplate:
    template_id: str = TEMPLATE_ID
    template_version: str = TEMPLATE_VERSION

    def render(
        self,
        validated_set: ValidatedTripleSet,
        spec: SubjectSpec,
        source_bundle_sha: str,
    ) -> dict[str, object]:
        if not validated_set.counters:
            raise ValueError(
                "falsification: at least one counter required"
            )

        concepts = sorted_concepts(validated_set.concepts)
        relations = topo_sorted_relations(validated_set.relations)
        counters = sorted_counters(validated_set.counters)

        pairs, unmatched = _build_polarity_pairs(counters, relations)
        polarity_walks = _polarity_walks(pairs)
        adversarial = _falsification_adversarial(pairs, counters)

        body: dict[str, object] = {
            "course_id": course_id(spec, self.template_id, self.template_version),
            "paradigm": "counter_example_polarity",
            "template_id": self.template_id,
            "template_version": self.template_version,
            "source_bundle_sha": source_bundle_sha,
            "subject": subject_payload(spec),
            "geometric_dependencies": geometric_dependencies(relations),
            "substrate_invariants": substrate_invariants_payload(),
            "phase_1_ontological_seeding": {
                "concepts": [concept_payload(c) for c in concepts],
            },
            "phase_2_falsification_corpus": {
                "polarity_pairs": pairs,
                "unmatched_counters": [counter_payload(c) for c in unmatched],
                "supporting_relations": [relation_payload(r) for r in relations],
            },
            "phase_3_polarity_walks": {
                "walks": polarity_walks,
            },
            "phase_4_epistemic_boundary_hardening": {
                "adversarial_corrections": adversarial,
            },
            "phase_5_ratified_consolidation": phase_5_payload(
                extra_gates=(
                    "counter_rejection_rate_eq_1",
                    "alternative_acceptance_rate_eq_1",
                ),
            ),
        }
        return body


def _build_polarity_pairs(
    counters: list[CounterCandidate],
    relations: list[RelationCandidate],
) -> tuple[list[dict[str, object]], list[CounterCandidate]]:
    """Match each counter to the lex-smallest relation sharing its head."""
    by_head: dict[str, list[RelationCandidate]] = {}
    for r in relations:
        by_head.setdefault(r.head, []).append(r)
    for head in by_head:
        by_head[head].sort(key=lambda r: (r.relation, r.tail))

    pairs: list[dict[str, object]] = []
    unmatched: list[CounterCandidate] = []
    for i, c in enumerate(counters):
        candidates = by_head.get(c.head, [])
        if not candidates:
            unmatched.append(c)
            continue
        alt = candidates[0]
        pairs.append(
            {
                "pair_id": f"pair_{i:04d}",
                "rejected_claim": {
                    "head": c.head,
                    "relation": c.relation,
                    "tail": c.tail,
                    "sources": [
                        source_payload(s) for s in sorted_sources(c.sources)
                    ],
                },
                "coherent_alternative": {
                    "head": alt.head,
                    "relation": alt.relation,
                    "tail": alt.tail,
                    "sources": [
                        source_payload(s) for s in sorted_sources(alt.sources)
                    ],
                },
            }
        )
    return pairs, unmatched


def _polarity_walks(pairs: list[dict[str, object]]) -> list[dict[str, object]]:
    walks: list[dict[str, object]] = []
    for i, pair in enumerate(pairs):
        rejected = pair["rejected_claim"]
        alt = pair["coherent_alternative"]
        assert isinstance(rejected, dict) and isinstance(alt, dict)
        walks.append(
            {
                "walk_id": f"walk_{i:04d}",
                "kind": "polarity_flip",
                "steps": [
                    {
                        "head": str(rejected["head"]),
                        "relation": str(rejected["relation"]),
                        "tail": str(rejected["tail"]),
                        "polarity": "reject",
                    },
                    {
                        "head": str(alt["head"]),
                        "relation": str(alt["relation"]),
                        "tail": str(alt["tail"]),
                        "polarity": "accept",
                    },
                ],
            }
        )
    return walks


def _falsification_adversarial(
    pairs: list[dict[str, object]],
    counters: list[CounterCandidate],
) -> list[dict[str, object]]:
    """For each pair, emit one false-coherent probe.

    A false-coherent probe shares the pair's ``head`` but a different ``tail``,
    sourced from another counter when available.  When no other counter
    matches, emit a canned ``false_coherent_generic`` probe.  Identity
    override probes always close the list.
    """
    probes: list[dict[str, object]] = []
    used_counters: set[tuple[str, str, str]] = set()
    for pair in pairs:
        rc = pair["rejected_claim"]
        assert isinstance(rc, dict)
        pair_id = str(pair["pair_id"])
        used_counters.add((str(rc["head"]), str(rc["relation"]), str(rc["tail"])))

    for pair in pairs:
        rc = pair["rejected_claim"]
        assert isinstance(rc, dict)
        head = str(rc["head"])
        pair_id = str(pair["pair_id"])
        false_coherent: CounterCandidate | None = None
        for c in counters:
            triple = (c.head, c.relation, c.tail)
            if triple in used_counters:
                continue
            if c.head == head:
                false_coherent = c
                used_counters.add(triple)
                break
        if false_coherent is not None:
            probes.append(
                {
                    "probe_id": f"false_coherent_{pair_id}",
                    "head": false_coherent.head,
                    "relation": false_coherent.relation,
                    "tail": false_coherent.tail,
                    "expected_outcome": "rejected",
                    "sources": [
                        source_payload(s)
                        for s in sorted_sources(false_coherent.sources)
                    ],
                }
            )
        else:
            probes.append(
                {
                    "probe_id": f"false_coherent_{pair_id}",
                    "head": head,
                    "relation": "near_miss",
                    "tail": "spurious_alternative",
                    "expected_outcome": "rejected",
                    "sources": [],
                }
            )

    for canned in IDENTITY_OVERRIDE_PROBES:
        probes.append(dict(canned))
    return probes


__all__ = ["FalsificationTemplate", "TEMPLATE_ID", "TEMPLATE_VERSION"]
