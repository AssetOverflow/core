"""R2 constraint setup-oracle runner — the RULER, before any reader capability (C2).

There is no R2 reader yet (it lands C5+). This lane validates that the independent gold is
internally coherent and canonicalizes stably: every fixture deserializes into the typed
:class:`ConstraintProblem` IR, its setup signature is deterministic, its taxonomy is closed,
and — for ``solved`` fixtures — the provided multiple-choice key agrees with the gold value.
When the reader lands, a grading lane compares the reader's signature against these same gold
signatures; the solver lane (C3) verifies that each ``solved`` setup actually computes ``gold``.

Exit 0 iff ``invalid == 0``. "Zero capability" is the point: this proves the ruler, not a reader.

Gold fixture ``expect`` taxonomy (closed):
  - ``solved``         — well-formed two-category / two-constraint setup; ``gold`` is the int
                         answer; ``options[answer] == gold`` (coherent key).
  - ``solver_refuses`` — well-formed setup, but unsolvable; ``solver_reason`` says why; no gold.
  - ``reader_refuses`` — incomplete/ambiguous prose the reader must refuse to assemble;
                         ``reader_reason`` says why; no setup fields required, no gold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.constraint_oracle.signature import constraint_setup_signature
from generate.constraint_comprehension.expr import LinearConstraint, LinearExpr
from generate.constraint_comprehension.model import (
    AttributeFact,
    ConstraintProblem,
    ConstraintQuery,
    Unknown,
)

_R2_GOLD_PATH = Path(__file__).resolve().parent / "r2_gold.jsonl"

#: Closed taxonomies. ``READER_REASONS`` grows as reader slices (C6/C8) add coefficient-level
#: refusals (equal coefficients, unit mismatch, …); each addition is ratified with its fixture.
EXPECTATIONS = frozenset({"solved", "solver_refuses", "reader_refuses"})
SOLVER_REASONS = frozenset(
    {"indistinguishable_weights", "non_integer_solution", "negative_solution", "verification_failed"}
)
READER_REASONS = frozenset({"missing_total_count", "missing_weighted_total", "too_many_categories"})
DOMAINS = frozenset({"nonnegative_integer", "integer"})


def _load_r2_gold() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _R2_GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def gold_to_problem(fx: dict[str, Any]) -> ConstraintProblem:
    """Deserialize a gold fixture's setup fields into the typed ConstraintProblem IR.

    Terms arrive as ``[symbol, coefficient]`` pairs (the pinned serialization). Raises the
    standard ``KeyError``/``TypeError``/``ValueError`` on a malformed fixture — the validator
    turns that into an ``invalid`` outcome rather than a crash.
    """
    unknowns = tuple(
        Unknown(u["symbol"], u["entity"], u["unit"], u["domain"]) for u in fx["unknowns"]
    )
    facts = tuple(
        AttributeFact(f["category"], f["measured_unit"], int(f["value"]))
        for f in fx.get("facts", [])
    )
    constraints = tuple(
        LinearConstraint(
            LinearExpr(
                tuple((str(s), int(c)) for s, c in con["terms"]),
                int(con.get("constant", 0)),
            ),
            con["relation"],
            int(con["rhs"]),
        )
        for con in fx["constraints"]
    )
    q = fx["query"]
    return ConstraintProblem(unknowns, facts, constraints, ConstraintQuery(q["symbol"], q["unit"]))


def validate_fixture(fx: dict[str, Any]) -> tuple[str, str | None]:
    """Validate one gold fixture's internal coherence. Returns ``(outcome, reason)`` where
    ``outcome`` is ``"valid"`` or ``"invalid"`` and ``reason`` names the failing check."""
    expect = fx.get("expect")
    if expect not in EXPECTATIONS:
        return "invalid", f"unknown_expect:{expect!r}"

    if expect == "reader_refuses":
        if fx.get("reader_reason") not in READER_REASONS:
            return "invalid", f"unknown_reader_reason:{fx.get('reader_reason')!r}"
        if fx.get("gold") is not None:
            return "invalid", "reader_refuses_has_gold"
        return "valid", None

    # solved | solver_refuses both require a well-formed two-category, two-constraint setup.
    try:
        problem = gold_to_problem(fx)
    except (KeyError, TypeError, ValueError) as exc:
        return "invalid", f"malformed_setup:{exc}"

    symbols = {u.symbol for u in problem.unknowns}
    if len(problem.unknowns) != 2 or len(symbols) != 2:
        return "invalid", "v1_requires_exactly_two_distinct_categories"
    if any(u.domain not in DOMAINS for u in problem.unknowns):
        return "invalid", "bad_domain"
    if len(problem.constraints) != 2:
        return "invalid", "v1_requires_exactly_two_constraints"
    if any(sym not in symbols for c in problem.constraints for sym, _ in c.lhs.terms):
        return "invalid", "constraint_references_unknown_symbol"
    if any(f.category not in symbols for f in problem.facts):
        return "invalid", "fact_references_unknown_symbol"
    if problem.query.symbol not in symbols:
        return "invalid", "query_target_not_a_category"
    if constraint_setup_signature(problem) != constraint_setup_signature(problem):
        return "invalid", "nondeterministic_signature"  # pragma: no cover - determinism guard

    if expect == "solver_refuses":
        if fx.get("solver_reason") not in SOLVER_REASONS:
            return "invalid", f"unknown_solver_reason:{fx.get('solver_reason')!r}"
        if fx.get("gold") is not None:
            return "invalid", "solver_refuses_has_gold"
        return "valid", None

    # solved: an integer gold and a coherent multiple-choice key.
    gold = fx.get("gold")
    if not isinstance(gold, int) or isinstance(gold, bool):
        return "invalid", "solved_needs_int_gold"
    options, answer = fx.get("options"), fx.get("answer")
    if not isinstance(options, dict) or answer not in options:
        return "invalid", "missing_or_unlabeled_answer"
    if options[answer] != gold:
        return "invalid", "answer_key_incoherent"
    return "valid", None


def run() -> dict[str, Any]:
    """Validate every R2 gold fixture. Exit-0 criterion for the lane is ``invalid == 0``."""
    fixtures = _load_r2_gold()
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
        "lane": "constraint_oracle_gold_validation",
        "total": len(fixtures),
        "valid": valid,
        "invalid": invalid,
        "by_expect": by_expect,
        "details": details,
    }


def run_reader() -> dict[str, Any]:
    """Grade the R2 reader against the gold (C5–C9).

    Well-formed fixtures (``solved`` / ``solver_refuses``) must read to a setup whose canonical
    signature equals the gold's — ``setup_correct``; a refusal is a miss (``setup_refused``); a
    mismatch is ``setup_wrong`` (the wrong=0-critical count). ``reader_refuses`` fixtures must
    refuse with EXACTLY the gold's ``reader_reason`` (``refused_correct``); a refusal with the
    wrong reason is ``reason_mismatch``; producing a setup at all is ``setup_wrong`` (over-read).
    Exit-0 criterion: ``setup_wrong == 0 and reason_mismatch == 0`` (and, once C9 lands, the
    well-formed fixtures are all correct, so ``setup_refused == 0``).
    """
    from generate.constraint_comprehension.reader import read_constraint_problem
    from generate.meaning_graph.reader import Refusal

    fixtures = _load_r2_gold()
    setup_correct = setup_wrong = setup_refused = refused_correct = reason_mismatch = 0
    details: list[dict[str, Any]] = []
    for fx in fixtures:
        out = read_constraint_problem(fx["text"])
        fid = fx.get("id")
        if fx["expect"] in ("solved", "solver_refuses"):
            if isinstance(out, Refusal):
                setup_refused += 1
                details.append({"id": fid, "outcome": "setup_refused", "reason": out.reason})
            elif constraint_setup_signature(out) == constraint_setup_signature(gold_to_problem(fx)):
                setup_correct += 1
                details.append({"id": fid, "outcome": "setup_correct"})
            else:
                setup_wrong += 1
                details.append(
                    {
                        "id": fid,
                        "outcome": "setup_WRONG",
                        "reader": constraint_setup_signature(out),
                        "gold": constraint_setup_signature(gold_to_problem(fx)),
                    }
                )
        else:  # reader_refuses
            if isinstance(out, Refusal) and out.reason == fx["reader_reason"]:
                refused_correct += 1
                details.append({"id": fid, "outcome": "refused_correct", "reason": out.reason})
            elif isinstance(out, Refusal):
                reason_mismatch += 1
                details.append(
                    {"id": fid, "outcome": "reason_mismatch", "got": out.reason, "want": fx["reader_reason"]}
                )
            else:
                setup_wrong += 1
                details.append({"id": fid, "outcome": "setup_WRONG_over_read"})
    return {
        "lane": "constraint_oracle_reader",
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
    "gold_to_problem",
    "run",
    "run_reader",
    "validate_fixture",
]
