# Implementation Work Packages

## WP-G5-001 — TargetBinding graph primitive

Owner:
TBD

Files likely touched:

- `generate/math_candidate_graph.py`
- `generate/math_binding_graph.py`
- `core/cognition/...`

Deliverables:

- typed TargetBinding structure;
- deterministic serialization;
- provenance edges;
- replay-safe hashing.

Acceptance:

- no replay drift;
- graph equality deterministic;
- no regression in existing B3 lane.

---

## WP-G5-002 — Aggregate question parser

Examples:

- how many total
- how many altogether
- combined total
- total amount

Acceptance:

- all curated cases deterministic;
- ambiguity triggers typed refusal;
- no greedy binding.

---

## WP-G5-003 — Derived-state traversal

Goal:

Allow question targets to bind against composed graph outputs.

Acceptance:

- verifier replay succeeds;
- composed provenance visible in trace;
- mixed-unit binding refuses.

---

## WP-G3-001 — Numeric literal normalization

Examples:

- `$40`
- `3,000`
- `12.5`
- `50%`

Acceptance:

- normalized canonical representation;
- provenance preserved;
- malformed literals refuse.

---

## WP-G6-001 — Verb ontology

Goal:

Map ordinary school-math verbs into typed operation semantics.

Acceptance:

- explicit operation class;
- polarity-safe transfer semantics;
- ambiguity refusal.

---

## WP-G7-001 — Discourse entity registry

Goal:

Track entities across sentences safely.

Acceptance:

- pronoun scope deterministic;
- alias collisions refuse;
- sentence-order replay stable.

---

## Global invariant

Every work package must preserve:

```text
admitted_wrong == 0
```
