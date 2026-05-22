"""Score ADR-0118a OOD surface variants for the parser dev lane."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from generate.math_parser import ParseError, parse_problem
from generate.math_problem_graph import MathProblemGraph, graph_from_dict
from generate.math_solver import SolveError, solve
from generate.ood_surface_generator import OODVariant, generate_ood_variants


_CASES_PATH = Path(__file__).with_name("cases.jsonl")
_GATE_RATIO = 0.95


@dataclass(frozen=True, slots=True)
class Case:
    case_id: str
    problem: str
    expected_answer: float
    expected_unit: str
    graph: MathProblemGraph


def load_cases(path: Path = _CASES_PATH) -> list[Case]:
    cases: list[Case] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        cases.append(
            Case(
                case_id=raw["id"],
                problem=raw["problem"],
                expected_answer=raw["expected_answer"],
                expected_unit=raw["expected_unit"],
                graph=graph_from_dict(raw["ground_truth_graph"]),
            )
        )
    return cases


def score_public(cases: list[Case]) -> tuple[int, int]:
    correct = 0
    for case in cases:
        try:
            graph = parse_problem(case.problem)
            trace = solve(graph)
        except (ParseError, SolveError):
            continue
        if (
            graph.canonical_bytes() == case.graph.canonical_bytes()
            and trace.answer_value == case.expected_answer
            and trace.answer_unit == case.expected_unit
        ):
            correct += 1
    return correct, len(cases)


def score_variant(variant: OODVariant) -> tuple[bool, str]:
    try:
        trace = solve(parse_problem(variant.problem_text))
    except (ParseError, SolveError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if trace.answer_unit != variant.expected_unit:
        return False, f"unit {trace.answer_unit!r} != {variant.expected_unit!r}"
    if trace.answer_value != variant.expected_answer:
        return False, f"answer {trace.answer_value!r} != {variant.expected_answer!r}"
    return True, "ok"


def _seed_from_case_id(case_id: str) -> int:
    return int(case_id.rsplit("-", 1)[1])


def main() -> int:
    cases = load_cases()
    public_correct, public_total = score_public(cases)
    public_ratio = public_correct / public_total if public_total else 0.0

    ood_correct = 0
    ood_total = 0
    per_transform: dict[str, list[bool]] = defaultdict(list)

    for case in cases:
        variants = generate_ood_variants(
            case.problem,
            case.graph,
            seed=_seed_from_case_id(case.case_id),
            n=3,
        )
        for variant in variants:
            ok, detail = score_variant(variant)
            ood_correct += int(ok)
            ood_total += 1
            per_transform[variant.transform].append(ok)
            status = "PASS" if ok else "FAIL"
            print(f"{status} {variant.variant_id} {variant.transform}: {detail}")

    print()
    for transform in sorted(per_transform):
        results = per_transform[transform]
        correct = sum(results)
        total = len(results)
        ratio = correct / total if total else 0.0
        print(f"transform {transform}: {correct}/{total} = {ratio:.4f}")

    ood_ratio = ood_correct / ood_total if ood_total else 0.0
    relative = ood_ratio / public_ratio if public_ratio else 0.0
    print(f"public: {public_correct}/{public_total} = {public_ratio:.4f}")
    print(f"ood: {ood_correct}/{ood_total} = {ood_ratio:.4f}")
    print(f"ood/public: {relative:.4f}")

    return 0 if relative >= _GATE_RATIO else 1


if __name__ == "__main__":
    raise SystemExit(main())
