"""R3 rate setup-oracle runner — the ruler before reader capability (R3b).

Validates that the independent rate gold is internally coherent and deserializes into the typed
``RateProblem`` IR: every fixture matches its closed ``expect`` taxonomy, well-formed setups
construct (exactly one unknown == the query), and the label is **cross-checked against the canonical
arithmetic** (``_canonical_outcome``): a ``solved`` gold must equal the computed answer and agree
with its multiple-choice key, and a ``solver_refuses`` reason must be the genuine reason the setup
refuses. This makes the ruler *meaningfully fail* on a mislabelled fixture (CLAUDE.md
proof-obligation rule) rather than asserting it. ``_canonical_outcome`` validates gold coherence
only; it is not a runtime solver (that is ``generate.rate_comprehension.solver``). The R3 twin of
``evals.constraint_oracle.runner``.

Exit 0 iff ``invalid == 0``.

``expect`` taxonomy (closed):
  - ``solved``         — full single-rate setup; ``gold`` is the int answer; ``options[answer] == gold``.
  - ``solver_refuses`` — full setup, but a non-exact inverse; ``solver_reason`` says why; no gold.
  - ``reader_refuses`` — prose the reader must refuse (missing piece / unit mismatch / combined /
                         temporal); ``reader_reason`` says why; no setup, no gold.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from evals.rate_oracle.signature import rate_setup_signature
from generate.rate_comprehension.conversion import ConversionError, convert_time
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.units import RateUnit, UnitError

_RATE_GOLD_PATH = Path(__file__).resolve().parent / "rate_gold.jsonl"

EXPECTATIONS = frozenset({"solved", "solver_refuses", "reader_refuses"})
SOLVER_REASONS = frozenset({"non_integer_solution"})
#: Closed reader-refusal set the gold uses; extended (with a fixture) as the reader grows.
READER_REASONS = frozenset(
    {
        "rate_unit_mismatch",
        "missing_rate",
        "missing_time",
        "missing_quantity",
        "two_unknowns",
        "combined_rates",
        "temporal_state",
    }
)


def _load_rate_gold() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _RATE_GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def gold_to_problem(fx: dict[str, Any]) -> RateProblem:
    """Deserialize a fixture's setup fields into the typed RateProblem IR."""
    ru = fx["rate_unit"]
    return RateProblem(
        rate_unit=RateUnit(ru["numerator"], ru["denominator"]),
        rate=fx.get("rate"),
        time=fx.get("time"),
        quantity=fx.get("quantity"),
        query=fx["query"],
        time_unit=fx.get("time_unit"),
    )


def _canonical_outcome(problem: RateProblem) -> tuple[str, int | None, str | None]:
    """The canonical answer/refusal for a well-formed single-rate setup, used ONLY to validate gold
    coherence — **not** a runtime solver (that is ``generate.rate_comprehension.solver``). An
    independent reimplementation of the rate algebra (``rate × convert(time)`` and its inverses) so
    the oracle's ``solved`` / ``solver_refuses`` labels can *meaningfully fail* (CLAUDE.md
    proof-obligation rule) rather than being asserted. Returns ``("solved", value, None)`` or
    ``("refused", None, reason)``.
    """
    ru = problem.rate_unit
    try:
        if problem.query == "quantity":
            assert problem.rate is not None and problem.time is not None
            value = Fraction(problem.rate) * convert_time(problem.time, problem.time_unit, ru.denominator)
        elif problem.query == "rate":
            assert problem.quantity is not None and problem.time is not None
            value = Fraction(problem.quantity) / convert_time(problem.time, problem.time_unit, ru.denominator)
        else:  # time — answered in the rate's denominator unit
            assert problem.quantity is not None and problem.rate is not None
            value = Fraction(problem.quantity) / Fraction(problem.rate)
    except ConversionError:
        # A non-convertible duration in a solved/solver_refuses setup is incoherent gold — the
        # convertibility refusal (``rate_unit_mismatch``) is the reader's boundary, not the solver's.
        return "refused", None, "rate_unit_mismatch"
    if value.denominator != 1:
        return "refused", None, "non_integer_solution"
    return "solved", int(value), None


