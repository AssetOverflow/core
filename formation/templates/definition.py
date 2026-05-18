"""The ``definition`` template — first and simplest Course YAML template.

A Course rendered with this template treats every relation as a definitional
edge in a concept ontology.  It emits the full five-phase body specified in
``docs/formation_pipeline_plan.md`` (§3 Phase 3).

Determinism rules enforced here:

* Concepts are sorted by ``(canonical_term, first_source_sha)`` lex.
* Relations are topologically sorted (Kahn's algorithm); ties broken by the
  ``(head, relation, tail)`` triple lex order.
* Walks are auto-generated from the topo-sorted relation DAG, one walk per
  maximal chain.
* All numerics are strings — floats are forbidden per
  ``formation.hashing._reject_floats`` and ``CLAUDE.md``.
* Adversarial probes include canned identity-override probes drawn from
  ``CLAUDE.md`` "Teaching Safety", plus one probe per ``CounterCandidate``.
"""

from __future__ import annotations

from dataclasses import dataclass

from formation.course import SubjectSpec, ValidatedTripleSet
from formation.templates._common import (
    MAX_VERSOR_CONDITION,
    adversarial_block,
    concept_payload,
    course_id,
    geometric_dependencies,
    maximal_chain_walks,
    phase_5_payload,
    relation_payload,
    sorted_concepts,
    sorted_counters,
    subject_payload,
    substrate_invariants_payload,
    topo_sorted_relations,
)

TEMPLATE_ID: str = "definition"
TEMPLATE_VERSION: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class DefinitionTemplate:
    """Template implementation.  Stateless; cheap to instantiate."""

    template_id: str = TEMPLATE_ID
    template_version: str = TEMPLATE_VERSION

    def render(
        self,
        validated_set: ValidatedTripleSet,
        spec: SubjectSpec,
        source_bundle_sha: str,
    ) -> dict[str, object]:
        concepts = sorted_concepts(validated_set.concepts)
        relations = topo_sorted_relations(validated_set.relations)
        counters = sorted_counters(validated_set.counters)

        body: dict[str, object] = {
            "course_id": course_id(spec, self.template_id, self.template_version),
            "paradigm": "five_phase_versor_formation",
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
                "walks": maximal_chain_walks(relations),
            },
            "phase_4_epistemic_boundary_hardening": {
                "adversarial_corrections": adversarial_block(counters),
            },
            "phase_5_ratified_consolidation": phase_5_payload(),
        }
        return body


__all__ = [
    "DefinitionTemplate",
    "MAX_VERSOR_CONDITION",
    "TEMPLATE_ID",
    "TEMPLATE_VERSION",
]
