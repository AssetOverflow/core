# compositionality lane — architectural findings (v1)

## Resolution (partial) — 2026-05-17 lane re-run

After the typed operators + pipeline wiring landed:

| Split | n | compositional_recall_rate | premises_stored | replay | overall |
|---|---|---|---|---|---|
| public/v1   | 16 | **0.6875** (was 0.0625) | 1.0 | 1.0 | ✓ pass |
| holdouts/v1 | 10 | (re-score)              | 1.0 | 1.0 | (re-score) |

`overall_pass = True` because the structural foundations gate, but
the recall rate is not yet 1.0.  The residual ~30% miss is on
patterns that require relation-aware composition
(`novel_pair_under_seen_relation`, `novel_relation_on_seen_pair`)
where a single `transitive_walk` or `multi_relation_walk` cannot
synthesise the derived edge.  v2 follow-on: a `compose_relations`
operator that materialises new edges from intersecting paths,
registered in `generate/operators.py` alongside the existing walks.

Historic finding preserved below.

## Original v1 result (now superseded)

| Split | n | compositional_recall_rate | premises_stored | replay | no_leakage |
|---|---|---|---|---|---|
| public/v1 | 16 | **0.0625** (1/16) | 1.0 | 1.0 | 0.4375 |
| holdouts/v1 | 10 | **0.0** | 1.0 | 1.0 | 0.4 |

The single public hit is consistent with a realizer-template token
coincidence rather than real composition (no second hit on holdouts;
no pattern in the hit; not reproducible across patterns).

## Foundation intact

Every teaching turn fires a `PackMutationProposal`
(`premises_stored_rate = 1.0`); every (premises, probe) sequence is
trace-hash-deterministic (`replay_determinism = 1.0`).  The
Phase 2 storage + replay guarantees survive at this depth.

## What v1 reveals

- **No composition operator.**  Across three patterns
  (`composed_predicate`, `novel_pair_under_seen_relation`,
  `novel_relation_on_seen_pair`), CORE produces no surface evidence
  of composing seen relation patterns into novel (relation, entity)
  combinations.
- **Same root cause as inference-closure.**  The realizer template
  picks one node and emits a definition stub; no node-pair
  composition step runs that would combine premises into a novel
  surface.

## Authoring finding — leakage rate

`no_leakage_rate` is 0.4375 / 0.4 — i.e. several
`novel_pair_under_seen_relation` cases have a premise whose tokens
include both a probe entity and an expected target.  This is
**intentional for that pattern** (the test is "given the model has
seen `R(A,B)` and `R(C,D)`, can it answer `R(A,D)` or `R(C,B)`?" —
both answers were taught as premise endpoints, just not together).
The strict author-time leakage check fires by design here.  v2 of
this contract should replace the strict check with a pattern-aware
check: leakage means the specific `(probe_entity, expected_target)`
*pair* was taught in a single premise, not that the target appears
anywhere in premises.

This is filed as a contract refinement for v2; it does not change
v1's substantive finding.

## Architectural gap (same family as inference-closure)

Composition requires the proposition-graph planner to walk multiple
nodes and synthesize a derived articulation.  `plan_articulation()`
in `generate/graph_planner.py` is single-node.  Closing the
inference-closure Gap 1 — adding a transitive composition walk —
also closes the bulk of this lane's failure surface.

## Future direction (recorded here so it's not forgotten)

Metaphor and simile are structurally **compositionality with
selective property transfer**: "the heart is a pump" is the same
graph-traversal shape as the compositionality probes above, with a
filter that says *which* relations transfer across the analogy.
Building first-class metaphor support is correctly downstream of
closing this lane's literal-composition gap.  When that lands, a
`metaphor-comprehension` lane becomes a natural Phase 3 v2 candidate.

## Status

v1 stands as honest-failure baseline.  The lane is permanent
regression evidence; future engineering work on `graph_planner.py`
that closes inference-closure Gap 1 should be re-scored here.
