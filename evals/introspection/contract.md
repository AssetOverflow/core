# introspection eval lane

## What it measures

Whether CORE can produce a natural-language **account of a prior
turn** that round-trips: a separate run conditioned on that account
predicts the same articulation as the original turn.

Roadmap shape (Phase 3):

  Run 1:  pipeline.run(prompt)       -> Result_A  (surface, trace_hash_A)
  Step:   explain(Result_A.turn_id)  -> account   (natural-language)
  Run 2:  fresh pipeline.run(account) -> Result_B (surface, trace_hash_B)
  Round-trip pass: Result_B.surface == Result_A.surface
                   (or a defensibly equivalent surface)

A passing round-trip demonstrates that CORE's articulation is
*explainable in its own terms* and that the explanation carries
enough state to reconstruct the answer.

## v1 reality: the `explain` interface does not exist

CORE has no `cognition/explain.py` module today.  Per the roadmap
(Phase 3 work items): *"A new `cognition/explain.py` module may be
needed for introspection."*  v1's role is to score the gap
honestly: the runner attempts to import an explain function from
`core.cognition` and falls through with `M1=0` when the import
fails.  This makes the lane runnable today and gives a structural-
zero result by construction until the module lands.

## Sub-metrics

- `M1. explain_api_present`        — the explain function imports
  cleanly from `core.cognition` (or a documented alternative).
- `M2. account_is_nonempty`        — when (1) succeeds, the
  generated account has non-trivial length (≥ 2 tokens).  The
  deterministic canonical form for a DEFINITION probe ("What is
  X?") is naturally 3 tokens; the v1 floor is 2 tokens, distinguishing
  a real sentence from an empty string or a single bare token.
- `M3. round_trip_surface_match`   — Result_B.surface tokens cover
  ≥ 60% of Result_A.surface tokens (case-insensitive,
  punctuation-stripped).
- `M4. round_trip_trace_match`     — Result_B.trace_hash ==
  Result_A.trace_hash (strict deterministic round-trip).

Today's expected result: M1 = 0; all downstream metrics = 0.

A case passes when M1 AND M2 AND M3 hold.  M4 is reported as a
stricter signal — likely to fail even after M3 starts succeeding
because the input texts (original prompt vs. account) differ
verbatim and trace_hash is computed over input_text.

## Overall pass thresholds (v1)

- `explain_api_present_rate` (M1) ≥ 0.95  — trivial once the
  module exists
- `account_nonempty_rate` (M2) ≥ 0.95
- `round_trip_surface_match_rate` (M3) ≥ 0.50

v1's expected score: all zero.  v1 is the lane that explicitly tests
whether the explain primitive exists and produces a usable
account.  Until it does, this is structural-zero work.

## Why a placeholder-runnable v1

The Phase 3 exit criteria state: "v1 results with honest scores
(which may be failing — that's acceptable for v1).  Each failure
has either a closed engineering gap or a documented architectural
deferral."  A lane that cannot run at all is worse than a lane that
runs and reports zero; the latter forms a real regression trigger
for the day the engineering lands.
