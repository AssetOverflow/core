"""ADR-0177 CP-2a — populate the cue-precision ledger from gold-labelled cases.

The CP-1 ledger (:mod:`generate.cue_precision.ledger`) is the mechanism; this is
the **training step** that gives it signal. For each ``(problem_text, gold)`` case
it gathers the candidate readings the search would consider, labels each by gold,
and folds the per-step ``(cue, op, unit_shape)`` credit into the ledger
(``record_case``). The result is the per-pattern reliability table — the
*measurement* CP-2b/CP-3 will consult before trusting a cue.

Decoupled by construction: the candidate *enumerators* are injected (callables
``problem_text -> Iterable[GroundedDerivation]``), so this module imports nothing
from :mod:`generate.derivation.search` / ``multistep`` and stays as inert and
replay-stable as CP-1. The eval side (:mod:`evals.gsm8k_math...`) wires the real
enumerators to the real cases.

wrong=0 posture: training reads gold (Tier-1, available in the sealed practice
regime only) and writes counts. It changes no search/gate behaviour — the ledger
is still consulted by nobody until CP-2b. Serving stays ``3/47/0``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from generate.cue_precision.ledger import CuePrecisionLedger
from generate.derivation.model import GroundedDerivation

# A candidate enumerator turns a problem into the readings the search considers.
CandidateEnumerator = Callable[[str], Iterable[GroundedDerivation]]

# A training case: the problem text and its gold numeric answer.
TrainingCase = tuple[str, float]


def candidates_for(
    problem_text: str, enumerators: Iterable[CandidateEnumerator]
) -> tuple[GroundedDerivation, ...]:
    """The deduplicated union of every enumerator's candidates, in stable order.

    A reading produced by two enumerators is counted **once** per case (per-step
    credit already counts each pattern occurrence within a chain; double-counting
    the whole chain across enumerators would inflate the same evidence twice).
    Dedup preserves first-seen order, so the fold is deterministic.
    """
    seen: dict[GroundedDerivation, None] = {}
    for enumerate_candidates in enumerators:
        for candidate in enumerate_candidates(problem_text):
            seen.setdefault(candidate, None)
    return tuple(seen)


def train_from_cases(
    cases: Iterable[TrainingCase],
    enumerators: Iterable[CandidateEnumerator],
) -> CuePrecisionLedger:
    """Fold every case's gold-labelled candidates into a fresh ledger.

    Deterministic in ``cases`` order, ``enumerators`` order, and each enumerator's
    own candidate order. A case with no candidate contributes nothing (no refusal
    penalty — the ledger only labels readings, ADR-0177).
    """
    enumerator_tuple = tuple(enumerators)
    ledger = CuePrecisionLedger()
    for problem_text, gold in cases:
        candidates = candidates_for(problem_text, enumerator_tuple)
        if candidates:
            ledger = ledger.record_case(candidates, float(gold))
    return ledger
