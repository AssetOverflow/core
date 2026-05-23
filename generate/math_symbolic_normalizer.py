"""ADR-0131.1 — Deterministic symbolic normalizer for univariate
integer-coefficient polynomials.

Scope (v1, intentionally narrow):
  - Single variable (configurable, default 'x').
  - Integer coefficients only.
  - Operators: +, -, *, ** (positive integer exponents only).
  - Parentheses for grouping.
  - No division (except implicit unary).
  - No transcendental functions, no multi-variable, no rationals.

The normalizer is the load-bearing primitive for the symbolic
equivalence benchmark (ADR-0131 Benchmark 1). Two expressions A and
B are equivalent iff their canonical forms are byte-equal. This is
the CGA exact-recall discriminator framed in algebra.

Determinism guarantees:
  - Pure functions, no global state, no randomness.
  - Same input string → same canonical string, byte-for-byte.
  - Same canonical string → same Polynomial dataclass.
  - Refuses (raises SymbolicError) rather than guessing on
    out-of-scope input (preserves wrong == 0).

Architecture: tokenize → parse to AST → expand + collect → canonical
serialize. Each stage is independently testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final


# ---------------------------------------------------------------------------
# Public errors
# ---------------------------------------------------------------------------

class SymbolicError(ValueError):
    """Raised on tokens, syntax, or operators the normalizer cannot
    deterministically handle. Refusal is first-class — the caller is
    expected to treat this as an explicit refusal, not a wrong answer.
    """


# ---------------------------------------------------------------------------
# Canonical polynomial representation
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Polynomial:
    """A univariate polynomial in canonical form.

    ``coefficients`` is a tuple of integers, index = exponent.
    coefficients[0] = constant term, coefficients[1] = x coefficient,
    coefficients[2] = x^2 coefficient, etc. Trailing zeros are
    stripped; the tuple is empty iff the polynomial is the zero
    polynomial.

    Two Polynomial instances are equal iff their coefficient tuples
    are equal. This is the equivalence relation the benchmark tests.
    """

    coefficients: tuple[int, ...]
    variable: str = "x"

    def __post_init__(self) -> None:
        if not isinstance(self.variable, str) or not self.variable.isidentifier():
            raise SymbolicError(
                f"Polynomial.variable must be a Python identifier; "
                f"got {self.variable!r}"
            )
        if not all(isinstance(c, int) for c in self.coefficients):
            raise SymbolicError(
                "Polynomial.coefficients must all be int "
                "(no float, no bool, no fraction in v1)"
            )
        # Trailing zeros must be stripped at construction; reject
        # non-canonical input loudly so downstream comparison is
        # unambiguous.
        if self.coefficients and self.coefficients[-1] == 0:
            raise SymbolicError(
                f"Polynomial.coefficients must have no trailing zeros; "
                f"got {self.coefficients}"
            )

    def to_canonical_string(self) -> str:
        """Render this polynomial in a single canonical string form.

        Terms are emitted in descending exponent order with explicit
        signs. The zero polynomial is rendered as ``"0"``. This is
        the byte-level comparison key for equivalence.
        """
        if not self.coefficients:
            return "0"
        parts: list[str] = []
        for exp in range(len(self.coefficients) - 1, -1, -1):
            coef = self.coefficients[exp]
            if coef == 0:
                continue
            sign = "+" if coef >= 0 else "-"
            abs_coef = abs(coef)
            if exp == 0:
                term = f"{abs_coef}"
            elif exp == 1:
                term = f"{self.variable}" if abs_coef == 1 else f"{abs_coef}*{self.variable}"
            else:
                term = (
                    f"{self.variable}^{exp}"
                    if abs_coef == 1
                    else f"{abs_coef}*{self.variable}^{exp}"
                )
            if not parts:
                # Leading term: no leading "+" sign.
                parts.append(term if sign == "+" else f"-{term}")
            else:
                parts.append(f"{sign}{term}")
        return "".join(parts)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"\s*(?:(?P<int>\d+)|(?P<ident>[A-Za-z_]\w*)|(?P<op>\*\*|[+\-*()^]))"
)


def _tokenize(text: str) -> list[tuple[str, str]]:
    """Return a list of ``(kind, lexeme)`` tokens.

    Kinds: ``"int"``, ``"ident"``, ``"op"``. The ``"^"`` operator is
    normalized to the canonical Python-style ``"**"`` (both spellings
    accepted on input).
    """
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


# ---------------------------------------------------------------------------
# Recursive-descent parser producing a normalized Polynomial.
#
# Grammar:
#   expr   := term (('+' | '-') term)*
#   term   := factor (('*') factor)*       # implicit '*' between (expr) and ident
#   factor := unary ('**' unary)?
#   unary  := ('+' | '-') unary | atom
#   atom   := INT | IDENT | '(' expr ')'
#
# Each grammar rule returns a Polynomial; addition / multiplication /
# negation / exponentiation are implemented as Polynomial operations.
# This is the "expand + collect" step inlined into parsing.
# ---------------------------------------------------------------------------

class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], variable: str) -> None:
        self._tokens = tokens
        self._pos = 0
        self._variable = variable

    def _peek(self) -> tuple[str, str] | None:
        if self._pos >= len(self._tokens):
            return None
        return self._tokens[self._pos]

    def _consume(self) -> tuple[str, str]:
        if self._pos >= len(self._tokens):
            raise SymbolicError("unexpected end of expression")
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse(self) -> Polynomial:
        result = self._expr()
        if self._pos != len(self._tokens):
            extra = self._tokens[self._pos]
            raise SymbolicError(f"unexpected trailing token {extra!r}")
        return result

    def _expr(self) -> Polynomial:
        left = self._term()
        while True:
            tok = self._peek()
            if tok is None or tok[0] != "op" or tok[1] not in ("+", "-"):
                break
            self._consume()
            right = self._term()
            if tok[1] == "+":
                left = _add(left, right)
            else:
                left = _sub(left, right)
        return left

    def _term(self) -> Polynomial:
        left = self._factor()
        while True:
            tok = self._peek()
            if tok is None:
                break
            # Explicit '*'
            if tok[0] == "op" and tok[1] == "*":
                self._consume()
                right = self._factor()
                left = _mul(left, right)
                continue
            break
        return left

    def _factor(self) -> Polynomial:
        base = self._unary()
        tok = self._peek()
        if tok is not None and tok[0] == "op" and tok[1] == "**":
            self._consume()
            exp_tok = self._unary()
            # Exponent must be a non-negative integer constant polynomial.
            if len(exp_tok.coefficients) > 1:
                raise SymbolicError(
                    "exponent must be a non-negative integer constant; "
                    "got non-constant polynomial"
                )
            exp_val = exp_tok.coefficients[0] if exp_tok.coefficients else 0
            if exp_val < 0:
                raise SymbolicError(
                    f"exponent must be non-negative; got {exp_val}"
                )
            return _pow(base, exp_val)
        return base

    def _unary(self) -> Polynomial:
        tok = self._peek()
        if tok is not None and tok[0] == "op" and tok[1] in ("+", "-"):
            self._consume()
            inner = self._unary()
            if tok[1] == "-":
                return _neg(inner)
            return inner
        return self._atom()

    def _atom(self) -> Polynomial:
        tok = self._consume()
        if tok[0] == "int":
            return _const(int(tok[1]), self._variable)
        if tok[0] == "ident":
            if tok[1] != self._variable:
                raise SymbolicError(
                    f"v1 supports a single variable {self._variable!r}; "
                    f"got identifier {tok[1]!r}"
                )
            return _x(self._variable)
        if tok == ("op", "("):
            inner = self._expr()
            close = self._consume()
            if close != ("op", ")"):
                raise SymbolicError(f"expected ')'; got {close!r}")
            return inner
        raise SymbolicError(f"unexpected token {tok!r}")


# ---------------------------------------------------------------------------
# Polynomial algebra primitives (the actual "expand and collect" engine)
# ---------------------------------------------------------------------------

def _strip_trailing_zeros(coeffs: list[int]) -> tuple[int, ...]:
    while coeffs and coeffs[-1] == 0:
        coeffs.pop()
    return tuple(coeffs)


def _const(value: int, variable: str) -> Polynomial:
    if value == 0:
        return Polynomial(coefficients=(), variable=variable)
    return Polynomial(coefficients=(value,), variable=variable)


def _x(variable: str) -> Polynomial:
    return Polynomial(coefficients=(0, 1), variable=variable)


def _add(a: Polynomial, b: Polynomial) -> Polynomial:
    if a.variable != b.variable:
        raise SymbolicError(
            f"variable mismatch: {a.variable!r} vs {b.variable!r}"
        )
    n = max(len(a.coefficients), len(b.coefficients))
    out = [0] * n
    for i, c in enumerate(a.coefficients):
        out[i] += c
    for i, c in enumerate(b.coefficients):
        out[i] += c
    return Polynomial(
        coefficients=_strip_trailing_zeros(out), variable=a.variable
    )


def _neg(a: Polynomial) -> Polynomial:
    return Polynomial(
        coefficients=tuple(-c for c in a.coefficients), variable=a.variable
    )


def _sub(a: Polynomial, b: Polynomial) -> Polynomial:
    return _add(a, _neg(b))


def _mul(a: Polynomial, b: Polynomial) -> Polynomial:
    if a.variable != b.variable:
        raise SymbolicError(
            f"variable mismatch: {a.variable!r} vs {b.variable!r}"
        )
    if not a.coefficients or not b.coefficients:
        return Polynomial(coefficients=(), variable=a.variable)
    out = [0] * (len(a.coefficients) + len(b.coefficients) - 1)
    for i, ca in enumerate(a.coefficients):
        if ca == 0:
            continue
        for j, cb in enumerate(b.coefficients):
            out[i + j] += ca * cb
    return Polynomial(
        coefficients=_strip_trailing_zeros(out), variable=a.variable
    )


def _pow(base: Polynomial, exponent: int) -> Polynomial:
    if exponent == 0:
        return _const(1, base.variable)
    result = base
    for _ in range(exponent - 1):
        result = _mul(result, base)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize(expression: str, *, variable: str = "x") -> Polynomial:
    """Parse + expand + collect ``expression`` into canonical Polynomial.

    Raises :class:`SymbolicError` on any input the v1 normalizer
    cannot deterministically handle (multi-variable, division,
    non-integer coefficient, unknown identifier, syntax error,
    negative exponent, non-constant exponent).
    """
    if not isinstance(expression, str) or not expression.strip():
        raise SymbolicError("empty or non-string expression")
    tokens = _tokenize(expression)
    if not tokens:
        raise SymbolicError("no tokens parsed from expression")
    return _Parser(tokens, variable).parse()


def canonical_string(expression: str, *, variable: str = "x") -> str:
    """Shortcut: ``normalize(expression).to_canonical_string()``."""
    return normalize(expression, variable=variable).to_canonical_string()
