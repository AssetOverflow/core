# Comprehension organ capability ledger

**As of:** `main` @ `3381e031` (after #646–#648 and the CMB ladder #650–#656).
A take-stock record of the off-serving comprehension system built so far — what
each organ does, where it lives, the lane that proves it, and what is
deliberately deferred.

This is a **consolidation** artifact (docs only, no capability change). It exists
so the next capability lands against a written whole rather than a stack of
per-batch ledgers. The R4 combined-rate organ has its own frozen v1 ledger
(`docs/analysis/combined-rate-capability-ledger-2026-06-08.md`); it is summarized
here as one organ among four.

## The shape of the work

We stopped patching one GSM8K shape with one reader rule. Each capability is now
a small **organ** built down a fixed ladder, off the sealed serving path:

```text
gold (ruler) → setup oracle → solver → answer-verifier → reader → router/contemplation → proposal ledger
```

- **gold / setup oracle** — span-free canonical *setup* signature; a fixture's
  `expect` (`solved` / `solver_refuses` / `reader_refuses`) is checked against an
  independent gold ruler, not against the reader that produced it.
- **solver** — pure typed computation over the setup; refuses (never guesses)
  outside its competence.
- **answer-verifier** — ties a solved value to a labeled answer choice
  (`generate/answer_choices/verify.py`), shared across organs.
- **reader** — text → typed setup, or a closed-set `Refusal`.
- **router / contemplation** — picks exactly one organ; on its own family a
  refusal can become a **proposal**; on foreign text it must step aside.
- **proposal ledger** — proposals are `proposal_only` / `mounted:false` /
  `requires_review:true`, content-addressed, never self-installed; they flow
  through the existing `teaching/*` HITL flywheel (ADR-0055/56/57), never a
  parallel correction path.

### The off-serving guarantee (load-bearing)

Every organ imports **no** `generate.derivation` and **no**
`core.reliability_gate`. That import-disjointness is what makes it
*structurally impossible* for this whole subsystem to regress the sealed GSM8K
serving metric or the pinned-SHA lanes. It is checked, not asserted — the
router-hygiene + off-serving greps are part of each batch's acceptance.

## Organs

### R1 — relational arithmetic

- **Capability.** "Quantity per container × containers", inverse frames, and the
  relational single-step arithmetic family. The first organ; established the
  gold→oracle→reader ladder.
- **Lives in.** `generate/` reader + `evals/setup_oracle/` (gold `r1_gold.jsonl`).
- **Lane.** setup oracle **7 / 0 / 3** (7 solved, 0 wrong, 3 refused-correct).
- **Ledger.** `docs/analysis/r1-inventory-ledger-*.md`.

### R2 — finite integer constraints

- **Capability.** Two-category integer constraint problems (a finite-integer
  constraint compiler: enumerate the bounded integer solution space, refuse if
  not uniquely determined). ADR-0217 (renumbered from 0211 — collided with the
  conformal-falsification-bench ADR; see that ADR's header).
- **Lives in.** `generate/` constraint reader + `evals/constraint_oracle/`
  (gold + reader lane).
- **Lane.** reader **10 / 0 / 0**.
- **Ledger.** `docs/analysis/r2-inventory-ledger-*.md`;
  `docs/decisions/ADR-0217-r2-finite-integer-constraint-compiler.md`.

### R3 — explicit single-rate (+ exact minute/hour conversion)

- **Capability.** A single explicit rate (`<N> <plural> per <singular>`), one
  duration or quantity unknown, compound-unit algebra
  (`mile/hour = quantity/time`). R3.2 adds **exact** time-unit conversion:
  `60 miles per hour for 30 minutes → 30 miles`. Conversion is rational
  (`fractions.Fraction`), confined to the solver, **int-or-refuse — no float
  path**. A non-convertible duration (`…per hour for 3 gallons`) refuses
  `rate_unit_mismatch` and stays a proposal surface.
- **Lives in.** `generate/rate_comprehension/`
  (`units` / `model` / `conversion` / `solver` / `reader`) +
  `evals/rate_oracle/` (gold `rate_gold.jsonl`).
- **Lane.** gold **13 / 13 valid** (7 solved / 2 solver_refuses / 4 reader_refuses);
  reader **9 setup_correct / 0 wrong / 4 refused** → answers **7 / 0 / 6**.
- **Ledger.** `docs/analysis/r3-rate-inventory-ledger-*.md`,
  `r3-2-unit-conversion-2026-06-08.md`.

### R4 — combined (two-rate) integer rates

- **Capability.** Two explicit `<N> <plural> per <singular>` rates over **one**
  shared compound unit, combined by an **explicitly cued** mode — **sum**
  (cooperation: *together / combined / both*) or **difference** (opposing flow:
  *fills … removes / drains*) — answering one of {net rate, accumulated quantity,
  elapsed time} **only when the result is an exact positive integer**. Everything
  outside that envelope refuses with a closed-set reason. Built CMB-a (gold +
  oracle) → CMB-b (exact integer solver) → CMB-c (reader, last) → CMB-d
  (router/contemplation wiring + domain-precedence).
- **Lives in.** `generate/combined_rate_comprehension/`
  (`units` / `model` / `solver` / `reader`) + `evals/combined_rate_oracle/`
  (gold `combined_rate_gold.jsonl`). Router/contemplation wiring in
  `core/comprehension_attempt/` + `generate/contemplation/`.
- **Lane.** gold **19 / 19 valid** (6 solved / 5 solver_refuses / 8 reader_refuses);
  reader **11 setup_correct / 0 wrong / 8 refused** → answers **6 / 0 / 13**.
- **Boundaries.** Solver: `non_positive_net_rate`, `non_integer_solution` (pure
  integer, no float/Fraction). Reader substantive: `rate_unit_mismatch`
  (`must_remain_refused` *until a dimension registry exists — not forever*),
  `combine_mode_ambiguous`, `missing_second_rate`. Deferred (proposal surfaces):
  `three_or_more_rates`, `reciprocal_work_rate_deferred`, `clock_interval_deferred`.
- **Ledger.** `docs/analysis/combined-rate-capability-ledger-2026-06-08.md`
  (frozen v1 claim + prominent non-claims), `cmb-lookback-review-2026-06-08.md`.

## Shared machinery

### Router + contemplation + proposal loop

- **Router** (`core/comprehension_attempt/`) classifies text and routes to
  **exactly one** organ (`r1_quantitative` / `r2_constraints` / `r3_rate` /
  `r4_combined_rate`), collecting one attempt per organ and selecting the unique
  `setup_correct`. R4's reasons are namespaced `cmb_*` (`classify.py::cmb_reason`)
  **before** the registry sees them, so an R4 boundary never inherits an R2/R3
  family for the same bare string.
- **Contemplation** (`generate/contemplation/pass_manager.py`) drives
  read→solve→verify and lands on one of a closed set of **terminals**
  (`SOLVED_VERIFIED` / `REFUSED_KNOWN_BOUNDARY` / `PROPOSAL_EMITTED` / …).
- **Failure families** (`core/comprehension_attempt/failure_family.py`) map each
  closed-set refusal reason to a family with `must_remain_refused` /
  `proposal_allowed` / `owner` (`r1` / `r2` / `r3` / `r4` / `cross`). Only
  genuine, domain-recognized coverage gaps propose (the R2 `missing_*` totals; the
  rate-like `unsupported_rate_duration`; the three R4 `cmb_unsupported_*`
  deferrals → `cmb_gold_fixture`). Boundaries that must stay refused — non-integer,
  temporal-state, underdetermined, ambiguous-combine, unit-mismatch — do not.

### Proposal-review reporter (RPT)

- `core/proposal_review/` — a read-only reporter over the emitted proposal
  ledger: counts, families, owners, content addresses. Deterministic CLI
  (`python -m core.proposal_review`). It *reports*; it never mounts or ratifies.
- **Ledger.** `docs/analysis/proposal-review-reporter-*.md`.

### idle_tick read-only visibility (IT)

- `chat/runtime.py::idle_tick` gained an **opt-in, read-only** proposal-review
  sub-pass (`RuntimeConfig.review_pending_proposals`, default `False`),
  failure-isolated, that surfaces pending proposals during idle without doing
  work, setting a checkpoint, or ratifying anything.
- **Ledger.** `docs/analysis/proposal-review-idle-integration-*.md`.

## Standing invariant — router/organ hygiene

> **No organ may block another organ's legitimate proposal unless it has first
> positively recognized the input as its own family.** On foreign text an organ
> must refuse with the non-substantive `input_shape` family — never a
> substantive boundary.

Pinned by `tests/test_router_organ_hygiene.py` (#646): for each organ × every
*other* organ's gold, the refusal must map to `input_shape`. This caught the
recurring over-broad-refusal hazard three times before it was crystallized
(N6 `category_pair_not_found`, R3e `temporal_state`, R3.1 `missing_rate`). Every
new organ must clear this lane before it ships.

- **Ledger.** `docs/analysis/router-organ-hygiene-invariant-*.md`.

## Standing precedent — domain-precedence adjudication

The hygiene invariant governs *foreign* text (step aside as `input_shape`). Its
companion governs the harder case: when a **specific** organ and a **broad** organ
both legitimately recognize the *same* text.

> **A `setup_correct` from a broader organ is not automatically admissible if a
> more specific organ positively recognizes load-bearing structure that the
> broader organ would drop.**
>
> **First concrete rule (CMB-d, `router.py::cmb_is_authoritative`):** when R4
> positively recognizes combined-rate shape (a combined setup, or a *substantive*
> `cmb_*` refusal), R4's recognition **beats** R3's single-rate read of the same
> text — for both routing (veto R3's `setup_correct`) and family attribution
> (suppress R3 so R4 owns the terminal/proposal). The exception: if R4 only
> stepped aside (`not_combined_rate_shaped` → `input_shape`), it cedes to R3.

**Proof cases** (`tests/test_cmb_router_contemplation.py`):

- **cmb-11** — R4 `missing_second_rate` **vetoes** R3's wrong single-rate answer
  (would-be `12`); terminal `REFUSED_KNOWN_BOUNDARY`, never a wrong answer.
- **cmb-15** — R4 cedes (`input_shape`); R3 solves the genuine single rate (`180`).
- **cmb-12 / 13 / 14** — R4 owns proposal attribution for specific combined-rate
  deferrals; R3's broader over-read is suppressed so the growth signal is filed
  under the correct combined-rate family.

R3 is **unchanged**: the adjudication lives entirely at the router/contemplation
layer. This precedent generalizes to any specific↔broad organ pair
(geometry+arithmetic, unit-conversion+rate, multi-equation+simple-arithmetic).

- **Ledger.** `docs/analysis/combined-rate-capability-ledger-2026-06-08.md` §7.

## Whole-system lane state (this commit)

| Lane | State |
|---|---|
| R1 setup oracle | 7 / 0 / 3 |
| R2 reader | 10 / 0 / 0 |
| R3 gold | 13 / 13 valid (7 / 2 / 4) |
| R3 reader → answers | 9 / 0 / 4 → 7 / 0 / 6 |
| R4 gold | 19 / 19 valid (6 / 5 / 8) |
| R4 reader → answers | 11 / 0 / 8 → 6 / 0 / 13 |
| router-organ-hygiene | green |
| domain-precedence (CMB↔R3) | green |
| off-serving (import grep + AST) | clean — no `generate.derivation` / `core.reliability_gate` |
| GSM8K serving | unchanged (sealed) |

`answer_wrong == 0` across every organ. The discipline is "6/0/6 over 11/2/0" —
breadth never bought with a single wrong answer.

## Deferred (named, not forgotten)

- **R3.3** — length (`mile ↔ km`) and currency (`dollar ↔ cent`) conversion.
  Build only if an existing R3 fixture/proposal needs it; the rational-conversion
  substrate is already proven for time.
- **R4 combined-rate deferrals** — the three filed growth surfaces (≥3 rates,
  reciprocal work-rate, clock-interval) plus the dimension-registry work that
  would let `cmb_rate_unit_mismatch` become a convertible-unit proposal. Picked up
  only when a real fixture demands one; see the R4 v1 ledger §5/§8.
- **Other organs** — percentage/ratio, geometry, n-variable systems, compound
  conversions. Each is a new rung down the same ladder, never reader-first.

## Next frontier — the served surface (not more comprehension)

Combined-rate v1 is **frozen** (R4 v1 ledger). The off-serving comprehension organ
stack now reads:

```text
R1 relational arithmetic · R2 finite-integer constraints ·
R3 single-rate + exact conversion · R4 combined-rate v1
shared: multi-organ routing · typed contemplation · proposal-only growth ·
        idle/review boundary · router-organ hygiene · domain-precedence adjudication
serving: unchanged (sealed)
```

The next move is **not** more off-serving comprehension. It is a qualitatively
different frontier — the **served-surface epistemology**: *what may CORE disclose
through the served surface?* (graded disclosure / a reserved `VERIFIED` reach
level, activating ADR-0206 `govern_response` / `shape_surface` / `ReachLevel` and
reusing `core/epistemic_state.py` — **not** a parallel correction/serving path).
Because it touches serving epistemology, it is **scoped first, before any code.**