def validate_fixture(fx: dict[str, Any]) -> tuple[str, str | None]:
    """Validate one gold fixture's coherence. Returns ``(outcome, reason)``."""
    expect = fx.get("expect")
    if expect not in EXPECTATIONS:
        return "invalid", f"unknown_expect:{expect!r}"

    if expect == "reader_refuses":
        if fx.get("reader_reason") not in READER_REASONS:
            return "invalid", f"unknown_reader_reason:{fx.get('reader_reason')!r}"
        if fx.get("gold") is not None:
            return "invalid", "reader_refuses_has_gold"
        return "valid", None

    # solved | solver_refuses require a well-formed single-rate setup. (Signature determinism is
    # proven by the model being a pure function over a frozen dataclass — see the oracle tests — not
    # by a runtime self-comparison.)
    try:
        problem = gold_to_problem(fx)
    except (KeyError, TypeError, ValueError, UnitError) as exc:
        return "invalid", f"malformed_setup:{exc}"
    kind, value, reason = _canonical_outcome(problem)

    if expect == "solver_refuses":
        if fx.get("solver_reason") not in SOLVER_REASONS:
            return "invalid", f"unknown_solver_reason:{fx.get('solver_reason')!r}"
        if fx.get("gold") is not None:
            return "invalid", "solver_refuses_has_gold"
        # The label must be the GENUINE reason this setup refuses — not asserted.
        if kind != "refused":
            return "invalid", "solver_refuses_is_actually_solvable"
        if reason != fx["solver_reason"]:
            return "invalid", f"solver_reason_mismatch:expected_{reason}"
        return "valid", None

    # solved: integer gold + coherent multiple-choice key + gold == the canonical computed answer.
    gold = fx.get("gold")
    if not isinstance(gold, int) or isinstance(gold, bool):
        return "invalid", "solved_needs_int_gold"
    options, answer = fx.get("options"), fx.get("answer")
    if not isinstance(options, dict) or answer not in options:
        return "invalid", "missing_or_unlabeled_answer"
    if options[answer] != gold:
        return "invalid", "answer_key_incoherent"
    if kind != "solved":
        return "invalid", "solved_is_not_canonically_solvable"
    if value != gold:
        return "invalid", "gold_does_not_match_computed_answer"
    return "valid", None


def run() -> dict[str, Any]:
    """Validate every R3 rate gold fixture. Exit-0 criterion: ``invalid == 0``."""
    fixtures = _load_rate_gold()
    valid = invalid = 0
    by_expect: dict[str, int] = {}
    details: list[dict[str, Any]] = []
    for fx in fixtures:
        outcome, reason = validate_fixture(fx)
        expect = fx.get("expect", "?")
        by_expect[expect] = by_expect.get(expect, 0) + 1
        if outcome == "valid":
            valid += 1
            details.append({"id": fx.get("id"), "outcome": "valid", "expect": expect})
        else:
            invalid += 1
            details.append({"id": fx.get("id"), "outcome": "invalid", "reason": reason})
    return {
        "lane": "rate_oracle_gold_validation",
        "total": len(fixtures),
        "valid": valid,
        "invalid": invalid,
        "by_expect": by_expect,
        "details": details,
    }


def run_reader() -> dict[str, Any]:
    """Grade the R3 rate reader against the gold (R3d).

    Well-formed fixtures (``solved`` / ``solver_refuses``) must read to a setup whose signature
    equals the gold's (``setup_correct``); a refusal is a miss; a mismatch is ``setup_wrong``.
    ``reader_refuses`` fixtures must refuse with the gold's ``reader_reason`` (``refused_correct``);
    a refusal with the wrong reason is ``reason_mismatch``; producing a setup is ``setup_wrong``.
    Exit-0 criterion: ``setup_wrong == 0 and reason_mismatch == 0``.
    """
    from generate.meaning_graph.reader import Refusal
    from generate.rate_comprehension.reader import read_rate_problem

    fixtures = _load_rate_gold()
    setup_correct = setup_wrong = setup_refused = refused_correct = reason_mismatch = 0
    details: list[dict[str, Any]] = []
    for fx in fixtures:
        out = read_rate_problem(fx["text"])
        fid = fx.get("id")
        if fx["expect"] in ("solved", "solver_refuses"):
            if isinstance(out, Refusal):
                setup_refused += 1
                details.append({"id": fid, "outcome": "setup_refused", "reason": out.reason})
            elif rate_setup_signature(out) == rate_setup_signature(gold_to_problem(fx)):
                setup_correct += 1
                details.append({"id": fid, "outcome": "setup_correct"})
            else:
                setup_wrong += 1
                details.append({"id": fid, "outcome": "setup_WRONG"})
        else:  # reader_refuses
            if isinstance(out, Refusal) and out.reason == fx["reader_reason"]:
                refused_correct += 1
                details.append({"id": fid, "outcome": "refused_correct", "reason": out.reason})
            elif isinstance(out, Refusal):
                reason_mismatch += 1
                details.append({"id": fid, "outcome": "reason_mismatch", "got": out.reason, "want": fx["reader_reason"]})
            else:
                setup_wrong += 1
                details.append({"id": fid, "outcome": "setup_WRONG_over_read"})
    return {
        "lane": "rate_oracle_reader",
        "total": len(fixtures),
        "setup_correct": setup_correct,
        "setup_wrong": setup_wrong,
        "setup_refused": setup_refused,
        "refused_correct": refused_correct,
        "reason_mismatch": reason_mismatch,
        "details": details,
    }


__all__ = [
    "EXPECTATIONS",
    "READER_REASONS",
    "SOLVER_REASONS",
    "_canonical_outcome",
    "gold_to_problem",
    "run",
    "run_reader",
    "validate_fixture",
]
