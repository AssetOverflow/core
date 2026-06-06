"""Per-lane adapters — normalize each independent-gold lane to a DomainResult.

These are thin COUNT extractors, not capability logic: each calls a lane's own
self-loading runner and reads its correct/wrong/refused counts. A lane that fails
to run is recorded as ``not_covered`` (no silent drop), never faked.
"""

from __future__ import annotations

from dataclasses import dataclass

from evals.capability_index.index import DomainResult


def _counts(report: dict) -> tuple[int, int, int]:
    c = report.get("counts", report)
    return int(c["correct"]), int(c["wrong"]), int(c["refused"])


def deductive_logic_result() -> DomainResult:
    from evals.deductive_logic.runner import build_combined_report

    agg = build_combined_report()["aggregate"]  # {n, correct, wrong, refused}
    return DomainResult(
        "deductive_logic", int(agg["correct"]), int(agg["wrong"]), int(agg["refused"])
    )


def relational_metric_result() -> DomainResult:
    from evals.relational_metric.runner import run

    r = run()
    return DomainResult(
        "relational_metric", int(r["correct"]), int(r["wrong"]), int(r["refused"])
    )


def dimensional_result() -> DomainResult:
    from evals.dimensional.runner import _ROOT, _load, build_report

    correct, wrong, refused = _counts(build_report(_load(_ROOT / "v1" / "cases.jsonl")))
    return DomainResult("dimensional", correct, wrong, refused)


def comprehension_set_membership_result() -> DomainResult:
    from evals.comprehension.set_membership_runner import run

    c, w, r = _counts(run())
    return DomainResult("comprehension_set_membership", c, w, r)


def comprehension_syllogism_result() -> DomainResult:
    from evals.comprehension.syllogism_runner import run

    c, w, r = _counts(run())
    return DomainResult("comprehension_syllogism", c, w, r)


def comprehension_total_ordering_result() -> DomainResult:
    from evals.comprehension.total_ordering_runner import run

    c, w, r = _counts(run())
    return DomainResult("comprehension_total_ordering", c, w, r)


def comprehension_propositional_result() -> DomainResult:
    from evals.comprehension.propositional_runner import run

    c, w, r = _counts(run())
    return DomainResult("comprehension_propositional", c, w, r)


#: The reasoning domains currently composed into the index (self-loading lanes).
#: The four ``comprehension_*`` lanes score the GENERAL comprehension reader
#: (prose -> MeaningGraph -> projection -> independent oracle), so the index now
#: measures comprehension breadth, not just structured-input reasoning.
ADAPTERS = (
    deductive_logic_result,
    relational_metric_result,
    dimensional_result,
    comprehension_set_membership_result,
    comprehension_syllogism_result,
    comprehension_total_ordering_result,
    comprehension_propositional_result,
)


@dataclass(frozen=True, slots=True)
class Collection:
    results: tuple[DomainResult, ...]
    not_covered: tuple[tuple[str, str], ...]  # (adapter_name, error) — no silent drop


def collect_domain_results() -> Collection:
    """Run every adapter; surface any that fail rather than dropping them."""
    results: list[DomainResult] = []
    not_covered: list[tuple[str, str]] = []
    for adapter in ADAPTERS:
        try:
            results.append(adapter())
        except Exception as exc:  # noqa: BLE001 — surfacing is the contract
            not_covered.append((adapter.__name__, repr(exc)))
    return Collection(results=tuple(results), not_covered=tuple(not_covered))
