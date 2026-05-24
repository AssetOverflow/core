# ADR-0141 — `multiply` as Dilator (Positive Non-Zero Multipliers Only)

**Status:** Draft
**Date:** 2026-05-24
**Author:** CORE agents
**Parent:** [ADR-0140](./ADR-0140-subtract-and-additive-group-closure.md), [ADR-0139](./ADR-0139-arithmetic-as-versor-spike.md)
**Engine target:** CGA cognitive engine (`algebra/versor.py`, `algebra/cga.py`)

---

## Context

ADR-0139 and ADR-0140 proved the **additive subgroup** of Cl(4,1)
translators along e1 is exactly closed: `add`, `subtract`, inverse
composition, round-trip, and commutativity all land at residual
0.0e+00 in float64. Three levels of verification (pointwise,
algebraic group, application round-trip) all hold exactly.

That subgroup is closed under one operation pair (translation /
inverse-translation). Multiplication is structurally different —
**dilation** in conformal geometric algebra is a *different versor
manifold* with a different generator. Whether the dilator construction
closes at the same tolerance as the translator does is **not implied by
the additive result**; it has to be re-derived and re-tested.

This ADR is the spike that tests it. Scope is deliberately narrow:
**positive non-zero real multipliers only.** Negative multipliers and
multiplication by zero are explicitly deferred to follow-on ADRs.

---

## Why this scope is narrow on purpose

Three operations look like "multiplication" at the math level but
have structurally distinct algebraic representations:

| Operation | CGA construction | This ADR? |
|---|---|---|
| `multiply(positive_nonzero_real)` | Pure dilator: `D_s = exp(α/2 · (n_o ∧ n_inf))` where `s = exp(α)` | **Yes** |
| `multiply(negative_real)` | Dilation composed with reflection (or inversion) — not a pure dilator | Deferred (ADR-0141b or 0141.N) |
| `multiply(0)` | Degenerate. `D_0` involves `log(0) = −∞`; not a well-defined versor | Deferred (ADR-0141.Z) |

Trying to cover all three in one ADR conflates the algebraic claim
("dilation closes exactly") with two separate construction claims
(reflection-composition, degenerate-handling). If any of the three
fails, the diagnosis becomes harder. Splitting them isolates the
*spike's* falsification clearly:

- If this ADR fails, dilator-as-multiply is wrong and the lift program
  pauses.
- If this ADR passes but the deferred ADRs fail, dilator-as-multiply
  works but composed constructions need different machinery.

Same discipline as ADR-0139 starting with `add` only and ADR-0140
adding `subtract` separately rather than trying to ship `multiply`
in the same PR.

---

## Decision

### Construction

`multiply(scale)` is implemented as the **CGA dilator versor**:

```text
D_s = exp(α/2 · (n_o ∧ n_inf))    where s = exp(α), s > 0
```

Computed via the closed-form expansion that uses
`(n_o ∧ n_inf)² = (something with known value derivable from cga.py
conventions)`. The exact construction is derivable from the existing
`algebra/cga.py` primitives; no new algebra is invented in this ADR.

Restriction: `scale > 0` and `scale ≠ 0`. Calls with `scale <= 0` raise
a typed `ValueError`. The check happens at construction time so the
restriction is visible at the boundary.

### Application

```text
result = versor_apply(D_s, embed_quantity(value, unit))
```

`versor_apply` already has the dual-path behavior for null inputs (CGA
points), so no change to the existing primitive is required. Same
substrate that ADR-0139 and 0140 used.

### Decoding

After dilation, the e1 coordinate of the result point gives `value * s`.
`decode_quantity(F, unit)` (unchanged) extracts it.

---

## Acceptance

A test module — `tests/test_arithmetic_multiply_as_dilator.py` — passes
with assertions on a fixed set of `(a, s)` pairs where `s > 0` strictly.

### Assertion families

