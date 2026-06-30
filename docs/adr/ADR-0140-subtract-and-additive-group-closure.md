# ADR-0140 — `subtract` as Inverse Translator + Additive Group Closure

**Status:** Draft
**Date:** 2026-05-24
**Author:** CORE agents
**Parent:** [ADR-0139](./ADR-0139-arithmetic-as-versor-spike.md)
**Engine target:** CGA cognitive engine (`algebra/versor.py`, `algebra/cga.py`)

---

## Context

ADR-0139 proved one operation — `add` — can be represented as a closed
unit versor in Cl(4,1) with all residuals exactly 0.0 in float64. The
construction `T_t = 1 - 0.5·(t·n_inf)` produces an exactly-closed
translator because `(t·n_inf)² = 0` algebraically before any float
arithmetic occurs.

That spike proved the algebraic substrate can host *one* operation. It
did not yet prove anything about the *structure* the operations should
form. Subtract is the smallest follow-on that:

1. Demonstrates the family generalizes — `subtract` is the same construction
   with a negated addend, so it should inherit the exact-closure property
   for free.
2. Surfaces the **additive group structure**. Add + subtract together
   form an abelian group on the e1 axis. The structural identities
   (inverse, identity, associativity, commutativity) are the actual
   thing being decoded — not just "two operations work."

The thesis (`thesis-decoding-not-generating`) is sharper here: the engine
isn't being given subtract as a *new capability*; it's being shown that
the additive group **was already there in the algebra**, and CORE is
decoding the relationships that already hold between the operations.

This ADR makes that decoding visible by testing the group axioms directly.

---

## Decision

### Construction

`subtract(addend)` is implemented as `translator(-addend)`. No new
algebra; the existing `translator()` from ADR-0139 is reused with a
negated argument.

```python
def subtract(addend: float) -> np.ndarray:
    return translator(-float(addend))
```

### Group-property tests

Beyond the six assertion families inherited from ADR-0139, this ADR
introduces **three new families** that test the additive group structure:

- **Family 7 — Inverse composition.** `T_{-b} · T_b = identity`.
  Specifically, the geometric product of `translator(-b)` and
  `translator(b)` equals the scalar `1` (component 0 = 1, all others 0)
  within machine epsilon.

- **Family 8 — Round-trip closure.** `versor_apply(T_{-b}, versor_apply(T_b, X)) = X`.
  An additive shift followed by its inverse recovers the original
  embedded quantity byte-equal at the chosen tolerance.

- **Family 9 — Commutativity of translators.** `T_a · T_b = T_b · T_a = T_{a+b}`.
  Additive translations commute and compose into a single translator
  by the sum. This is the abelian property of the group; if it fails,
  the algebra is decoding something other than scalar addition.

---

## Acceptance

A single test module — `tests/test_arithmetic_subtract_and_group.py` —
passes with the following assertions on a small fixed set of `(a, b)` pairs.

### Inherited from ADR-0139 (applied to subtract)

The same six families ADR-0139 used for `add`, applied to `subtract`:

1. Embedding well-formedness (re-verified on subtract cases)
2. Translator-of-negative well-formedness — `versor_condition(subtract(b)) < 1e-6`
3. Closure under sandwich — `cga_inner(R, R) < 1e-5`
4. Arithmetic correctness — `decode_quantity(R, u) == (a − b, u)` within `1e-9`
5. Replay determinism — byte-identical across runs
6. Composability — `subtract(c) ∘ subtract(b)` decodes to `a − b − c`

### New group-property families

7. **Inverse composition.** For each `b` in the test set:
   `geometric_product(translator(-b), translator(b))` equals the scalar
   versor `[1, 0, 0, ..., 0]` within `1e-9` component-wise.

8. **Round-trip closure.** For each `(a, b)` in the test set:
   `versor_apply(translator(-b), versor_apply(translator(b), embed_quantity(a, "u")))`
   decodes to `(a, "u")` with error `< 1e-9`. Includes the case `b = 0`
   (degenerate — should be identity in the algebra).

9. **Commutativity / composition into sum.** For each `(a, b)`:
   - `geometric_product(translator(a), translator(b))` equals
     `translator(a + b)` component-wise within `1e-9`.
   - `geometric_product(translator(a), translator(b))` equals
     `geometric_product(translator(b), translator(a))` byte-equal.

### Fixed test cases

```text
Subtract cases (a, b):
  (0, 0), (5, 0), (0, 5),
  (10, 3), (3, 10),
  (1.5, 0.5), (0.25, 0.75),
  (-5, 3), (5, -3),
  (-2, -3), (100, 1)

Group cases (a, b) for families 7-9:
  (0, 0), (1, 0), (0, 1),
  (1, 1), (-1, 1), (3, 4),
  (0.5, 0.5), (-2.5, 2.5),
  (100, 1), (1, 100)
```

---

## Non-goals

Out of scope for this ADR (every item below is for a follow-on):

- No `multiply`, `divide`, or any non-additive operation. `multiply` is
  ADR-0141 territory — the dilator construction is structurally different
  and concentrates the next risk.
- No `MathProblemGraph` consumer. No `PropositionGraph` construction.
  No `CognitiveTurnPipeline` integration.
- No GSM8K case routed.
- No pack changes.
- No proof of associativity beyond what binary-composition tests implicitly
  cover. (Three-element associativity `T_a · (T_b · T_c) = (T_a · T_b) · T_c`
  would be a clean addition but is redundant given commutativity + closure
  into the sum.)
