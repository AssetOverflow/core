# R3.1 — R3 wired into the contemplation router (ledger)

**As of:** R3.1, on `main @ a320c69a` + `feat/r3-1-router`.

R3.1 completes the growth loop for the single-rate organ: R3 is now a first-class organ in the
multi-organ router and contemplation pass, so a rate problem the reader can't yet handle is
classified and (for genuine rate gaps) emits a proposal-only artifact — surfaced by the existing
read-only `idle_tick` review. The chain is now whole:

```text
R1 / R2 / R3 organs → route_setup → contemplation pass → proposal-only artifacts → proposal review → idle_tick visibility
```

## What changed
- `core/comprehension_attempt/model.py` — `Organ` gains `r3_rate`.
- `core/comprehension_attempt/classify.py` — `classify_r3` normalizes the rate reader's output
  into a `ComprehensionAttempt` (deterministic rate signature).
- `core/comprehension_attempt/router.py` — `route_setup` now tries R1, R2, **and R3**, with the
  same exactly-one-`setup_correct` rule (zero → refuse, ≥2 → ambiguous).
- `generate/contemplation/pass_manager.py` — a routed `r3_rate` setup is solved + verified
  (`solve_rate` + the reused answer-choice verifier); `unsupported_temporal_state` is dropped from
  the unsupported-family set so `temporal_state` is a generic `REFUSED_KNOWN_BOUNDARY`.

## Terminal matrix (verified)

| R3 case | Terminal | Proposal? |
|---|---|---|
| supported single-rate (6 solved) | `SOLVED_VERIFIED` | — |
| `rate_unit_mismatch` (minutes vs /hour) | `PROPOSAL_EMITTED` (`unsupported_rate_duration`) | ✅ |
| `combined_rates` | `PROPOSAL_EMITTED` (`unsupported_rate_duration`) | ✅ |
| `non_integer_solution` (inverse) | `REFUSED_KNOWN_BOUNDARY` | — |
| `missing_time` (underdetermined) | `REFUSED_KNOWN_BOUNDARY` | — |
| `temporal_state` (clock time) | `REFUSED_KNOWN_BOUNDARY` | — |

Exactly **2** proposals over the rate gold — only the rate-like unsupported features
(`rate_unit_mismatch`, `combined_rates`), never the boundaries.

## Anti-over-broad-refusal fix (a regression caught in R3.1)
Adding R3 to the router initially **blocked an R2 proposal**: R3's reader returned `missing_rate`
(a substantive boundary) on R2's `r2-011` (a non-rate problem), and boundary-first classification
let that block R2's legitimate `missing_total_count` proposal. Fix: R3 claims `missing_rate` ONLY
when rate-like structure (a duration) is present; otherwise it refuses `not_rate_shaped` →
`input_shape` (not-my-domain). So **R3 never claims a substantive boundary on R1/R2 text** — the
same discipline as the N6 `category_pair_not_found` fix. `r2-011` proposes again; R1/R2 unaffected.

## Invariants held
R1 **7/0/3** · 15-case **15/0/0** · R2 reader **10/0/0** · R3 reader **8/0/0** (answers 6/0/6) ·
serving unchanged · off-serving · 121-test smoke green incl. architectural invariants and both
existing idle contract suites. No `AMBIGUOUS_ORGAN` on any gold (the three organs are exclusive).

## Next
Per the agreed sequencing: **R3.2 — explicit unit conversion** (minutes↔hours, exact rational
only, no floats), which directly closes the `rate_unit_mismatch` gap this loop now surfaces as a
proposal. Combined rates / multi-agent composition come after.
