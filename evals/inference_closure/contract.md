# inference-closure eval lane

## What it measures

CORE's ability to derive **entailments that were not directly asserted**
from a chain of premises that were.  This picks up where the
`symbolic-logic` lane explicitly deferred: that lane verified premise
storage, replay determinism, and recall; this lane verifies the
inferential closure step.

Test shape:

  Premise 1: A R B   (e.g. "Actually fire causes smoke.")
  Premise 2: B R C   (e.g. "Actually smoke causes irritation.")
  Probe:     "What does A R?"  ("What does fire cause?")
  Pass:      response surface or vault recall references **C**
             (the derived entailment, never directly asserted).

The relation `R` is drawn from the existing
`en_core_cognition_v1` lexicon's relation predicates:
`is`, `causes`, `precedes`, `follows`, `grounds`, `belongs_to`,
`reveals`, `means`, `contrasts_with`.

## Why it matters

The roadmap (`docs/capability_roadmap.md` Phase 3) frames this lane as
one of the load-bearing tests of whether CORE actually *thinks*
rather than retrieves and articulates.  A successful v1 result would
mean the pipeline carries derivable-but-not-asserted recall paths
through `field/propagate.py` and/or `generate/graph_planner.py`.

Per the roadmap's explicit guidance:

> v1 results with honest scores (which may be failing — that's
> acceptable for v1). Each failure has either a closed engineering
> gap or a documented architectural deferral.

If v1 fails, the lane's signal is "where exactly does CORE stop short
of inference closure today?" — captured in `gaps.md`.

## Patterns covered (v1)

| Pattern | Premise template | Probe template | Expected entailment |
|---|---|---|---|
| `transitive_causes` | A causes B; B causes C | What does A cause? | C |
| `transitive_precedes` | A precedes B; B precedes C | What does A precede? | C |
| `transitive_grounds` | A grounds B; B grounds C | What grounds A? (reverse) | C |
| `transitive_is` | A is B; B is C | What is A? | C |
| `transitive_belongs_to` | A belongs_to B; B belongs_to C | Where does A belong? | C |

Each pattern stays within the cognition lexicon's relation vocabulary
so the probe is grounded by the same vault content that anchors the
premises.

## Sub-metrics

Per case, the runner reports four signals:

- `M1. derived_token_in_surface` — the expected entailment token
  appears (case-insensitively, token-bounded) in the probe response's
  `surface` or `articulation_surface`.
- `M2. derived_token_in_vault` — the expected entailment token is
  among the recalled vault entries produced by the probe.
- `M3. premises_stored` — every premise turn produced a
  `pack_mutation_proposal` (regression gate for the symbolic-logic
  foundation).
- `M4. replay_determinism` — two independent runs of the (premises,
  probe) sequence produce identical `trace_hash`.

A case passes only when M1 or M2 hold (true closure evidence) AND
M3 AND M4 hold (foundation intact).  M3 + M4 alone is the
symbolic-logic guarantee — not an inference-closure pass.

## Overall pass thresholds (v1)

- `derived_recall_rate` (M1 ∨ M2) ≥ 0.50
- `replay_determinism` (M4) ≥ 0.95
- `premises_stored_rate` (M3) ≥ 0.95

If CORE produces no inference operator at v1 — which is the working
hypothesis going in — `derived_recall_rate` will hover near zero and
the threshold above will not be met.  That outcome is a load-bearing
finding, not a regression; it is recorded as Phase 3's first
honest-failure lane and turned into an engineering plan in
`gaps.md`.

## Anti-overfitting

- Public split uses one entity set; holdouts split uses a disjoint
  entity set drawn from a different region of the cognition lexicon.
- Relations are drawn from the lexicon, not invented for the lane.
- No case is included whose answer is also a direct surface form of
  any premise.

## Calibration

Each case has an `entailment_chain_length` field (2 for the basic
two-hop form).  Longer chains may be added in v2 once v1 baselines
the two-hop case.
