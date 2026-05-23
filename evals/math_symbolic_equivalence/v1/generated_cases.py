"""ADR-0131.1.B — deterministic generated symbolic-equivalence cases.

This module expands the symbolic-equivalence lane without introducing
runtime randomness. Cases are generated from a pinned integer seed and a
closed set of polynomial/metamorphic transforms.

The generated corpus deliberately stays inside the ADR-0131.1 v1
normalizer scope (single variable, integer coefficients, polynomial
operators only). It is not a substitute for the later multi-variable /
rational / sealed-holdout expansion. Its purpose is to harden Benchmark
1 against a tiny hand-curated-only dataset.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Final, Iterable


SEED: Final[int] = 131101
GENERATED_CASE_COUNT: Final[int] = 120
VARIABLE: Final[str] = "x"


@dataclass(frozen=True, slots=True)
class GeneratedCase:
    case_id: str
    expression_a: str
    expression_b: str
    expected: str
    category: str
    provenance: str

    def as_dict(self) -> dict[str, str]:
        return {
            "case_id": self.case_id,
            "expression_a": self.expression_a,
            "expression_b": self.expression_b,
            "expected": self.expected,
            "category": self.category,
            "provenance": self.provenance,
        }


def _coef(rng: random.Random, *, allow_zero: bool = False) -> int:
    choices = list(range(-5, 6))
    if not allow_zero:
        choices.remove(0)
    return rng.choice(choices)


def _linear(rng: random.Random) -> tuple[str, int, int]:
    """Return (expr, a, b) for a*x + b."""
    a = _coef(rng)
    b = _coef(rng, allow_zero=True)
    parts: list[str] = []
    if a == 1:
        parts.append("x")
    elif a == -1:
        parts.append("-x")
    else:
        parts.append(f"{a}*x")
    if b > 0:
        parts.append(f"+{b}")
    elif b < 0:
        parts.append(str(b))
    return "".join(parts), a, b


def _expanded_square(a: int, b: int) -> str:
    # (a*x+b)^2 = a^2*x^2 + 2ab*x + b^2
    return _poly_to_expr({2: a * a, 1: 2 * a * b, 0: b * b})


def _expanded_product(a: int, b: int, c: int, d: int) -> str:
    # (a*x+b)(c*x+d) = ac*x^2 + (ad+bc)x + bd
    return _poly_to_expr({2: a * c, 1: a * d + b * c, 0: b * d})


def _poly_to_expr(terms: dict[int, int]) -> str:
    """Serialize sparse exponent->coefficient map to parser-compatible expr.

    This is intentionally not the same as the normalizer's canonical string;
    it emits a readable expression for generated corpus cases.
    """
    parts: list[str] = []
    for exp in sorted(terms.keys(), reverse=True):
        coef = terms[exp]
        if coef == 0:
            continue
        sign = "+" if coef > 0 else "-"
        abs_coef = abs(coef)
        if exp == 0:
            term = str(abs_coef)
        elif exp == 1:
            term = "x" if abs_coef == 1 else f"{abs_coef}*x"
        else:
            term = f"x^{exp}" if abs_coef == 1 else f"{abs_coef}*x^{exp}"
        if not parts:
            parts.append(term if sign == "+" else f"-{term}")
        else:
            parts.append(f" {sign} {term}")
    return "0" if not parts else "".join(parts)


def _wrap_add_zero(expr: str, rng: random.Random) -> str:
    z = rng.choice(["0", "x-x", "2*x-2*x", "3-3"])
    return f"({expr}) + ({z})"


def _wrap_mul_one(expr: str, rng: random.Random) -> str:
    one = rng.choice(["1", "x^0", "(2-1)", "(3/3)"])
    # v1 does not support division, so avoid (3/3) until rational support.
    if "/" in one:
        one = "1"
    return f"({expr}) * ({one})"


def _equivalent_cases(rng: random.Random) -> Iterable[GeneratedCase]:
    idx = 1

    # 40 square-of-linear cases.
    for _ in range(40):
        lin, a, b = _linear(rng)
        yield GeneratedCase(
            case_id=f"sym-eq-gen-v1-{idx:04d}",
            expression_a=f"({lin})^2",
            expression_b=_expanded_square(a, b),
            expected="equivalent",
            category="generated_square_of_linear",
            provenance=f"adr-0131.1b:generated:seed={SEED}",
        )
        idx += 1

    # 40 product-of-linears cases.
    for _ in range(40):
        left, a, b = _linear(rng)
        right, c, d = _linear(rng)
        yield GeneratedCase(
            case_id=f"sym-eq-gen-v1-{idx:04d}",
            expression_a=f"({left})*({right})",
            expression_b=_expanded_product(a, b, c, d),
            expected="equivalent",
            category="generated_product_of_linears",
            provenance=f"adr-0131.1b:generated:seed={SEED}",
        )
        idx += 1

    # 20 add-zero metamorphic cases.
    for _ in range(20):
        lin, _, _ = _linear(rng)
        yield GeneratedCase(
            case_id=f"sym-eq-gen-v1-{idx:04d}",
            expression_a=_wrap_add_zero(lin, rng),
            expression_b=lin,
            expected="equivalent",
            category="generated_metamorphic_add_zero",
            provenance=f"adr-0131.1b:generated:seed={SEED}",
        )
        idx += 1

    # 20 multiply-one metamorphic cases.
    for _ in range(20):
        lin, _, _ = _linear(rng)
        yield GeneratedCase(
            case_id=f"sym-eq-gen-v1-{idx:04d}",
            expression_a=_wrap_mul_one(lin, rng),
            expression_b=lin,
            expected="equivalent",
            category="generated_metamorphic_mul_one",
            provenance=f"adr-0131.1b:generated:seed={SEED}",
        )
        idx += 1


def _not_equivalent_cases(rng: random.Random, start_idx: int) -> Iterable[GeneratedCase]:
    # 30 near-miss cases. Each mutates a correct expansion by +1 in the
    # constant term, creating a definite non-equivalence without leaving scope.
    idx = start_idx
    for _ in range(30):
        left, a, b = _linear(rng)
        right, c, d = _linear(rng)
        terms = {2: a * c, 1: a * d + b * c, 0: b * d + 1}
        yield GeneratedCase(
            case_id=f"sym-eq-gen-v1-{idx:04d}",
            expression_a=f"({left})*({right})",
            expression_b=_poly_to_expr(terms),
            expected="not_equivalent",
            category="generated_near_miss_constant",
            provenance=f"adr-0131.1b:generated:seed={SEED}",
        )
        idx += 1


def _refusal_cases(start_idx: int) -> Iterable[GeneratedCase]:
    scope_expanded = [
        ("x + y", "x + 1", "generated_multivariable_distinct"),
        ("x / 2", "x", "generated_constant_denominator_distinct"),
    ]
    templates = [
        ("sin(x)", "x", "generated_refusal_function"),
        ("x^-1", "1", "generated_refusal_negative_exponent"),
        ("x +", "x", "generated_refusal_malformed"),
    ]
    idx = start_idx
    for expr_a, expr_b, category in scope_expanded:
        yield GeneratedCase(
            case_id=f"sym-eq-gen-v1-{idx:04d}",
            expression_a=expr_a,
            expression_b=expr_b,
            expected="not_equivalent",
            category=category,
            provenance=f"adr-0131.1b:generated:seed={SEED}:scope-expanded",
        )
        idx += 1
    for expr_a, expr_b, category in templates:
        yield GeneratedCase(
            case_id=f"sym-eq-gen-v1-{idx:04d}",
            expression_a=expr_a,
            expression_b=expr_b,
            expected="refused",
            category=category,
            provenance=f"adr-0131.1b:generated:seed={SEED}:adversarial",
        )
        idx += 1


def build_generated_cases() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    cases = list(_equivalent_cases(rng))
    cases.extend(_not_equivalent_cases(rng, len(cases) + 1))
    cases.extend(_refusal_cases(len(cases) + 1))
    return [c.as_dict() for c in cases]


if __name__ == "__main__":
    import json
    import sys

    for case in build_generated_cases():
        sys.stdout.write(json.dumps(case, sort_keys=True) + "\n")