**Family 1 — Dilator well-formedness.** For each `s` in the test set:
- `versor_condition(multiply(s)) < 1e-6` (dilator is a unit versor).

**Family 2 — Closure under sandwich.** For each `(a, s)`:
- `cga_inner(R, R) < 1e-5` where `R = versor_apply(multiply(s), embed_quantity(a, "u"))`.

**Family 3 — Arithmetic correctness.** For each `(a, s)`:
- `decode_quantity(R, "u") == (a * s, "u")` within `1e-9`.
- Includes integer `s` (e.g., `s = 2, 3, 10`), unit fraction `s` (e.g.,
  `s = 0.5, 0.25, 1/3`), and irrational-ish `s` (e.g., `s = √2 ≈
  1.4142..., s = π ≈ 3.14159...`).

**Family 4 — Replay determinism.** Two independent runs produce byte-
identical multivectors for `multiply(s)`, applied results, and decoded
values.

**Family 5 — Identity dilator.** `multiply(1.0)` equals the scalar
identity versor `[1, 0, 0, ...]` within `1e-9` component-wise. This is
the analog of `translator(0)` being identity in the additive group;
verified explicitly because it's a degenerate-but-important edge.

**Family 6 — Composition into product.** For each `(s1, s2)`:
- `geometric_product(multiply(s1), multiply(s2)) == multiply(s1 * s2)`
  component-wise within `1e-9`.
- Tests the multiplicative group structure: dilations compose to
  dilations by the scalar product of their scales. This is the analog
  of ADR-0140 family 9 (additive composition) for the multiplicative
  group.

**Family 7 — Inverse composition.** For each `s`:
- `geometric_product(multiply(1/s), multiply(s))` equals the scalar
  identity within `1e-9`.
- Tests that `multiply(1/s)` is the inverse of `multiply(s)`. This
  introduces the operation that becomes ADR-0141's natural sibling
  (division-as-inverse-dilator) without committing to it formally.

**Family 8 — Round-trip closure.** For each `(a, s)`:
- `versor_apply(multiply(1/s), versor_apply(multiply(s), embed_quantity(a, "u")))`
  decodes to `(a, "u")` within `1e-9`.

**Family 9 — Commutativity.** For each `(s1, s2)`:
- `geometric_product(multiply(s1), multiply(s2))` byte-equals
  `geometric_product(multiply(s2), multiply(s1))`.
- Dilations along a single conformal axis commute (this is the abelian
  property of the multiplicative subgroup).

### Boundary refusal

**Family 10 — Refusal on invalid scale.** For each `s ∈ {0, -1, -3.5}`:
- `multiply(s)` raises `ValueError` with a typed message naming the
  scale value and the restriction.
- Test that the error fires at construction time, not at application
  time.

### Fixed test cases

```text
Scale set for families 1-5, 7, 8 (a, s):
  (0, 2), (1, 2), (1, 3), (3, 4),
  (5, 0.5), (10, 0.25), (4, 0.75),
  (7, 1.0),                          ← identity scale
  (2, 1.4142135623730951),           ← √2
  (1, 3.141592653589793),            ← π
  (100, 0.01), (0.01, 100),
  (-5, 2), (5, -2)                   ← excluded — see family 10

Composition set for families 6, 9 (s1, s2):
  (1, 1), (2, 1), (1, 2), (1.0, 1.0),
  (2, 3), (3, 2), (0.5, 4),
  (1.4142..., 1.4142...) → 2.0       ← √2 × √2 round-trip
  (3.14159..., 1.0),
  (10, 0.1) → 1.0

Boundary set for family 10 (invalid s):
  0, -1, -3.5, -100, -0.0001
```

---

## Non-goals

Out of scope for this ADR:

- **No negative multiplication.** `multiply(-3)` is deferred. The
  construction would need to compose a dilator with a reflection or
  inversion, which is a different versor and requires its own
  closure analysis. Tests for negative `s` in family 10 verify
  refusal-on-construction, not admission.
