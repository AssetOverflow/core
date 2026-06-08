"""Combined-rate setup-oracle runner — the ruler before reader capability (CMB-a).

Validates that the independent combined-rate gold is internally coherent and deserializes into the
typed ``CombinedRateProblem`` IR: every fixture matches its closed ``expect`` taxonomy, well-formed
setups construct (two explicit rates, exactly the query's slot unknown), and — for ``solved``
fixtures — the multiple-choice key agrees with the gold value. No reader yet (lands CMB-c); this
proves the ruler. The CMB twin of ``evals.rate_oracle.runner``.

Exit 0 iff ``invalid == 0``.

The validator is **non-vacuous**: it cross-checks every ``solved`` gold and every
``solver_refuses`` reason against the canonical arithmetic (``_canonical_outcome``) so a fixture
whose label contradicts its own setup (a positive net rate labelled refused, a wrong gold value,
a non-integer reason on a quantity query) is rejected — the ruler can *meaningfully fail*, not just
assert (CLAUDE.md proof-obligation rule). ``_canonical_outcome`` validates gold coherence only; it
is not a runtime solver (that is CMB-b).

``expect`` taxonomy (closed):
  - ``solved``         — full combined-rate setup; ``gold`` is the int answer; ``options[answer] == gold``
                         **and** ``gold`` equals the canonical computed answer.
  - ``solver_refuses`` — full, well-formed setup whose canonical outcome is a refusal for exactly
                         the stated ``solver_reason`` (non-positive net rate / non-exact division); no gold.
  - ``reader_refuses`` — prose the reader must refuse (mismatched units / ambiguous combine mode /
                         missing second rate / >=3 rates / reciprocal or clock forms / not
                         combined-rate-shaped); ``reader_reason`` says why; no setup, no gold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generate.combined_rate_comprehension.model import CombinedRateProblem
from generate.combined_rate_comprehension.units import RateUnit, UnitError

_GOLD_PATH = Path(__file__).resolve().parent / "combined_rate_gold.jsonl"

EXPECTATIONS = frozenset({"solved", "solver_refuses", "reader_refuses"})
COMBINE_MODES = frozenset({"sum", "difference"})
QUERIES = frozenset({"quantity", "time", "effective_rate"})
SOLVER_REASONS = frozenset({"non_positive_net_rate", "non_integer_solution"})
#: Closed reader-refusal set the gold uses; extended (with a fixture) as the reader grows.
#: ``not_combined_rate_shaped`` is the hygiene "not my domain" reason (maps to the ``input_shape``
#: family in CMB-d); the rest are substantive combined-rate boundaries.
READER_REASONS = frozenset(
    {
        "rate_unit_mismatch",
        "combine_mode_ambiguous",
        "missing_second_rate",
        "three_or_more_rates",
        "reciprocal_work_rate_deferred",
        "clock_interval_deferred",
        "not_combined_rate_shaped",
    }
)


def _load_combined_rate_gold() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def gold_to_problem(fx: dict[str, Any]) -> CombinedRateProblem:
    """Deserialize a fixture's setup fields into the typed CombinedRateProblem IR."""
    ru = fx["rate_unit"]
    return CombinedRateProblem(
        rate_a=fx.get("rate_a"),
        rate_b=fx.get("rate_b"),
        rate_unit=RateUnit(ru["numerator"], ru["denominator"]),
        combine_mode=fx["combine_mode"],
        time=fx.get("time"),
        quantity=fx.get("quantity"),
        query=fx["query"],
        time_unit=fx.get("time_unit"),
    )


