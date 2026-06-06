"""Gold lane for E — calibrating the converse-guess per predicate.

The blind converse-solver commits "the converse holds" for every problem; the
``GoldTether`` scores it against the *pack's own* symmetry declaration
(``graph.edge.symmetric`` vs ``graph.edge.directed`` in the relational predicates
lexicon) — a truth source independent of the solver (ADR-0199 L-2). Folding
``run_practice`` over the cases yields a committed ``ClassTally`` per predicate whose
Wilson floor the reliability gate reads: a symmetric predicate earns SERVE; a directed
one does not.

The lane is sized to the SERVE volume floor, not the bar to the lane: a perfect record
clears θ_SERVE=0.99 only at ``n/(n+z²) ≥ 0.99`` (z=2.576) ⇒ ``n ≥ 657``. Deterministic
synthetic entities; no clock, no randomness.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.learning_arena.protocols import BaseAttempt, DomainProblem, Problem
from generate.determine.estimate import converse_class_name

_LEXICON = (
    Path(__file__).resolve().parents[2]
    / "language_packs"
    / "data"
    / "en_core_relational_predicates_v1"
    / "lexicon.jsonl"
)

#: Cases per predicate-class. ≥657 lets a perfect (symmetric) record clear the
#: θ_SERVE=0.99 Wilson floor; the same count on a directed class proves the gate
#: discriminates (its converse-guess is wrong every time → reliability 0).
CASES_PER_CLASS = 660

#: One symmetric + one directed predicate — the minimal discriminating pair. The
#: lane stays small and the falsification is unambiguous (licensed vs refused).
LICENSED_PREDICATE = "sibling_of"  # graph.edge.symmetric → converse true
REFUSED_PREDICATE = "parent_of"  # graph.edge.directed → converse false


def load_symmetric_predicates() -> frozenset[str]:
    """The predicates the pack declares symmetric (the GOLD truth, not the solver's)."""
    out: set[str] = set()
    for line in _LEXICON.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if "graph.edge.symmetric" in entry.get("semantic_domains", []):
            out.add(entry["lemma"])
    return frozenset(out)


class ConverseSolver:
    """The blind converse-guesser as a ``DomainSolver``: always commit "converse holds".

    It reads no symmetry metadata — exactly the serving-side estimator's move
    (``generate.determine.estimate``). Its per-class precision is therefore an honest
    measurement of how often the converse-guess is right, never a peek at the truth.
    """

    domain_id = "determination_estimation"

    def attempt(self, problem: DomainProblem) -> BaseAttempt:
        predicate, a, b = problem.payload["predicate"], problem.payload["a"], problem.payload["b"]
        # Told p(a, b); guess the converse p(b, a) holds. Always commits.
        return BaseAttempt(
            committed=True,
            answer={"predicate": predicate, "subject": b, "object": a, "holds": True},
            reason="estimate_converse",
            case_id=problem.problem_id,
        )


class SymmetryGoldTether:
    """Tier-1 truth: the converse holds iff the pack declares the predicate symmetric."""

    domain_id = "determination_estimation"

    def __init__(self, symmetric: frozenset[str] | None = None) -> None:
        self._symmetric = symmetric if symmetric is not None else load_symmetric_predicates()

    def is_correct(self, attempt: BaseAttempt, problem: DomainProblem) -> bool:
        return bool(attempt.answer["holds"]) is (problem.payload["predicate"] in self._symmetric)

    def gold_answer(self, problem: DomainProblem) -> bool:
        return problem.payload["predicate"] in self._symmetric


def generate_gold_problems(
    predicate: str, n: int = CASES_PER_CLASS
) -> tuple[Problem, ...]:
    """``n`` deterministic converse-query problems for ``predicate``.

    Each is "told ``p(a_i, b_i)``, asked ``p(b_i, a_i)``" over distinct synthetic
    entities, tallied under the predicate's converse class.
    """
    cls = converse_class_name(predicate)
    return tuple(
        Problem(
            problem_id=f"{predicate}-{i:04d}",
            class_name=cls,
            payload={"predicate": predicate, "a": f"{predicate}_a{i}", "b": f"{predicate}_b{i}"},
        )
        for i in range(n)
    )


def all_gold_problems() -> tuple[Problem, ...]:
    """The full lane: the licensed (symmetric) + refused (directed) classes."""
    return generate_gold_problems(LICENSED_PREDICATE) + generate_gold_problems(REFUSED_PREDICATE)


__all__ = [
    "CASES_PER_CLASS",
    "ConverseSolver",
    "LICENSED_PREDICATE",
    "REFUSED_PREDICATE",
    "SymmetryGoldTether",
    "all_gold_problems",
    "generate_gold_problems",
    "load_symmetric_predicates",
]
