"""Deterministic generator for the deductive-logic lane.

Produces RuleTaker-style propositional problems — base **facts** plus implication
**rules** (conjunctive antecedent → literal consequent) plus a literal **query** —
with the gold answer computed by the *independent* truth-table oracle
(:mod:`evals.deductive_logic.oracle`), never by the engine under test.

Determinism: a fixed-seed ``random.Random`` per split, so the committed
``cases.jsonl`` is exactly reproducible. Splits use disjoint seeds. Inconsistent
premise sets (oracle → ``refused``) are discarded, so every emitted case has a
definite ``entailed`` / ``refuted`` / ``unknown`` gold — the engine is scored on
producing the right *deduction*, with ``wrong=0`` as the floor.

Atom counts are kept small (≤ 7) so the oracle's 2^k enumeration is cheap and the
ROBDD never approaches its node budget.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Final

from evals.deductive_logic.oracle import REFUSED, oracle_entailment

_ATOMS: Final[tuple[str, ...]] = ("a", "b", "c", "d", "e", "f", "g")


def _literal(rng: random.Random, atom: str) -> str:
    return atom if rng.random() < 0.5 else f"~{atom}"


def _make_case(rng: random.Random, case_id: str) -> dict | None:
    k = rng.randint(4, len(_ATOMS))
    atoms = rng.sample(_ATOMS, k)

    premises: list[str] = []

    # Base facts: assert a few literals (kept distinct atoms).
    n_facts = rng.randint(1, max(1, k // 2))
    fact_atoms = rng.sample(atoms, n_facts)
    for at in fact_atoms:
        premises.append(_literal(rng, at))

    # Implication rules: (L1 & ... ) -> Lc. Bias antecedents toward earlier atoms
    # and consequents toward later atoms so multi-hop chains form.
    n_rules = rng.randint(2, 5)
    for _ in range(n_rules):
        body_size = rng.randint(1, 2)
        body_atoms = rng.sample(atoms, min(body_size, k))
        body = " & ".join(_literal(rng, at) for at in body_atoms)
        head_atom = rng.choice(atoms)
        head = _literal(rng, head_atom)
        premises.append(f"({body}) -> {head}")

    query = _literal(rng, rng.choice(atoms))

    gold = oracle_entailment(tuple(premises), query)
    if gold == REFUSED:
        return None  # inconsistent premises — discard; keep only definite golds

    return {"id": case_id, "premises": premises, "query": query, "gold": gold}


def generate(seed: int, n: int, prefix: str) -> list[dict]:
    """Generate ``n`` consistent cases deterministically from ``seed``."""
    rng = random.Random(seed)
    cases: list[dict] = []
    attempts = 0
    while len(cases) < n:
        attempts += 1
        case = _make_case(rng, f"{prefix}-{len(cases):04d}")
        if case is not None:
            cases.append(case)
        if attempts > n * 50:  # pragma: no cover - safety valve
            raise RuntimeError("generator could not reach target count")
    return cases


def _write(path: Path, cases: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for case in cases:
            fh.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    _write(root / "dev" / "cases.jsonl", generate(20260604, 200, "dl-dev-v1"))
    _write(root / "holdout" / "v1" / "cases.jsonl", generate(70260604, 500, "dl-holdout-v1"))
    print("generated dev=200 holdout=500")
