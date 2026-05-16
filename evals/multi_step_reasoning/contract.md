# multi-step-reasoning eval lane

## What it measures

Whether the pipeline produces *and consumes* intermediate
proposition-graph states for problems whose solution requires three
or more inferential hops.

This sharpens inference-closure: inference-closure scored two-hop
transitive entailments; this lane scores 3-, 4-, and 5-hop chains
and additionally checks that intermediate states are observable in
the proposition graph after the chain is taught.

## Why it matters

Single-hop and two-hop closure can in principle be implemented by
local pattern composition.  Three-or-more hops require the pipeline
to build *and traverse* an inference path that does not exist
verbatim in any single premise.  This is closer to the roadmap's
question: does CORE *think*, or does it pattern-match longer
templates.

## Patterns covered (v1)

| Pattern | Shape | Hops |
|---|---|---|
| `chain_3` | A is B; B is C; C is D | 3 |
| `chain_4` | A is B; B is C; C is D; D is E | 4 |
| `chain_5` | A is B; B is C; C is D; D is E; E is F | 5 |
| `mixed_relation_3` | A is B; B grounds C; C precedes D | 3 |
| `mixed_relation_4` | A causes B; B grounds C; C is D; D precedes E | 4 |

## Sub-metrics

- `M1. chain_endpoint_in_surface` — the final-hop entity appears
  (case-insensitive, token-bounded) in `surface` or `walk_surface`.
- `M2. intermediate_in_graph`     — at least one intermediate hop is
  observable in the probe response's articulation_surface or
  walk_surface (proxy for graph state inspection).
- `M3. premises_stored`            — every taught hop emits a proposal.
- `M4. replay_determinism`         — two fresh runs match by trace_hash.

A case passes when M1 AND M3 AND M4 hold.  M2 is reported as
diagnostic signal — partial credit when chain_endpoint is missed.

## Overall pass thresholds (v1)

- `chain_endpoint_recall_rate` (M1) ≥ 0.50
- `premises_stored_rate` ≥ 0.95
- `replay_determinism` ≥ 0.95

## Relationship to inference-closure v1

Same architectural gaps apply: no transitive composition in
`graph_planner.py`, no path-recall in `field/propagate.py`.  This
lane scores how the gap scales with chain length.  v1's likely
result: uniform M1 failure across all chain lengths.
