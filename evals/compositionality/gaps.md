# compositionality lane — architectural findings (v1)

## Resolution (full) — 2026-05-16 compose_relations lands

After the typed operators + pipeline wiring + `compose_relations`:

| Split | n | compositional_recall_rate | premises_stored | replay | overall |
|---|---|---|---|---|---|
| public/v1   | 16 | **1.0** (was 0.0625 → 0.6875 → 1.0) | 1.0 | 1.0 | ✓ pass |

All three patterns now hit:

  - `composed_predicate` (7/7) — via `multi_relation_walk` (chain
    A → B → C across mixed relations).
  - `novel_relation_on_seen_pair` (4/4) — via `multi_relation_walk`
    matching morphological verb-form probes against the chain
    endpoint noun.
  - `novel_pair_under_seen_relation` (5/5) — via the **new
    `compose_relations` operator** + the `FRAME_TRANSFER` intent
    shape ("What does X R in Y?").  The operator reports both
    `R(X, ?)` and `R(Y, ?)` tails so the realizer surfaces the
    cross-instance compositional answer.

### How it works

  1. `_FRAME_TRANSFER_RE` (`generate/intent.py`) matches the probe
     shape "What does X R [to] in Y?" — tried before the generic
     `TRANSITIVE_QUERY` regex so the trailing "in Y" is not
     silently truncated.  An optional "to" between R and "in" is
     normalized to `belongs_to`.
  2. `compose_relations(triples, head, frame, relation)`
     (`generate/operators.py`) is a pure function that looks up
     both `R(head, ?)` and `R(frame, ?)` from the typed teaching
     store and returns a `FrameComposeResult` with both tails (or
     None when an edge is absent).
  3. `CognitiveTurnPipeline._maybe_compose_relations` fires only on
     `FRAME_TRANSFER` intents, `_fold_compose_into_surface` names
     both endpoints in the surface deterministically, and
     `_serialize_compose` folds the result into `operator_invocation`
     so `trace_hash` remains bit-identical across replay.

Historic findings preserved below.

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
