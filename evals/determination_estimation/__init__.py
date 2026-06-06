"""Determination-estimation lane (Step E — ESTIMATION).

Calibrates the blind converse-guess (``generate.determine.estimate``) per predicate via
the sealed ADR-0199 practice engine + the ADR-0175 reliability gate: a symmetric
predicate's converse-guess earns the SERVE license; a directed one does not. The
committed ledger this produces is the evidence the ADR-0206 reach bridge consults to
serve a DISCLOSED ``[approximate]`` estimate instead of refusing.
"""

from evals.determination_estimation.gold import (
    CASES_PER_CLASS,
    LICENSED_PREDICATE,
    REFUSED_PREDICATE,
    ConverseSolver,
    SymmetryGoldTether,
    all_gold_problems,
    generate_gold_problems,
    load_symmetric_predicates,
)
from evals.determination_estimation.runner import build_ledger, reliability_at, run

__all__ = [
    "CASES_PER_CLASS",
    "ConverseSolver",
    "LICENSED_PREDICATE",
    "REFUSED_PREDICATE",
    "SymmetryGoldTether",
    "all_gold_problems",
    "build_ledger",
    "generate_gold_problems",
    "load_symmetric_predicates",
    "reliability_at",
    "run",
]