def _canonical_outcome(problem: CombinedRateProblem) -> tuple[str, int | None, str | None]:
    """The canonical answer/refusal for a well-formed setup, used ONLY to validate gold coherence.

    This is **not** a runtime solver (that is CMB-b) and not a runtime decode path — it is the
    ruler checking its own gold, so the oracle's ``solved`` / ``solver_refuses`` labels can
    *meaningfully fail* (CLAUDE.md proof-obligation rule) rather than being asserted. Returns
    ``("solved", value, None)`` or ``("refused", None, reason)`` with ``reason`` in
    :data:`SOLVER_REASONS`.

    - ``effective_rate`` query: the net rate is well-defined even when ``<= 0`` (a net-draining
      tank) — answered, never refused.
    - ``quantity`` / ``time`` queries: a non-positive net rate cannot accumulate or finish ->
      ``non_positive_net_rate`` (this also guards the ``eff == 0`` time query from dividing by 0).
    - ``time`` query: an exact integer or ``non_integer_solution`` (never rounds). ``quantity``
      queries are ``eff * time`` and are always integral, so they never refuse for non-integrality.
    """
    eff = problem.effective_rate
    if problem.query == "effective_rate":
        return "solved", eff, None
    if eff <= 0:
        return "refused", None, "non_positive_net_rate"
    if problem.query == "quantity":
        assert problem.time is not None  # guaranteed by the model's per-query slot guard
        return "solved", eff * problem.time, None
    # query == "time": quantity is the known (model guard); exact integer or refuse.
    assert problem.quantity is not None
    if problem.quantity % eff != 0:
        return "refused", None, "non_integer_solution"
    return "solved", problem.quantity // eff, None


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

    # solved | solver_refuses require a well-formed combined-rate setup. (Signature determinism is
    # proven by the model being a pure function over a frozen dataclass — see the oracle tests —
    # not by a runtime self-comparison.)
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
        # The label must be the GENUINE reason this setup refuses — not asserted. A positive,
        # exactly-solvable setup mislabeled solver_refuses, or the wrong refusal reason, is invalid.
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
    """Validate every combined-rate gold fixture. Exit-0 criterion: ``invalid == 0``."""
    fixtures = _load_combined_rate_gold()
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
        "lane": "combined_rate_oracle_gold_validation",
        "total": len(fixtures),
        "valid": valid,
        "invalid": invalid,
        "by_expect": by_expect,
        "details": details,
    }


def run_solver() -> dict[str, Any]:
    """Grade the CMB solver against the gold setups (CMB-b).

    For every fixture with a setup (``solved`` / ``solver_refuses``), solve the gold setup and
    compare to the gold label: a ``solved`` fixture must produce the gold int; a ``solver_refuses``
    fixture must produce a ``Refusal`` carrying the gold ``solver_reason``. ``reader_refuses``
    fixtures have no setup and are skipped (the reader's lane, CMB-c). This grades the runtime
    solver against the *committed* gold values (not against ``_canonical_outcome``). Note both the
    solver and ``_canonical_outcome`` delegate net-rate arithmetic to ``model.effective_rate``, so
    the hand-computed literal tests — not path-independence — are the anchor against a shared
    ``effective_rate`` bug. Exit-0 criterion: ``solved_wrong == 0 and refuse_wrong == 0``.
    """
    from generate.combined_rate_comprehension.solver import solve_combined_rate
    from generate.meaning_graph.reader import Refusal

    fixtures = _load_combined_rate_gold()
    solved_correct = solved_wrong = refuse_correct = refuse_wrong = skipped = 0
    details: list[dict[str, Any]] = []
    for fx in fixtures:
        fid = fx.get("id")
        if fx["expect"] == "reader_refuses":
            skipped += 1
            continue
        out = solve_combined_rate(gold_to_problem(fx))
        if fx["expect"] == "solved":
            if not isinstance(out, Refusal) and out == fx["gold"]:
                solved_correct += 1
                details.append({"id": fid, "outcome": "solved_correct"})
            else:
                solved_wrong += 1
                details.append({"id": fid, "outcome": "solved_WRONG", "got": str(out), "want": fx["gold"]})
        else:  # solver_refuses
            if isinstance(out, Refusal) and out.reason == fx["solver_reason"]:
                refuse_correct += 1
                details.append({"id": fid, "outcome": "refuse_correct", "reason": out.reason})
            else:
                refuse_wrong += 1
                details.append({"id": fid, "outcome": "refuse_WRONG", "got": str(out), "want": fx["solver_reason"]})
    return {
        "lane": "combined_rate_oracle_solver",
        "total": len(fixtures),
        "solved_correct": solved_correct,
        "solved_wrong": solved_wrong,
        "refuse_correct": refuse_correct,
        "refuse_wrong": refuse_wrong,
        "skipped_reader_refuses": skipped,
        "details": details,
    }


__all__ = [
    "COMBINE_MODES",
    "EXPECTATIONS",
    "QUERIES",
    "READER_REASONS",
    "SOLVER_REASONS",
    "_canonical_outcome",
    "_load_combined_rate_gold",
    "gold_to_problem",
    "run",
    "run_solver",
    "validate_fixture",
]
