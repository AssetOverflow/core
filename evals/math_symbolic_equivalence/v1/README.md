# Symbolic Equivalence Benchmark v1 (ADR-0131.1)

The primary discriminator for the `mathematics_logic` expert
promotion under ADR-0131. Tests whether the engine can determine
that two algebraic expressions are *equivalent* under deterministic
polynomial normalization.

## Scope (v1, intentionally narrow)

- **Single variable** (`x` by default).
- **Integer coefficients only.**
- **Operators**: `+`, `-`, `*`, `**`/`^` (positive integer exponents).
- **Parentheses** for grouping.
- **No division** (other than trivial).
- **No transcendental functions, no multi-variable, no rationals.**

The narrowness is by design. The architecture's strength is exact
recall + replay determinism; the benchmark stays inside that
envelope so the result is a clean measure of that strength, not a
proxy for it.

## Pipeline

```
expression_a -> normalize -> canonical_string_a
expression_b -> normalize -> canonical_string_b
verdict      = (canonical_string_a == canonical_string_b)
                 ? EQUIVALENT : NOT_EQUIVALENT
or REFUSED   if either expression is out-of-scope
```

`normalize` is `generate/math_symbolic_normalizer.py`:
recursive-descent parser → polynomial expand-and-collect →
canonical string serialization. `check_equivalence` is
`generate/math_symbolic_equivalence.py`.

## Dataset

`cases.jsonl` ships 30 hand-curated cases covering:

| Category | Count | Examples |
|---|---|---|
| commutative_add / commutative_mul | 2 | `x+1 ≡ 1+x`, `3*x ≡ x*3` |
| distributive | 2 | `2*(x+3) ≡ 2*x+6` |
| square_of_binomial | 3 | `(x+1)^2 ≡ x^2+2*x+1` |
| difference_of_squares | 2 | `(x+1)*(x-1) ≡ x^2-1` |
| cube_of_binomial | 2 | `(x+1)^3 ≡ x^3+3*x^2+3*x+1` |
| foil | 1 | `(x+2)*(x+3) ≡ x^2+5*x+6` |
| collect_like_terms | 2 | `2*x+3*x ≡ 5*x` |
| zero_cancellation | 1 | `x-x ≡ 0` |
| repeated_addition | 1 | `x+x+x+x ≡ 4*x` |
| exponent_combine | 1 | `x^2*x ≡ x^3` |
| product_of_factors | 1 | `x*(x+1)*(x-1) ≡ x^3-x` |
| unary_neg_distribute | 1 | `-(x+1) ≡ -x-1` |
| distributive_collect | 1 | `3*(x+1)+2*(x-1) ≡ 5*x+1` |
| different_constant / coefficient / degree | 3 | `x+1 ≢ x+2` |
| sign_flipped | 2 | `(x+1)^2 ≢ (x-1)^2` |
| distributive_miss / foil_miss / cube_miss | 3 | `2*(x+3) ≢ 2*x+3` |
| out_of_scope_variable | 1 | `x+y` → REFUSED |
| out_of_scope_division | 1 | `x/2` → REFUSED |

20 expected-equivalent + 8 expected-not-equivalent + 2 expected-refused.

## Exit criterion (per ADR-0131 Benchmark 1)

```
correct_rate >= 0.95
wrong         == 0
```

`wrong` is incremented only when the engine produces a *definite*
answer that disagrees with the expected verdict. Refusal on an
out-of-scope case is `correct` when expected; `refused` when
unexpected (which the lane test flags as a normalizer-coverage
regression).

## Running the lane

```bash
python -m evals.math_symbolic_equivalence.v1.runner
# exits 0 if exit criterion passes, 1 otherwise
# writes report.json with counts + per-case verdicts
```

## v1 result (baseline at landing)

```
correct = 30 / 30   (100.0%)
wrong   =  0 / 30   (wrong == 0 invariant satisfied)
refused =  0 / 30   (both expected-refused cases were caught correctly)
exit:   PASSED
```

This is the first benchmark on the `mathematics_logic` lane where
the architecture's structural strengths fully express. The result
is *not* a claim about how hard the cases are; it's a claim about
the architecture-benchmark fit being correct.

## Future expansion (ADR-0131.1.B and beyond)

- Multi-variable polynomials (`x`, `y`, `z` simultaneous).
- Rational coefficients (Fraction).
- Larger dataset (~500 cases per ADR-0131's Benchmark 1 spec).
- Sealed holdout (mirror ADR-0119.7's pyrage X25519 pattern).
- More algebraic identities (Pascal triangle expansions, factoring,
  partial fractions for rationals).

v1 ships the minimum viable substrate. The exit criterion is met;
the dataset can grow without breaking the contract.
