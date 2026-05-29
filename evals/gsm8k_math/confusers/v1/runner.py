"""ADR-0163-F2 — the confuser corpus runner (a discrimination probe).

Scored the **opposite way from a coverage lane** (see
``docs/decisions/ADR-0163-F2-confuser-corpus-spec.md``): the headline is
``wrong == 0`` on confusers — a confuser *answered* is a defect regardless of its
value — plus **pair-consistency** (a reader that solves a twin but also commits an
answer on its confuser is surface-matching, not reading). ``refused`` on confusers
is the honest frontier, never optimised down.

The probe runs the realistic sealed *attempt*: the composers a refused case is
allowed to try, in fixed order (accumulation, then the multiplicative product, then
the multi-step chain); the first that returns a resolution is the engine's answer.
This is exactly where the overfitting misfires live (the templated lane hid them).

Deterministic; sealed (serving is never invoked here).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from generate.derivation.pool import resolve_pooled

_CASES_PATH: Final[Path] = Path(__file__).resolve().parent / "cases.jsonl"
_TOL: Final[float] = 1e-6


def _engine_answer(problem_text: str) -> float | None:
    """The sealed engine's attempt (ADR-0182 cross-composer pooling).

    Pools the ungated readings of every composer (accumulation, multiplicative,
    chain) and resolves them together: a single ``complete`` answer commits;
    disagreement among the pool — e.g. a distractor problem's blunt product vs its
    competing additive reading — refuses. Replaces the prior first-composer-wins
    order, which had no way to notice it held two incompatible readings.
    """
    resolution = resolve_pooled(problem_text)
    return resolution.answer if resolution is not None else None


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    expected: str  # "refuse" | "solve"
    gold: float
    answered: float | None
    verdict: str  # "refused" | "solved" | "wrong" | "spurious"


def _verdict(expected: str, gold: float, answered: float | None) -> str:
    if answered is None:
        return "refused"
    if abs(answered - gold) <= _TOL:
        # a correct answer is "solved" for a positive, "spurious" for a refuse-case
        return "solved" if expected == "solve" else "spurious"
    return "wrong"


def load_cases(path: Path = _CASES_PATH) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def run_probe(path: Path = _CASES_PATH) -> tuple[CaseResult, ...]:
    """Evaluate the engine attempt over every confuser case. Deterministic order."""
    results: list[CaseResult] = []
    for case in load_cases(path):
        gold = float(case["answer_numeric"])
        answered = _engine_answer(case["question"])
        results.append(
            CaseResult(
                case_id=case["case_id"],
                category=case["category"],
                expected=case["expected"],
                gold=gold,
                answered=answered,
                verdict=_verdict(case["expected"], gold, answered),
            )
        )
    return tuple(results)


def pair_inconsistencies(path: Path = _CASES_PATH) -> tuple[str, ...]:
    """Pairs where the engine *solved the twin but committed an answer on the
    confuser* — the surface-matching tell. Returns the confuser case_ids."""
    cases = {c["case_id"]: c for c in load_cases(path)}
    by_id = {r.case_id: r for r in run_probe(path)}
    flagged: list[str] = []
    for cid, case in cases.items():
        pair = case.get("pair_id")
        if not pair or case["expected"] != "refuse":
            continue
        confuser, twin = by_id.get(cid), by_id.get(pair)
        if confuser is None or twin is None:
            continue
        # the tell: twin solved, yet the confuser was answered (wrong or spurious).
        if twin.verdict == "solved" and confuser.verdict in {"wrong", "spurious"}:
            flagged.append(cid)
    return tuple(sorted(flagged))


def summarize(results: tuple[CaseResult, ...]) -> dict[str, dict[str, int]]:
    """Per-category verdict counts. Deterministic (sorted categories)."""
    out: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = out.setdefault(r.category, {"solved": 0, "refused": 0, "wrong": 0, "spurious": 0})
        bucket[r.verdict] += 1
    return {k: out[k] for k in sorted(out)}


def main() -> int:  # pragma: no cover
    results = run_probe()
    summary = summarize(results)
    totals = {"solved": 0, "refused": 0, "wrong": 0, "spurious": 0}
    print(f"confuser probe: {len(results)} cases")
    print(f"{'category':<22} solved refused wrong spurious")
    for cat, counts in summary.items():
        for k in totals:
            totals[k] += counts[k]
        print(f"{cat:<22} {counts['solved']:>6} {counts['refused']:>7} {counts['wrong']:>5} {counts['spurious']:>8}")
    print(f"{'TOTAL':<22} {totals['solved']:>6} {totals['refused']:>7} {totals['wrong']:>5} {totals['spurious']:>8}")
    print(f"wrong (the bar; must trend to 0): {totals['wrong']}")
    print(f"pair-inconsistencies (surface-match tells): {list(pair_inconsistencies())}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