- No "inverse element" exposed as a separate primitive. `subtract(b)` is
  the inverse of `add(b)`; the engine does not need a named "inverse"
  function until ADR-0143 (compare) or later.

Engine B (`math_solver.py`, candidate-graph parser, S.x corridor) remains
unchanged. The 3/50 GSM8K admission set is preserved.

---

## Rationale

**Why test the group axioms here rather than later?**

The thesis says the engine decodes what is already there. The additive
group on the real line *is* already there — it's a mathematical fact
independent of CORE. If `translator()` faithfully decodes addition, then
the group axioms must hold automatically. Testing them isn't "adding a
feature"; it's *verifying that what we think we decoded is what we
actually decoded*.

If the inverse composition test (family 7) fails, the construction is
not decoding addition — it's decoding something that looks like addition
on small cases but doesn't form a group. That would invalidate ADR-0139
retroactively and pause the lift program.

If commutativity (family 9) fails, the algebra is not decoding scalar
addition — it's decoding some non-abelian operation, which means scalar
arithmetic can't be lifted onto this construction as we assumed.

So families 7-9 are not nice-to-haves. They are the structural
verification that ADR-0139's algebraic claim is actually true at the
*group* level, not just at the *point-pair* level.

**Why subtract, not multiply, as the next step?**

Multiply is structurally different — it's a dilator, not a translator,
and the dilator construction in CGA (`D_s = cosh(α/2) + sinh(α/2)·(n_o ∧ n_inf)`)
sits on a different versor manifold. The closure properties have to be
re-derived. That's the next big risk; doing subtract first locks down
the additive subgroup so multiply has a clean foundation to extend from.

Subtract is also the smallest possible follow-on — same construction,
same module, three new test families. If subtract's spike fails, we
catch the inverse-element failure with a one-line change rather than a
multi-module multiply implementation.

**Why no MathProblemGraph wiring yet?**

Same reason as ADR-0139: the substrate must be proven before integration.
We don't yet know whether `multiply` (the next risk) closes; if it
doesn't, the integration plan changes shape. Wiring `add` and `subtract`
into MathProblemGraph before multiply is tested would couple two
unrelated unknowns.

---

## Risks

Materially smaller than ADR-0139 because most of the load-bearing
algebra is already discharged:

- **The inverse-composition test (family 7) may not hit exact zero.**
  In ADR-0139, `T_t · reverse(T_t) = 1` was exact because of an
  algebraic cancellation `B² = 0`. The composition `T_{-b} · T_b` is a
  different product (`reverse` is not the same as negate). The
  expected residual is bounded by `(geometric_product cancellation
  precision)` at float64. If it lands between `1e-9` and `1e-6`, the
  test passes the versor-condition threshold but suggests the algebra
  isn't *exactly* the additive group. Worth measuring honestly.

- **Commutativity is non-trivial at the multivector level.** Two
  bivectors don't generally commute. `translator(a) · translator(b)`
  multiplied out involves cross-terms; whether those cancel depends
  on the structure of `B_a = a·e1·n_inf` and `B_b = b·e1·n_inf`. They
  do (because both bivectors live in the same 2D subspace spanned by
  `e14` and `e15`, where the algebra reduces to a commuting plane).
  But this is the kind of property that's *true by structure*, not
  by accident — and family 9 is exactly the test that confirms it.

- **`b = 0` edge case.** `translator(0)` should be the scalar 1
  exactly. The construction `1 - 0.5 · (0 · n_inf)` simplifies to `1`
  symbolically, and float arithmetic should reach the same result, but
  family 8's `b = 0` case verifies it explicitly.

---

## Replay & invariants

Same invariants as ADR-0139:

- `versor_condition(T) < 1e-6` for all constructed translators (now
  including negative addends).
- Null inputs to `versor_apply` stay null.
- No new normalization is introduced.
- Float64 end-to-end where precision matters.
- Determinism: same `(a, b)` → identical multivector bytes across runs.

New cross-cutting invariant introduced by this ADR (worth pinning in
the test module): **the additive subgroup of Cl(4,1) translators along
e1 is abelian and closed under composition.** Families 7-9 are the
CI-enforced statement of this invariant.

---

## Sequencing for follow-on

Only if every assertion in this ADR passes:

1. ADR-0141: `multiply` as dilator. Concentrates the next risk.
2. ADR-0142: `Rate` as bivector; `apply_rate` as combined translator-dilator.
3. ADR-0143: `compare_*` at the proposition layer, not the versor layer.
4. ADR-0144: `PropositionGraph` from `MathProblemGraph`.
5. ADR-0145: One GSM8K case routed end-to-end through Engine A.

If any assertion fails — particularly family 7 (inverse) or family 9
(commutativity) — ADR-0139's algebraic claim is invalidated retroactively.
The lift program pauses until the failure mode is documented and a
revised construction is proposed.

---

## Decision summary

Extend `generate/math_versor_arithmetic.py` with one new function
(`subtract`, a one-line delegate to `translator(-b)`). Add one test
module verifying the six ADR-0139 acceptance families against subtract,
plus three new families that test the additive group structure
(inverse, round-trip, commutativity).

Acceptance is binary: every test passes, or the ADR is withdrawn and
ADR-0139's claim is re-examined.
