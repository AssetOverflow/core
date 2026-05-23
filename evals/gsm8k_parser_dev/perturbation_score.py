"""Score ADR-0125 semantic perturbations for the parser dev lane."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from evals.gsm8k_parser_dev.ood_score import load_cases
from generate.math_parser import ParseError, parse_problem
from generate.math_solver import SolutionTrace, SolveError, solve
from generate.perturbation_suite import (
    INVARIANCE_BREAKING,
    INVARIANCE_PRESERVING,
    Perturbation,
    generate_perturbations,
    skip_reasons,
)


def score_perturbation(perturbation: Perturbation) -> tuple[bool, str]:
    try:
        graph = parse_problem(perturbation.problem_text)
        trace = solve(graph)
    except (ParseError, SolveError) as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if graph.canonical_bytes() != perturbation.expected_graph.canonical_bytes():
        return False, "parsed graph did not match predicted perturbation graph"
    if trace.answer_unit != perturbation.expected_unit:
        return False, f"unit {trace.answer_unit!r} != {perturbation.expected_unit!r}"
    if trace.answer_value != perturbation.expected_answer:
        return (
            False,
            f"answer {trace.answer_value!r} != {perturbation.expected_answer!r}",
        )
    if perturbation.kind == INVARIANCE_BREAKING:
        expected_trace_hash = perturbation.transform_params.get("expected_trace_hash")
        if expected_trace_hash is not None and _trace_hash(trace) != expected_trace_hash:
            return False, "trace hash did not match predicted perturbation trace"
    return True, "ok"


def _trace_hash(trace: SolutionTrace) -> str:
    return hashlib.sha256(trace.canonical_bytes()).hexdigest()


def _seed_from_case_id(case_id: str) -> int:
    return int(case_id.rsplit("-", 1)[1])


def _ratio(correct: int, total: int) -> float:
    return correct / total if total else 0.0


def _ratio_text(correct: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{_ratio(correct, total):.4f}"


def main() -> int:
    cases = load_cases()
    per_transform: dict[str, list[bool]] = defaultdict(list)
    per_kind: dict[str, list[bool]] = defaultdict(list)
    skip_counts: dict[str, list[str]] = defaultdict(list)

    for case in cases:
        seed = _seed_from_case_id(case.case_id)
        perturbations = generate_perturbations(case.problem, case.graph, seed=seed)
        skips = skip_reasons(case.problem, case.graph, seed=seed)
        for transform, reason in sorted(skips.items()):
            skip_counts[transform].append(case.case_id)
            print(f"SKIP {case.case_id}:{transform}: {reason}")

        for perturbation in perturbations:
            ok, detail = score_perturbation(perturbation)
            per_transform[perturbation.transform].append(ok)
            per_kind[perturbation.kind].append(ok)
            status = "PASS" if ok else "FAIL"
            print(
                f"{status} {perturbation.perturbation_id} "
                f"{perturbation.kind}/{perturbation.transform}: {detail}"
            )

    print()
    for transform in sorted(set(per_transform) | set(skip_counts)):
        results = per_transform.get(transform, [])
        correct = sum(results)
        total = len(results)
        skipped = len(skip_counts.get(transform, []))
        print(
            f"transform {transform}: {correct}/{total} = {_ratio_text(correct, total)} "
            f"(skipped {skipped}/{len(cases)})"
        )

    preserving = per_kind[INVARIANCE_PRESERVING]
    breaking = per_kind[INVARIANCE_BREAKING]
    preserving_correct = sum(preserving)
    breaking_correct = sum(breaking)
    preserving_total = len(preserving)
    breaking_total = len(breaking)
    preserving_ratio = _ratio(preserving_correct, preserving_total)
    breaking_ratio = _ratio(breaking_correct, breaking_total)

    print(
        f"invariance_preserving: {preserving_correct}/{preserving_total} = "
        f"{preserving_ratio:.4f}"
    )
    print(
        f"invariance_breaking: {breaking_correct}/{breaking_total} = "
        f"{breaking_ratio:.4f}"
    )

    return 0 if preserving_ratio == 1.0 and breaking_ratio == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
