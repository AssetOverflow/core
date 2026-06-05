"""Independent categorical-syllogism oracle for the staged Phase 2 gold lane.

The oracle reads structured categorical propositions, not text. It evaluates
validity by brute-force finite-model enumeration over a small domain. This is
intentionally simple and independent of any future comprehension reader.
"""

from __future__ import annotations

from itertools import product
from typing import Any, Final


class OracleError(ValueError):
    """Malformed or out-of-grammar case; the oracle refuses, never guesses."""


_FORMS: Final[frozenset[str]] = frozenset({"A", "E", "I", "O"})


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise OracleError(f"{label} must be a non-empty string: {value!r}")
    return value


def _proposition(raw: object, terms: set[str]) -> tuple[str, str, str]:
    if not isinstance(raw, dict):
        raise OracleError(f"proposition must be an object: {raw!r}")
    form = _require_str(raw.get("form"), "form")
    subject = _require_str(raw.get("subject"), "subject")
    predicate = _require_str(raw.get("predicate"), "predicate")
    if form not in _FORMS:
        raise OracleError(f"unsupported categorical form: {form!r}")
    if subject not in terms or predicate not in terms:
        raise OracleError(f"proposition names unknown term: {raw!r}")
    if subject == predicate:
        raise OracleError("subject and predicate must be distinct")
    return form, subject, predicate


def _holds(prop: tuple[str, str, str], env: dict[str, frozenset[int]]) -> bool:
    form, subject, predicate = prop
    s = env[subject]
    p = env[predicate]
    if form == "A":
        return s <= p
    if form == "E":
        return not (s & p)
    if form == "I":
        return bool(s & p)
    if form == "O":
        return bool(s - p)
    raise OracleError(f"unknown form: {form!r}")  # pragma: no cover


def oracle_answer(structure: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    """Return ``{"valid": bool, "conclusion": conclusion-or-None}``.

    Premises with no satisfying model are refused as inconsistent; otherwise a
    candidate conclusion is valid iff it holds in every model of the premises.
    """
    raw_terms = structure.get("terms")
    if not isinstance(raw_terms, list) or len(raw_terms) < 2:
        raise OracleError("terms must be a list of at least two term names")
    terms = [_require_str(t, "term") for t in raw_terms]
    if len(set(terms)) != len(terms):
        raise OracleError("terms contains duplicates")
    term_set = set(terms)

    raw_premises = structure.get("premises")
    if not isinstance(raw_premises, list) or not raw_premises:
        raise OracleError("premises must be a non-empty list")
    premises = [_proposition(p, term_set) for p in raw_premises]

    if query.get("kind") != "validity":
        raise OracleError(f"unsupported query kind: {query.get('kind')!r}")
    conclusion_payload = query.get("conclusion")
    conclusion = _proposition(conclusion_payload, term_set)

    domain = tuple(range(int(structure.get("domain_size", 3))))
    if not domain:
        raise OracleError("domain_size must be positive")
    subsets = [
        frozenset(i for i, include in enumerate(bits) if include)
        for bits in product((False, True), repeat=len(domain))
    ]

    models = 0
    conclusion_true = 0
    for assignment in product(subsets, repeat=len(terms)):
        env = dict(zip(terms, assignment))
        if all(_holds(premise, env) for premise in premises):
            models += 1
            if _holds(conclusion, env):
                conclusion_true += 1

    if models == 0:
        raise OracleError("premises have no satisfying model")
    valid = conclusion_true == models
    return {
        "valid": valid,
        "conclusion": dict(conclusion_payload) if valid else None,
    }

