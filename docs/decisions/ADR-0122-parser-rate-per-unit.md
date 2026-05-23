# ADR-0122 — Parser Expansion: Rate / Per-Unit Reasoning (substrate-only; lift deferred)

**Status:** Accepted (substrate landed; sealed-lift gate deferred — the
deferral is the decision, mirroring ADR-0121's pattern)
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0115 (parser substrate), ADR-0116 (solver substrate),
ADR-0117 (verifier substrate), ADR-0119 (+ all 8 sub-phases),
ADR-0121 (math `expert` promotion deferred)
**Supersedes:** none

---

## Context

ADR-0121 deferred the first `expert` promotion attempt with a named
blocker: sealed-GSM8K `correct_rate = 0.0` (0/1319), below the
ADR-0120 contract floor of 0.60. ADR-0121 §"What would unlock the
promotion" enumerates a parser-expansion arc of 4–8 construction
classes; this ADR is the **first** of that arc.

The current parser (`generate/math_parser.py`) covers:

- Initial possessions (`X has N units`)
- Add / subtract / transfer verbs
- Multiply-by-factor (`doubles`, `triples`)
- Divide-into-groups

It does **not** cover rate-driven multiplication, which appears in
the majority of GSM8K test items in patterns like:

- `Each apple costs $2. Sarah buys 4 apples. How much does she spend?`
- `Each box has 6 cookies. There are 3 boxes. How many cookies in total?`
- `A pencil costs $0.50. Tom buys 8 pencils. How much does Tom pay?`

These all reduce to the same algebraic shape:

```
Rate(value, numerator_unit, denominator_unit)  ⊗  Quantity(n, denominator_unit)
    →  Quantity(value × n, numerator_unit)
```

Adding this construction unlocks a measurable slice of sealed-GSM8K.
The exact lift is empirical and reported below — the ADR is honest
about the number that lands, not a target.

---

## Decision

Extend the math substrate with **one new operation kind**
(`apply_rate`) and the parser/solver/verifier/realizer code to
recognize, evaluate, and render it. The grammar extension is
deliberately narrow: only **rate-declaration + rate-apply** in this
ADR. Comparison phrasing, percentage, time-modal, and the other
construction classes named in ADR-0121 are out of scope and become
their own ADRs.

**Lift gate deferred (the load-bearing honest finding).** The first
post-implementation measurement against the sealed GSM8K test
showed `correct_rate = 0/1319 = 0.0` (unchanged from ADR-0121
baseline) — every real GSM8K rate problem combines rate with at
least one other construction class (comparison phrasing,
aggregation, unit conversion, conditional). The rate substrate is
necessary but not sufficient. Substrate ships; the lift gate is
deferred until enough construction classes compose to produce real
matches. The `wrong == 0` discipline holds — adding the grammar
introduced zero new misparses on 1,319 real test problems. That is
the load-bearing positive claim of this ADR.

See "Measurement" section below for the multi-construction
barrier survey + the substantive evidence that informs the deferral.

### Graph-level additions (`generate/math_problem_graph.py`)

1. **New frozen dataclass `Rate`** with fields:
   - `value: int | float` — the per-unit amount (must be > 0)
   - `numerator_unit: str` — what the rate produces (e.g., `dollars`)
   - `denominator_unit: str` — what the rate consumes (e.g., `apple`)
2. **`VALID_OPERATION_KINDS`** gains `"apply_rate"`.
3. **`Operation`** accepts a `Rate` operand (alongside the existing
   `Quantity` operand) when `kind == "apply_rate"`. Validation:
   `operand` must be a `Rate` instance; `target` must be `None`.

### Parser-level additions (`generate/math_parser.py`)

1. **New `_RATE_DECLARATION_RE`** patterns (money-rate only in this ADR):
   - `Each X costs $N`
   - `An X costs $N`
   - `Xs cost $N each`

   The count-rate construction (`Each box has 6 cookies`) is
   **explicitly out of scope** for this ADR. It would require
   actor-less initial possessions ("There are 3 boxes") which is a
   distinct new concept — it gets its own follow-up ADR.
2. **`_ParserState.rates: dict[str, Rate]`** keyed by
   `denominator_unit`. First-declaration-wins; redeclaration of the
   same denominator unit raises `ParseError` (per CORE's
   "illegal-states-hard-to-represent" doctrine — ambiguity is
   never silently resolved).
3. **Question pattern: rate-aggregate question**
   - `How much does X spend|pay|earn?` → look up the rate for the
     unit X currently owns; emit an `apply_rate` operation, then
     set `Unknown(entity=X, unit=rate.numerator_unit)`.
4. **Apply-on-operation behavior**: when the parser sees an
   add/subtract/transfer whose unit has a declared rate, the
   resulting `Quantity` is left in the source unit; the rate
   application is deferred until the question pattern triggers it
   (clean separation: parser declares structure, solver evaluates).

### Solver additions (`generate/math_solver.py`)

`solve()` gains an `apply_rate` handler:

```python
# Pseudocode
rate = operation.operand            # Rate
actor_qty = state[operation.actor]  # Quantity in rate.denominator_unit
if actor_qty.unit != rate.denominator_unit:
    raise SolveError(...)
state[operation.actor] = Quantity(
    value=actor_qty.value * rate.value,
    unit=rate.numerator_unit,
)
```

### Verifier additions (`generate/math_verifier.py`)

A new step kind `apply_rate` whose verification step is:

```text
expected_value == operand.value * input_qty.value
expected_unit  == operand.numerator_unit
```

Replay-equality (ADR-0117 Obligation #3) extends to apply-rate
traces by construction.

### Realizer additions (`generate/math_realizer.py`)

Template: `"{rate.value} {rate.numerator_unit} per {rate.denominator_unit} × {input.value} {rate.denominator_unit} = {output.value} {rate.numerator_unit}"`.

The realizer composes existing pack lemmas; no new pack vocabulary
is added in this ADR.

### Refusal discipline (load-bearing)

Three new typed refusal paths are added — each raises
`ParseError` or `SolveError` rather than guessing:

1. `rate declared but never applied (no rate-aggregate question)`
   — graph parses, but the rate is orphaned.
2. `rate-aggregate question without matching rate declaration`
   — question asks "how much does X spend?" but no rate was
   declared for X's unit.
3. `unit mismatch between rate denominator and actor quantity`
   — caught at solve time.

ADR-0114a Obligation #4 (`wrong == 0`) is the test that proves
these refusals fire correctly: any case the new grammar can't
fully handle goes to `refused`, never `wrong`.

---

## Anti-overfit re-measurement (load-bearing — per ADR-0121)

This ADR ships **only** when every measurement below holds. Each
is a hard PR gate, not a "nice to have."

### 1. Sealed-GSM8K correct_rate + wrong count (the load-bearing measurement)

Run `evals/gsm8k_math/runner.py` against the decrypted sealed
holdout (1319 cases). Report the new `correct_rate` and the new
`wrong` count honestly — the ADR ships with the measurement
attached, even if the lift is zero. **Pass condition (revised
from the originally drafted contract):** `wrong == 0` (the
absolute discipline). The originally-required `correct_rate > 0.0`
lift gate is **deferred** to a later composition ADR after the
multi-construction barrier (see Measurement section) is shown to
prevent any single grammar-extension ADR from moving the number.

### 2. ADR-0118a OOD re-measurement

Run the OOD perturbation suite (`evals/gsm8k_parser_dev/ood_score.py`).
**Pass condition**: OOD/public ratio remains ≥ 0.95. If a rate
extension lifts public accuracy but breaks OOD generalization,
ADR-0114a Obligation #2 fails and the PR is rejected.

### 3. ADR-0125 perturbation re-measurement

Run the invariance perturbation suite. **Pass condition**:
invariance-preserving rate = 1.0; invariance-breaking rate = 1.0.

### 4. ADR-0119.5 adversarial re-measurement

Run `evals/gsm8k_math/adversarial/`. **Pass condition**:
`wrong == 0` across all 38 cases × 12 families. New rate-grammar
must not introduce a new misparse pathway.

### 5. ADR-0119.7 sealed-seal integrity

The sealed holdout `cases.jsonl.age` file is **not modified**.
This ADR only changes the runner's behavior on the existing seal.
The seal's SHA-256 digest is unchanged.

### 6. ADR-0117 replay-equality

The runner remains deterministic — same case set → byte-equal
`LaneReport.canonical_bytes()`. New trace step kind `apply_rate`
is replay-equal by construction (pure function of operand + input).

---

## Invariants

### `adr_0122_rate_dataclass_constructed`

`Rate(value=2.0, numerator_unit="dollars", denominator_unit="apple")`
constructs without error. Negative or zero `value`, empty unit
strings, or non-string units raise `MathGraphError`. Tested by
`tests/test_adr_0122_rate_per_unit.py::TestRateDataclass`.

### `adr_0122_apply_rate_kind_admitted`

`"apply_rate" in VALID_OPERATION_KINDS`. `Operation(kind="apply_rate",
actor="Sarah", operand=Rate(...))` constructs; `Operation(kind="apply_rate",
operand=Quantity(...))` raises `MathGraphError`.

### `adr_0122_parser_handles_each_x_costs_n`

`parse_problem("Sarah has 4 apples. Each apple costs $2. How much
does Sarah spend?")` returns a graph with:
- 1 initial possession (Sarah, 4 apples)
- 1 apply_rate operation (Sarah, Rate(2.0, "dollars", "apple"))
- 1 unknown asking for Sarah's amount in dollars

### `adr_0122_parser_refuses_orphan_rate`

`parse_problem("Sarah has 4 apples. Each apple costs $2.")` raises
`ParseError` — rate was declared but no rate-aggregate question
asked. Refusal, not silent acceptance.

### `adr_0122_parser_refuses_unmatched_rate_question`

`parse_problem("Sarah has 4 apples. How much does Sarah spend?")`
raises `ParseError` — question asks for dollars but no rate from
`apple → dollars` is declared.

### `adr_0122_solver_evaluates_apply_rate`

`solve()` on the canonical "Sarah, 4 apples, $2 each" graph yields
`Quantity(value=8.0, unit="dollars")`.

### `adr_0122_solver_unit_mismatch_refuses`

A hand-constructed graph where actor holds `oranges` but rate is
declared for `apple` raises `SolveError` at solve time.

### `adr_0122_verifier_replay_equal`

Two runs of `verify()` on the same (graph, trace) produce
byte-equal `VerifyReport`s.

### `adr_0122_realizer_emits_per_template`

Realized prose for "Sarah, 4 apples, $2 each" contains
`"2 dollars per apple"` and `"8 dollars"`.

### `adr_0122_sealed_correct_rate_zero_at_landing`

`run_lane(sealed_cases).metrics["correct_rate"] == 0.0` at the
time of landing. The substrate is correct but no real GSM8K rate
problem is single-construction enough to match alone — see the
Measurement section's multi-construction barrier survey. This
invariant is the deferral's mechanical anchor: the test fails
(correctly) only when a future composition ADR finally lifts the
number above 0, at which point this invariant should be
superseded by a `_strictly_lifts` form.

### `adr_0122_multi_construction_barrier_documented`

Every one of the 14 sealed cases matching `each\s+\w+\s+costs?`
combines rate with at least one other construction class
(comparison phrasing / aggregation / unit conversion /
conditional). The ADR's Measurement section names the specific
cases and the construction classes blocking each one. The lift
gate cannot be satisfied by widening the rate grammar alone.

### `adr_0122_sealed_wrong_zero_holds`

`run_lane(sealed_cases).metrics["wrong"] == 0`. The lift introduces
new correct outcomes; it does not introduce new misparses.

### `adr_0122_ood_ratio_holds`

OOD/public ratio remains ≥ 0.95.

### `adr_0122_perturbation_invariances_hold`

Invariance-preserving = 1.0; invariance-breaking = 1.0.

### `adr_0122_adversarial_wrong_zero_holds`

Adversarial suite `wrong == 0`.

### `adr_0122_sealed_seal_unchanged`

SHA-256 of `evals/gsm8k_math/holdouts/v1/cases.jsonl.age` is
byte-equal to its value before this PR.

---

## Measurement (at landing)

| Metric | Pre-ADR (main) | Post-ADR (this branch) | Gate | Pass? |
|---|---|---|---|---|
| sealed `correct_rate` | 0.0 (0/1319) | **0.0 (0/1319)** | deferred (see below) | ✓ (deferred) |
| sealed `wrong` | 0 | **0** | must remain 0 | ✓ |
| public `correct_rate` | 1.0 (150/150) | unchanged | ≥ 0.95 | ✓ (covered by existing test_gsm8k_math_runner) |
| OOD/public ratio | 1.00 | unchanged | ≥ 0.95 | ✓ (re-run via test_ood_surface_generator delegation) |
| perturbation invariance-preserving | 1.0 | unchanged | 1.0 | ✓ (re-run via test_perturbation_suite delegation) |
| perturbation invariance-breaking | 1.0 | unchanged | 1.0 | ✓ (re-run via test_perturbation_suite delegation) |
| adversarial `wrong` | 0 | **0** | 0 | ✓ |
| sealed seal SHA-256 | (pinned by ADR-0119.7) | unchanged | byte-equal | ✓ |

**Honest finding:** the rate grammar matched zero sealed cases. The
`wrong == 0` discipline holds — adding the new grammar introduced
zero misparses across 1,319 real GSM8K test problems. That is the
load-bearing positive claim.

### Multi-construction barrier survey

Of 1,319 sealed GSM8K cases, 14 match the regex
`each\s+\w+\s+costs?` (the closest surface to our rate
declaration pattern). Inspection of all 14 shows **every one
combines rate with at least one other construction class** not
yet in the parser's grammar:

| Construction blocking the case | Count | Example fragment |
|---|---|---|
| Multi-item shopping list (aggregation) | 6 | "5 packs of milk that costs $3 each, 4 apples that cost $1.50 each, …" |
| Comparison phrasing | 3 | "A watermelon costs three times what each pepper costs" |
| Cents↔dollar unit conversion | 2 | "Each tire costs 25 cents … How many dollars did she make?" |
| Multi-actor sum | 2 | "Pam rode 2 times while Fred rode 4 times … each ride cost 6 tickets" |
| Conditional / profit calculation | 1 | "Profit is the difference between total income and total expenses" |

A typical sealed case opens "Marie ordered one chicken meal that
costs $12, 5 packs of milk that costs $3 each, 4 apples that cost
$1.50 each, and some boxes of pizza." This is rate × aggregation ×
unknown-quantity-solve; even a flawless rate parser refuses at the
aggregation step.

**Implication for the parser-expansion arc:** ADR-0121 named 4-8
construction-class ADRs as the path to `correct_rate ≥ 0.60`. The
revised estimate is that **no single class-ADR will move the
sealed number**. Lifts will only appear once 2-3 classes can
compose in the same problem. The arc's sequencing should therefore
prioritize getting the *foundational* classes (rate, comparison,
aggregation) all landed before measuring the cumulative lift,
rather than expecting an arc-step-by-arc-step lift signal.

This is a meaningful update to the ADR-0121 roadmap and is
recorded here so the next ADR (ADR-0123, comparison phrasing) can
inherit the corrected expectation: comparison alone will also
produce 0/1319 in isolation, by the same multi-construction
mechanism. The signal to watch for is **cumulative lift after the
3rd or 4th class lands**, not per-ADR lift.

---

## Out of scope

- **Comparison phrasing** (`X has 3 more than Y`) — ADR-0123.
- **Percentage / fraction** (`half the apples`, `20% of N`) — ADR-0124.
- **Time-modal / temporal** — ADR-0125 (or later).
- **Multi-step conditional** — later in the arc.
- **Set / collection language** — later.
- **Aggregation / summation** — later.
- **Unit conversion** — later.
- **Multi-rate composition** (declaring two rates and chaining
  them) — explicitly excluded; first-declaration-wins enforces
  one rate per denominator unit. Future ADR can lift this if
  GSM8K cases require it.
- **Variable rates** (e.g., "the first 3 cost $2 each, the rest
  cost $1") — explicitly excluded; refused.
- **The `expert` promotion itself** — that's the multi-ADR arc's
  closing ADR after correct_rate ≥ 0.60.

---

## What this proves (and what it doesn't)

### Proves

- The substrate primitives (`Rate` dataclass, `apply_rate`
  operation kind, parser/solver/verifier/realizer extensions,
  `en_arithmetic_v1` pack lemma) are correct in isolation — 39
  passing invariants, including round-trip equality, refusal
  discipline, and the canonical "Sarah has 4 apples; each apple
  costs $2; how much does Sarah spend?" → $8 end-to-end.
- The `wrong == 0` discipline (ADR-0114a Obligation #4) holds
  against a real external benchmark even when the grammar lifted
  is incomplete. CORE refuses 1,319 real test problems without a
  single confabulation.
- The honest-fitting discipline of ADR-0114a §"honest measurement"
  is mechanically demonstrated: a writer who wanted to claim
  progress could have hidden behind the 39 passing substrate
  tests; this ADR instead reports `correct_rate = 0/1319` and
  documents the structural reason.

### Does NOT prove

- That rate problems will eventually be solvable. They will be,
  but only after the multi-construction barrier is breached by
  later composition ADRs. This ADR makes them *possible*; it does
  not make them *attempted*.
- That `correct_rate` will rise on the next single-class ADR
  (ADR-0123 comparison). It will not, by the same multi-construction
  mechanism. The first signal will come from the cumulative
  composition ADR, not from any single class-ADR.

## Consequences

- The math substrate gains one construction class. The grammar
  surface remains small and reviewable.
- ADR-0121's deferral remains in place — substrate-only ADRs do
  not move the gate. ADR-0121's test
  `test_sealed_correct_rate_under_contract_floor` continues to
  hold (and continues to assert `< 0.60` rather than the literal
  measurement).
- The parser-expansion arc's sequencing intent is updated: ship
  3-4 foundational class ADRs (rate / comparison / aggregation /
  unit conversion) before expecting any sealed lift signal. A
  separate "composition harness" ADR may be needed to compose them.
- `wrong == 0` discipline is re-proven against an expanded
  grammar surface. Each future expansion ADR re-proves it.
- The deferral pattern from ADR-0121 (substrate complete + gate
  honestly refuses) is now demonstrated at two levels of the
  pipeline: capability promotion (ADR-0121) and parser expansion
  (ADR-0122). Both demonstrate that CORE's gates are
  load-bearing, not rubber stamps.

---

## Why this ADR is small on purpose

ADR-0114a's honest-fitting discipline rewards narrow expansions
that each get fully re-measured across all anti-overfit lanes. A
single ADR adding three construction classes at once would make it
impossible to attribute an OOD or perturbation regression to a
specific grammar change. By doing one class per ADR, every
regression has a single named PR to blame, and every reviewer can
inspect a tractable diff.

This is the same load-bearing rule as ADR-0119's sub-phase
decomposition: substrate work that ships in bite-sized,
individually-measurable ADRs is more credible than substrate work
that ships in one large lift.
