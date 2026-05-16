# multi-step-reasoning lane — architectural findings (v1)

## v1 result

| Split | n | endpoint_recall | intermediate_visible | stored | replay |
|---|---|---|---|---|---|
| public/v1 | 15 | **0.0** | 0.0 | 1.0 | 1.0 |
| holdouts/v1 | 10 | **0.0** | 0.0 | 1.0 | 1.0 |

Uniform zero on the inference signal across 3-hop, 4-hop, and
5-hop chains; foundation intact.

## Relationship to inference-closure v1

This lane extends inference-closure (which was 2-hop) to longer
chains.  v1's result is the same architectural finding scaled with
chain length: no transitive composition exists at any depth, so the
failure mode is depth-independent.

Concretely: a 3-hop chain `wisdom is judgment; judgment is decision;
decision is action` plus probe `What is wisdom?` returns the
template `wisdom is defined as ...`.  The vault stores all three
premises; the realizer emits a definition stub.  The intermediate
hops are not visible in the surface, the endpoint never appears.

## Architectural gap (shared with inference-closure)

Same Gap 1 (no transitive composition in `graph_planner.py`) and
Gap 2 (no path-recall in `field/propagate.py`).  The depth-scaling
signal from this lane should be revisited after Gap 1 closes: a
correct fix should pass 3-hop, may degrade gracefully on 4- and
5-hop, and should clearly indicate where chain-traversal bounds
become a performance versus a correctness issue.

## Phase 3 exit posture

This lane satisfies the v1 honest-failure expectation.  When Gap 1
engineering lands, this lane should be re-run as the primary scaling
diagnostic.
