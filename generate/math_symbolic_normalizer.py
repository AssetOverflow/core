"""ADR-0131.1.B — Deterministic symbolic normalizer for exact polynomials.

Scope:
  - One or more symbolic variables.
  - Exact integer or rational coefficients via fractions.Fraction.
  - Operators: +, -, *, / by numeric constants, ** with non-negative
    integer exponents.
  - Parentheses for grouping.
  - No division by symbolic expressions yet.
  - No transcendental functions.

Two expressions A and B are equivalent iff their canonical polynomial
forms are byte-equal. Refusal is first-class: unsupported input raises
SymbolicError rather than producing a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Final


class SymbolicError(ValueError):
    """Raised on tokens, syntax, or operators the normalizer cannot handle."""


Coeff = Fraction


def _as_fraction(value: int | Fraction) -> Fraction:
    if isinstance(value, bool):
        raise SymbolicError("boolean coefficients are not allowed")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    raise SymbolicError(f"unsupported coefficient type {type(value).__name__}")


def _format_coeff(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class Polynomial:
    """A multivariable exact polynomial in canonical sparse form."""

    terms: dict[tuple[int, ...], int | Fraction]
    variables: tuple[str, ...] = ("x",)

    def __post_init__(self) -> None:
        if not self.variables:
            raise SymbolicError("Polynomial.variables must be non-empty")
        if tuple(sorted(self.variables)) != self.variables:
            raise SymbolicError(f"variables must be sorted; got {self.variables}")
        if len(set(self.variables)) != len(self.variables):
            raise SymbolicError(f"duplicate variables: {self.variables}")
        for v in self.variables:
            if not isinstance(v, str) or not v.isidentifier():
                raise SymbolicError(f"invalid variable name {v!r}")
        clean: dict[tuple[int, ...], Fraction] = {}
        for exps, raw_coef in self.terms.items():
            coef = _as_fraction(raw_coef)
            if coef == 0:
                continue
            if len(exps) != len(self.variables):
                raise SymbolicError(
                    f"exponent tuple length {len(exps)} does not match variables {self.variables}"
                )
            if any((not isinstance(e, int)) or e < 0 for e in exps):
                raise SymbolicError(f"invalid exponent tuple {exps!r}")
            clean[tuple(exps)] = coef
        object.__setattr__(self, "terms", clean)

    @property
    def coefficients(self) -> tuple[int | Fraction, ...]:
        if len(self.variables) != 1:
            raise SymbolicError("coefficients view is univariate-only")
        if not self.terms:
            return ()
        max_exp = max(exps[0] for exps in self.terms)
        out: list[int | Fraction] = [0] * (max_exp + 1)
        for exps, coef in self.terms.items():
            out[exps[0]] = coef.numerator if coef.denominator == 1 else coef
        while out and out[-1] == 0:
            out.pop()
        return tuple(out)

    @property
    def variable(self) -> str:
        if len(self.variables) != 1:
            raise SymbolicError("variable view is univariate-only")
        return self.variables[0]

    def to_canonical_string(self) -> str:
        if not self.terms:
            return "0"
        parts: list[str] = []
        for exps, coef in sorted(self.terms.items(), key=lambda kv: kv[0], reverse=True):
            sign = "+" if coef >= 0 else "-"
            abs_coef = abs(coef)
            monomial_parts: list[str] = []
            for variable, exp in zip(self.variables, exps):
                if exp == 0:
                    continue
                if exp == 1:
                    monomial_parts.append(variable)
                else:
                    monomial_parts.append(f"{variable}^{exp}")
            if monomial_parts:
                mono = "*".join(monomial_parts)
                term = mono if abs_coef == 1 else f"{_format_coeff(abs_coef)}*{mono}"
            else:
                term = _format_coeff(abs_coef)
            if not parts:
                parts.append(term if sign == "+" else f"-{term}")
            else:
                parts.append(f"{sign}{term}")
        return "".join(parts)


_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"\s*(?:(?P<int>\d+)|(?P<ident>[A-Za-z_]\w*)|(?P<op>\*\*|[+\-*/()^]))"
)


def _tokenize(text: str) -> list[tuple[str, str]]:
    pos = 0
    tokens: list[tuple[str, str]] = []
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if m is None or m.end() == pos:
            raise SymbolicError(
                f"unexpected character at position {pos}: {text[pos:pos+10]!r}"
            )
        for kind in ("int", "ident", "op"):
            lex = m.group(kind)
            if lex is not None:
                if kind == "op" and lex == "^":
                    lex = "**"
                tokens.append((kind, lex))
                break
        pos = m.end()
    return tokens


def _infer_variables(tokens: list[tuple[str, str]]) -> tuple[str, ...]:
    names = sorted({lex for kind, lex in tokens if kind == "ident"})
    return tuple(names) if names else ("x",)


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], variables: tuple[str, ...]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._variables = variables

    def _peek(self) -> tuple[str, str] | None:
        return None if self._pos >= len(self._tokens) else self._tokens[self._pos]

    def _consume(self) -> tuple[str, str]:
        if self._pos >= len(self._tokens):
            raise SymbolicError("unexpected end of expression")
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse(self) -> Polynomial:
        result = self._expr()
        if self._pos != len(self._tokens):
            raise SymbolicError(f"unexpected trailing token {self._tokens[self._pos]!r}")
        return result

    def _expr(self) -> Polynomial:
        left = self._term()
        while True:
            tok = self._peek()
            if tok is None or tok[0] != "op" or tok[1] not in ("+", "-"):
                break
            self._consume()
            right = self._term()
            left = _add(left, right) if tok[1] == "+" else _sub(left, right)
        return left

    def _term(self) -> Polynomial:
        left = self._factor()
        while True:
            tok = self._peek()
            if tok is None:
                break
            if tok[0] == "op" and tok[1] == "*":
                self._consume()
                left = _mul(left, self._factor())
                continue
            if tok[0] == "op" and tok[1] == "/":
                self._consume()
                divisor = self._factor()
                left = _div(left, divisor)
                continue
            break
        return left

    def _factor(self) -> Polynomial:
        base = self._unary()
        tok = self._peek()
        if tok is not None and tok == ("op", "**"):
            self._consume()
            exp_poly = self._unary()
            exp_val = _constant_value(exp_poly)
            if exp_val.denominator != 1:
                raise SymbolicError("exponent must be an integer constant")
            exponent = exp_val.numerator
            if exponent < 0:
                raise SymbolicError(f"exponent must be non-negative; got {exponent}")
            return _pow(base, exponent)
        return base

    def _unary(self) -> Polynomial:
        tok = self._peek()
        if tok is not None and tok[0] == "op" and tok[1] in ("+", "-"):
            self._consume()
            inner = self._unary()
            return _neg(inner) if tok[1] == "-" else inner
        return self._atom()

    def _atom(self) -> Polynomial:
        tok = self._consume()
        if tok[0] == "int":
            return _const(Fraction(int(tok[1]), 1), self._variables)
        if tok[0] == "ident":
            if tok[1] not in self._variables:
                raise SymbolicError(f"identifier {tok[1]!r} is outside variable set")
            return _var(tok[1], self._variables)
        if tok == ("op", "("):
            inner = self._expr()
            close = self._consume()
            if close != ("op", ")"):
                raise SymbolicError(f"expected ')'; got {close!r}")
            return inner
        raise SymbolicError(f"unexpected token {tok!r}")


def _zero_key(variables: tuple[str, ...]) -> tuple[int, ...]:
    return (0,) * len(variables)


def _const(value: int | Fraction, variables: tuple[str, ...]) -> Polynomial:
    coef = _as_fraction(value)
    if coef == 0:
        return Polynomial(terms={}, variables=variables)
    return Polynomial(terms={_zero_key(variables): coef}, variables=variables)


def _var(name: str, variables: tuple[str, ...]) -> Polynomial:
    exps = [0] * len(variables)
    exps[variables.index(name)] = 1
    return Polynomial(terms={tuple(exps): Fraction(1, 1)}, variables=variables)


def _constant_value(poly: Polynomial) -> Fraction:
    if not poly.terms:
        return Fraction(0, 1)
    zero_key = _zero_key(poly.variables)
    if set(poly.terms.keys()) == {zero_key}:
        return poly.terms[zero_key]
    raise SymbolicError("expected a constant polynomial")


def _align(poly: Polynomial, variables: tuple[str, ...]) -> Polynomial:
    if poly.variables == variables:
        return poly
    positions = [variables.index(v) for v in poly.variables]
    out: dict[tuple[int, ...], Fraction] = {}
    for exps, coef in poly.terms.items():
        new_exps = [0] * len(variables)
        for old_i, new_i in enumerate(positions):
            new_exps[new_i] = exps[old_i]
        out[tuple(new_exps)] = coef
    return Polynomial(terms=out, variables=variables)


def _common_variables(a: Polynomial, b: Polynomial) -> tuple[str, ...]:
    return tuple(sorted(set(a.variables) | set(b.variables)))


def _add(a: Polynomial, b: Polynomial) -> Polynomial:
    variables = _common_variables(a, b)
    a = _align(a, variables)
    b = _align(b, variables)
    out = dict(a.terms)
    for exps, coef in b.terms.items():
        out[exps] = out.get(exps, Fraction(0, 1)) + coef
        if out[exps] == 0:
            del out[exps]
    return Polynomial(terms=out, variables=variables)


def _neg(a: Polynomial) -> Polynomial:
    return Polynomial(terms={exps: -coef for exps, coef in a.terms.items()}, variables=a.variables)


def _sub(a: Polynomial, b: Polynomial) -> Polynomial:
    return _add(a, _neg(b))


def _mul(a: Polynomial, b: Polynomial) -> Polynomial:
    variables = _common_variables(a, b)
    a = _align(a, variables)
    b = _align(b, variables)
    if not a.terms or not b.terms:
        return Polynomial(terms={}, variables=variables)
    out: dict[tuple[int, ...], Fraction] = {}
    for exps_a, coef_a in a.terms.items():
        for exps_b, coef_b in b.terms.items():
            exps = tuple(x + y for x, y in zip(exps_a, exps_b))
            out[exps] = out.get(exps, Fraction(0, 1)) + coef_a * coef_b
            if out[exps] == 0:
                del out[exps]
    return Polynomial(terms=out, variables=variables)


def _div(a: Polynomial, b: Polynomial) -> Polynomial:
    divisor = _constant_value(b)
    if divisor == 0:
        raise SymbolicError("division by zero")
    return Polynomial(
        terms={exps: coef / divisor for exps, coef in a.terms.items()},
        variables=a.variables,
    )


def _pow(base: Polynomial, exponent: int) -> Polynomial:
    if exponent == 0:
        return _const(1, base.variables)
    result = _const(1, base.variables)
    for _ in range(exponent):
        result = _mul(result, base)
    return result


def normalize(
    expression: str,
    *,
    variable: str | None = None,
    variables: tuple[str, ...] | None = None,
) -> Polynomial:
    """Parse + expand + collect ``expression`` into canonical Polynomial."""
    if not isinstance(expression, str) or not expression.strip():
        raise SymbolicError("empty or non-string expression")
    tokens = _tokenize(expression)
    if not tokens:
        raise SymbolicError("no tokens parsed from expression")
    if variable is not None and variables is not None:
        raise SymbolicError("pass either variable or variables, not both")
    if variables is None:
        variables = (variable,) if variable is not None else _infer_variables(tokens)
    variables = tuple(sorted(variables))
    return _Parser(tokens, variables).parse()


def canonical_string(
    expression: str,
    *,
    variable: str | None = None,
    variables: tuple[str, ...] | None = None,
) -> str:
    return normalize(expression, variable=variable, variables=variables).to_canonical_string()
