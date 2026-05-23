"""ADR-0131.1.B — Deterministic symbolic normalizer for integer polynomials.

Scope:
  - One or more symbolic variables.
  - Integer coefficients only.
  - Operators: +, -, *, ** (positive integer exponents only).
  - Parentheses for grouping.
  - No division.
  - No transcendental functions, no rational coefficients.

Two expressions A and B are equivalent iff their canonical polynomial
forms are byte-equal. Refusal is first-class: unsupported input raises
SymbolicError rather than producing a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final


class SymbolicError(ValueError):
    """Raised on tokens, syntax, or operators the normalizer cannot handle."""


@dataclass(frozen=True, slots=True)
class Polynomial:
    """A multivariable integer polynomial in canonical sparse form.

    ``terms`` maps exponent tuples to integer coefficients. The exponent
    tuple length must equal ``len(variables)``. Variables are sorted and
    stable; term serialization uses lexicographic descending exponent order.
    The zero polynomial has an empty terms mapping.
    """

    terms: dict[tuple[int, ...], int]
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
        clean: dict[tuple[int, ...], int] = {}
        for exps, coef in self.terms.items():
            if not isinstance(coef, int) or isinstance(coef, bool):
                raise SymbolicError("coefficients must be integer values")
            if coef == 0:
                continue
            if len(exps) != len(self.variables):
                raise SymbolicError(
                    f"exponent tuple length {len(exps)} does not match "
                    f"variables {self.variables}"
                )
            if any((not isinstance(e, int)) or e < 0 for e in exps):
                raise SymbolicError(f"invalid exponent tuple {exps!r}")
            clean[tuple(exps)] = coef
        object.__setattr__(self, "terms", clean)

    @property
    def coefficients(self) -> tuple[int, ...]:
        """Compatibility view for univariate callers/tests.

        For a univariate polynomial, returns the old coefficient tuple where
        index = exponent. For multivariable polynomials this property refuses
        because no single coefficient tuple can represent the expression.
        """
        if len(self.variables) != 1:
            raise SymbolicError("coefficients view is univariate-only")
        if not self.terms:
            return ()
        max_exp = max(exps[0] for exps in self.terms)
        out = [0] * (max_exp + 1)
        for exps, coef in self.terms.items():
            out[exps[0]] = coef
        while out and out[-1] == 0:
            out.pop()
        return tuple(out)

    @property
    def variable(self) -> str:
        """Compatibility view for univariate callers/tests."""
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
                term = mono if abs_coef == 1 else f"{abs_coef}*{mono}"
            else:
                term = str(abs_coef)
            if not parts:
                parts.append(term if sign == "+" else f"-{term}")
            else:
                parts.append(f"{sign}{term}")
        return "".join(parts)


_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"\s*(?:(?P<int>\d+)|(?P<ident>[A-Za-z_]\w*)|(?P<op>\*\*|[+\-*()^]))"
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
    if not names:
        return ("x",)
    return tuple(names)


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
            break
        return left

    def _factor(self) -> Polynomial:
        base = self._unary()
        tok = self._peek()
        if tok is not None and tok == ("op", "**"):
            self._consume()
            exp_poly = self._unary()
            if len(exp_poly.terms) > 1:
                raise SymbolicError("exponent must be a non-negative integer constant")
            zero_key = (0,) * len(exp_poly.variables)
            exp_val = exp_poly.terms.get(zero_key, 0) if exp_poly.terms else 0
            if any(any(e != 0 for e in exps) for exps in exp_poly.terms):
                raise SymbolicError("exponent must be a constant polynomial")
            if exp_val < 0:
                raise SymbolicError(f"exponent must be non-negative; got {exp_val}")
            return _pow(base, exp_val)
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
            return _const(int(tok[1]), self._variables)
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


def _const(value: int, variables: tuple[str, ...]) -> Polynomial:
    if value == 0:
        return Polynomial(terms={}, variables=variables)
    return Polynomial(terms={_zero_key(variables): value}, variables=variables)


def _var(name: str, variables: tuple[str, ...]) -> Polynomial:
    exps = [0] * len(variables)
    exps[variables.index(name)] = 1
    return Polynomial(terms={tuple(exps): 1}, variables=variables)


def _align(poly: Polynomial, variables: tuple[str, ...]) -> Polynomial:
    if poly.variables == variables:
        return poly
    positions = [variables.index(v) for v in poly.variables]
    out: dict[tuple[int, ...], int] = {}
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
        out[exps] = out.get(exps, 0) + coef
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
    out: dict[tuple[int, ...], int] = {}
    for exps_a, coef_a in a.terms.items():
        for exps_b, coef_b in b.terms.items():
            exps = tuple(x + y for x, y in zip(exps_a, exps_b))
            out[exps] = out.get(exps, 0) + coef_a * coef_b
            if out[exps] == 0:
                del out[exps]
    return Polynomial(terms=out, variables=variables)


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
    """Parse + expand + collect ``expression`` into canonical Polynomial.

    ``variable`` is retained for backward compatibility. If supplied, the
    expression must use only that single variable. New callers should prefer
    ``variables`` or allow the normalizer to infer variables from identifiers.
    """
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