- **No multiplication by zero.** `multiply(0)` is deferred. The
  dilator `D_0` is degenerate (involves `log(0)`). A separate ADR
  decides whether `multiply(0)` returns the zero embedding or raises.
- **No `divide` operation.** Family 7 tests `multiply(1/s)` as an
  inverse internally but does not expose a public `divide()` function.
  That's a sibling ADR (likely 0141.B).
- **No `Rate` construction.** Rates (`apply_rate`) are
  bivector-shaped and require their own ADR (0142).
- **No `MathProblemGraph` consumer.** No `PropositionGraph`
  construction. No `CognitiveTurnPipeline` integration. No GSM8K case
  routed. Same boundary as ADR-0139 and ADR-0140.
- **No pack changes.** `en_arithmetic_v1` already contains the
  `multiply` lemma; this ADR doesn't extend the pack.

Engine B (`math_solver.py`, candidate-graph parser, S.x corridor) remains
unchanged. The 3/50 GSM8K admission set is preserved.

---

## Rationale

**Why dilator at all?**

In CGA, the natural representation of scalar multiplication on
Euclidean points is dilation: a versor that scales distances from the
origin. Applied to a point at `[a, 0, 0]` on the e1 axis, the dilator
`D_s` (for `s > 0`) produces the point at `[a·s, 0, 0]`. This is the
direct analog of how translators represent addition.

Dilators are unit versors *on their manifold* — but that manifold is
different from the translator manifold. The closure properties have to
be checked explicitly; they're not inherited from ADR-0139/0140.

**Why the multiplicative group, not just point-pair tests?**

Same reason ADR-0140 added group-structure tests beyond pointwise
correctness: scalar multiplication on positive reals *is* a group
(abelian, with identity 1, inverse `1/s`, associative). If the dilator
construction faithfully decodes multiplication, the group axioms must
hold automatically. Testing them (families 5–9) is structural
verification, not optional.

If family 6 (composition into product) fails, the construction is
decoding something that *isn't* the multiplicative group on positive
reals. If family 9 (commutativity) fails, the algebra is non-abelian
along the conformal e1 axis — which would be a much deeper problem
than just "multiply doesn't work."

**Why irrational test values?**

ADR-0139 tested only integer and simple-fractional values. The
dilator construction involves `exp(α/2)`, which produces irrational
intermediate values even for integer `s`. Including `√2` and `π` in the
test set probes whether the construction handles the full positive-real
domain or only computationally clean values.

If `(2, √2)` and `(2, √2)` compose to `(2, 2)` byte-equal (family 6's
`√2 × √2 = 2` case), that's evidence the construction is closed under
its own outputs — not just on inputs the test author happened to
write down.

**Why no test for negative scales beyond family 10?**

Family 10 verifies the *boundary refusal* — that the construction
rejects invalid inputs at construction time. It does *not* test what
the right behavior for negative scales should be; that's the deferred
ADR's job. The test here only proves the boundary is enforced.

---

## Risks the spike must surface

This ADR concentrates the **highest algebra risk** in the lift program
to date. Several plausible failure modes:

- **Dilator construction may not close at `1e-6`.** Translators closed
  *exactly* (residual 0.0) because their bivector squared to zero.
  Dilator bivectors `(n_o ∧ n_inf)` do *not* square to zero — they
  square to a known value derivable from the metric signature. So the
  closure cancellation is different and may only be at machine epsilon
  (~1e-15) rather than exactly 0.0. **Report measured residuals; do
  not loosen the 1e-6 threshold.**

- **The exponential expansion may introduce drift.** `D_s = exp(α/2 ·
  (n_o ∧ n_inf))` is computed via series expansion or via
  `cosh + sinh` decomposition. The latter is closed-form and
  expected to be exact in float64 because `(n_o ∧ n_inf)²` is a known
  scalar; but the implementation has to commit to one or the other and
  measure.

