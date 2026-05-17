# forward-semantic-control eval lane

## What it measures

Whether the proposition graph **constrains** field propagation (the
graph acts as an admissibility region on the manifold, per ADR-0022)
or merely *decorates* it after the fact.

The lane is the load-bearing acceptance gate (1) for ADR-0022's
Draft → Proposed transition.

## Why it matters

CORE's structural claim is "geometric cognition, not sequence
sampling."  Today the field walk and the proposition graph are
causally independent: the graph does not bound the field, the field
does not prove the graph.  This lane forces a case design where the
expected surface depends on a relation chain that is only walkable
under graph constraint — i.e. the unconstrained walk happens to
answer some negative-control prompts correctly by coincidence; the
constrained walk answers the chain-dependent prompts correctly *by
causality*.

Without this lane, "the graph constrains the field" is an assertion
in the ADR, not a property of the implementation.

## Protocol

Each case follows the same shape:

1. **Setup** — prime the session with one or more teaching turns so
   the vault carries a known triple chain (e.g.
   `A→B`, `B→C`, `C→D`).
2. **Probe** — issue a query whose expected surface names the
   chain endpoint (`D`) by walking from `A` under the typed
   relation.
3. **Score** — inspect the surface for the expected token.  The
   unconstrained baseline (`expect_baseline_pass=false`) must
   *fail* to surface the endpoint by coincidence; the constrained
   walk must succeed.

## Pass criteria

| Metric | Definition | v1 threshold | Initial |
|--------|-----------|--------------|---------|
| `constrained_pass_rate` | Fraction of chain-dependent probes whose surface names the expected endpoint | 0.80 | **TBD** |
| `coincidence_rate` | Fraction of negative-control probes that the unconstrained baseline happens to answer correctly (must be **low** for the lane to be measuring causality, not accuracy) | < 0.20 | **TBD** |
| `causality_gap` | `constrained_pass_rate − unconstrained_pass_rate` on chain-dependent probes — must be positive for the lane to evidence "graph caused the answer" | > 0.50 | **TBD** |
| `overall_pass` | `constrained_pass_rate ≥ 0.80 AND causality_gap > 0.50` | true | **TBD** |
| `region_only_constrained_rate` | Same-path ablation: fraction of chain-dependent probes whose `generate(..., region=R)` surfaces the endpoint, evaluated against the *same* runtime/vocab/field/persona/prompt that produced `region_only_unconstrained_*` (ADR-0023 §1) | 0.80 | **TBD** |
| `region_only_unconstrained_rate` | Same-path ablation baseline: `generate(..., region=None)` on the same state | low | **TBD** |
| `region_only_gap` | `region_only_constrained_rate − region_only_unconstrained_rate` — the cleanest single-variable evidence that the admissibility region itself is the cause | > 0.50 | **TBD** |
| `ratified_rate` / `demoted_rate` / `passthrough_rate` | Fraction of pipeline-leg turns whose intent was ratified / demoted / passthrough (ADR-0023 §3) | n/a | **TBD** |
| `passthrough_on_scored` | Whether *any* chain-dependent (scored) case had `PASSTHROUGH` — that means the regex seed bypassed the field gate on a load-bearing case | **false** | **TBD** |

## Anti-patterns (cases must avoid)

- A case that the unconstrained walk passes by template coincidence
  is not evidence of forward semantic control; it is evidence of a
  good rhetorical scaffold.  Such cases belong in the
  `articulation_of_status` or `compositionality` lanes.
- A case scored on surface fluency rather than chain endpoint
  presence inherits the same gap.
- A case that requires probabilistic ranking to disambiguate
  candidates is out of scope for this ADR (no softmax, no
  temperature — ADR-0022 §"What this ADR is NOT").

## Cases (dev)

- **chain_three_hop** — teach `A causes B`, `B causes C`,
  `C causes D`.  Probe `What does A cause?`.  Constrained walk
  must surface `D` (chain endpoint); unconstrained walk surfaces
  only `B` (nearest neighbour).
- **negative_control_no_chain** — teach `A causes B`,
  `X causes Y`.  Probe `What does A cause?`.  Both paths
  should surface `B`; chain is length-1, the constrained-walk
  surface should match.  This case must *not* be the load-bearing
  case — if it is the only one passing, the lane measures
  nothing.
- **frame_constraint_blocks_wrong_relation** — teach
  `A causes B` and `A means C`.  Probe `What does A cause?`.
  Constrained walk surfaces `B`; an unconstrained walk that
  drifts to `C` via geometric proximity fails the case.

## Status — Draft

Lane is **scaffolded but not yet wired** to a constrained
implementation.  Dev cases below are drafted; the runner returns
`overall_pass=false` until the constrained propagation operator
lands per ADR-0022 implementation step 4.

This is intentional — `evals/CLAIMS.md` Tier 4 commits to writing
the test before earning the claim.

## Runner

`runner.py` in this directory.
