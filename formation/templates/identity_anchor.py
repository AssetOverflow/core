"""The ``identity_anchor`` template — Layer 1, identity seeding.

The course *is* the identity probe set.  ``concepts`` are interpreted as
identity axes whose ``definition`` field carries the axis's behavioral
commitment (e.g. ``"Precision-first: weight accuracy over coverage"``).
``counters`` are interpreted as override attempts the system must refuse.
``relations`` are interpreted as compatibility constraints between axes
(``axis_a compatible_with axis_b``); these are optional.

This template is run first in any new domain so subsequent courses have
an anchored identity to ratify against.  It hard-requires at least one
counter — an identity course with no override attempts is not an
identity-anchor course, it is a definition course, and the caller is
told to switch templates.

Axis priority is derived from ``ordering_hints``: a hint
``axis_a -> axis_b`` means ``axis_a`` ranks above ``axis_b``.  Axes
unmentioned by any hint get appended in lex order after the ranked ones,
so output is fully deterministic even when hints under-specify.

Paradigm-specific gates:
    every_axis_seeded_at_least_once
    every_override_rejected
"""

from __future__ import annotations

from dataclasses import dataclass

from formation.candidate import ConceptCandidate, OrderingHint
from formation.course import SubjectSpec, ValidatedTripleSet
from formation.templates._common import (
    IDENTITY_OVERRIDE_PROBES,
    course_id,
    first_source_sha,
    phase_5_payload,
    relation_payload,
    sorted_counters,
    source_payload,
    sorted_sources,
    subject_payload,
    substrate_invariants_payload,
    topo_sorted_relations,
)

TEMPLATE_ID: str = "identity_anchor"
TEMPLATE_VERSION: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class IdentityAnchorTemplate:
    template_id: str = TEMPLATE_ID
    template_version: str = TEMPLATE_VERSION

    def render(
        self,
        validated_set: ValidatedTripleSet,
        spec: SubjectSpec,
        source_bundle_sha: str,
    ) -> dict[str, object]:
        if not validated_set.concepts:
            raise ValueError(
                "identity_anchor: at least one axis (concept) required"
            )
        if not validated_set.counters:
            raise ValueError(
                "identity_anchor: at least one override-attempt counter required"
            )

        axes = _ranked_axes(
            validated_set.concepts, validated_set.ordering_hints,
        )
        compat_relations = topo_sorted_relations(validated_set.relations)
        counters = sorted_counters(validated_set.counters)

        refusal_walks = _refusal_walks(counters)
        adversarial = _identity_adversarial(counters)

        body: dict[str, object] = {
            "course_id": course_id(spec, self.template_id, self.template_version),
            "paradigm": "identity_axis_seeding",
            "template_id": self.template_id,
            "template_version": self.template_version,
            "source_bundle_sha": source_bundle_sha,
            "subject": subject_payload(spec),
            "substrate_invariants": substrate_invariants_payload(),
            "phase_1_axis_declaration": {
                "axes": axes,
            },
            "phase_2_immutability_relations": {
                "relations": [relation_payload(r) for r in compat_relations],
            },
            "phase_3_refusal_walks": {
                "walks": refusal_walks,
            },
            "phase_4_epistemic_boundary_hardening": {
                "adversarial_corrections": adversarial,
            },
            "phase_5_ratified_consolidation": phase_5_payload(
                extra_gates=(
                    "every_axis_seeded_at_least_once",
                    "every_override_rejected",
                ),
            ),
        }
        return body


def _ranked_axes(
    concepts: tuple[ConceptCandidate, ...],
    ordering_hints: tuple[OrderingHint, ...],
) -> list[dict[str, object]]:
    """Rank axes by ordering_hints, then by canonical_term lex for tail."""
    names = [c.canonical_term for c in concepts]
    name_set = set(names)

    indegree: dict[str, int] = {n: 0 for n in name_set}
    out_edges: dict[str, list[str]] = {n: [] for n in name_set}
    for h in sorted(ordering_hints, key=lambda h: (h.before, h.after)):
        if h.before in name_set and h.after in name_set:
            indegree[h.after] += 1
            out_edges[h.before].append(h.after)

    ready: list[str] = sorted(n for n, d in indegree.items() if d == 0)
    ordered: list[str] = []
    while ready:
        ready.sort()
        n = ready.pop(0)
        ordered.append(n)
        for nxt in sorted(out_edges[n]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
    if len(ordered) < len(name_set):
        ordered.extend(sorted(name_set - set(ordered)))

    by_name: dict[str, ConceptCandidate] = {c.canonical_term: c for c in concepts}
    payload: list[dict[str, object]] = []
    for rank, name in enumerate(ordered):
        c = by_name[name]
        payload.append(
            {
                "axis_id": f"axis_{rank:04d}",
                "priority": str(rank),
                "canonical_term": c.canonical_term,
                "commitment": c.definition,
                "sources": [source_payload(s) for s in sorted_sources(c.sources)],
            }
        )
    # Determinism cross-check: axes ordered by (priority asc, canonical_term asc).
    _ = first_source_sha  # silence unused-import on lean runs
    return payload


def _refusal_walks(counters: list) -> list[dict[str, object]]:
    walks: list[dict[str, object]] = []
    for i, c in enumerate(counters):
        walks.append(
            {
                "walk_id": f"walk_{i:04d}",
                "kind": "refusal",
                "steps": [
                    {
                        "head": c.head,
                        "relation": c.relation,
                        "tail": c.tail,
                        "expected_terminal_state": "rejected",
                    }
                ],
            }
        )
    return walks


def _identity_adversarial(counters: list) -> list[dict[str, object]]:
    """All counters become numbered override probes, then canned probes."""
    probes: list[dict[str, object]] = []
    for i, c in enumerate(counters):
        probes.append(
            {
                "probe_id": f"override_{i:04d}",
                "head": c.head,
                "relation": c.relation,
                "tail": c.tail,
                "expected_outcome": "rejected",
                "sources": [source_payload(s) for s in sorted_sources(c.sources)],
            }
        )
    for canned in IDENTITY_OVERRIDE_PROBES:
        probes.append(dict(canned))
    return probes


__all__ = ["IdentityAnchorTemplate", "TEMPLATE_ID", "TEMPLATE_VERSION"]