- **Irrational scales may not round-trip exactly.** `√2 × √2 = 2`
  algebraically but in float64 may produce `2.0000000000000004` or
  similar. Family 6's `(√2, √2) → 2` case explicitly probes this. If
  the residual exceeds `1e-9`, that's a finding about the
  construction's numerical fidelity, not a failure to weaken
  tolerance.

- **Composition may produce drift faster than addition.** Multiplying
  `(10, 0.1)` to land on the identity scale relies on `10 × 0.1 = 1.0`
  in float64, which is *not* exact (`0.1` has no finite binary
  representation). Family 6's `(10, 0.1) → 1.0` case is the smallest
  case that probes this drift; the test threshold (`1e-9`) may need to
  be reported honestly even if it doesn't quite hit `0.0`.

- **Identity-dilator may not be the literal scalar `1`.**
  `multiply(1.0)` should equal the identity versor `[1, 0, ...]`. The
  closed-form construction should yield this, but family 5 tests it
  explicitly because the analogous `translator(0)` case was a known
  edge in ADR-0140.

- **Application-level round-trip (family 8) may be worse than
  algebra-level inverse (family 7).** ADR-0140 found these were both
  exactly 0.0, but with translators the cancellation was perfect.
  With dilators, the round-trip involves two non-zero-residual
  versors composing through `versor_apply`. The application path may
  accumulate drift the algebra path doesn't show. **Report both
  family 7 and family 8 residuals independently.**

Per [[feedback-address-critiques-dont-waive]]: any measured value that
exceeds its threshold — even by a small amount — must be reported, not
adjusted-around. If `1e-9` is exceeded in family 3, the finding is
"dilator construction introduces float64-precision drift in arithmetic
correctness," and the ADR's status becomes a partial pass or a
falsification depending on the magnitude.

---

## Replay & invariants

Same invariants as ADR-0139 and ADR-0140:

- `versor_condition(D_s) < 1e-6` for all constructed dilators.
- Null inputs to `versor_apply` stay null.
- No new normalization introduced; no normalization site moves outside
  the allowed list (CLAUDE.md).
- Float64 end-to-end.
- Determinism: same `(a, s)` → identical multivector bytes across runs.

**New cross-cutting invariant introduced by this ADR:** the
multiplicative subgroup of Cl(4,1) dilators along the conformal
diagonal is abelian and closed under composition, with identity at
`s = 1` and inverse at `s ↦ 1/s`, **for `s > 0`**. Families 5–9 are
the CI-enforced statement of this invariant within the restricted
domain.

---

## Sequencing for follow-on

Only if every assertion in this ADR passes:

1. **ADR-0141.B** — `divide` as inverse dilator. Should be near-trivial
   (analog of how `subtract` followed `add`): `divide(s) = multiply(1/s)`,
   with the same group-structure verification.
2. **ADR-0141.N** — Negative multiplication. Needs the composed
   dilation-with-reflection construction. Higher risk than this ADR.
3. **ADR-0141.Z** — Multiplication by zero. Degenerate case; may not be
   representable as a versor at all and may require a typed refusal
   or a different multivector representation.
4. **ADR-0142** — `Rate` as bivector + `apply_rate` as combined
   translator-dilator. Bivectors carry units in two directions; the
   construction is structurally different from both translators and
   dilators.

If this ADR fails, the lift program pauses pending a revised dilator
construction or a fundamentally different multiplication representation.

---

## Decision summary

Extend `generate/math_versor_arithmetic.py` with `multiply(scale)` —
the standard CGA dilator versor restricted to `scale > 0`. Add a test
module verifying ten assertion families (well-formedness, closure,
arithmetic correctness, replay, identity, group composition,
inverse, round-trip, commutativity, and boundary refusal).

Acceptance is binary: every test passes within the specified
tolerances, or the ADR is withdrawn and the lift program pauses
pending a revised construction. Measured values are reported honestly
even when they pass — the threshold is the limit, not the goal.
