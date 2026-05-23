from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evals.gsm8k_parser_dev.perturbation_score import score_perturbation
from generate.math_parser import parse_problem
from generate.math_problem_graph import (
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
    Unknown,
    graph_from_dict,
)
from generate.math_solver import solve
from generate.perturbation_suite import (
    INVARIANCE_BREAKING,
    INVARIANCE_PRESERVING,
    Perturbation,
    generate_perturbations,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES_PATH = _REPO_ROOT / "evals" / "gsm8k_parser_dev" / "cases.jsonl"


def _cases() -> list[dict]:
    return [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _seed(case_id: str) -> int:
    return int(case_id.rsplit("-", 1)[1])


def _graph(case: dict) -> MathProblemGraph:
    return graph_from_dict(case["ground_truth_graph"])


def _perturbations() -> list[tuple[dict, Perturbation]]:
    out: list[tuple[dict, Perturbation]] = []
    for case in _cases():
        graph = _graph(case)
        for perturbation in generate_perturbations(
            case["problem"], graph, seed=_seed(case["id"])
        ):
            out.append((case, perturbation))
    return out


def _perturbation_bytes(perturbations: list[Perturbation]) -> bytes:
    payload = [
        {
            "original_id": p.original_id,
            "perturbation_id": p.perturbation_id,
            "kind": p.kind,
            "transform": p.transform,
            "transform_params": p.transform_params,
            "problem_text": p.problem_text,
            "expected_graph": json.loads(p.expected_graph.canonical_bytes()),
            "expected_answer": p.expected_answer,
            "expected_unit": p.expected_unit,
        }
        for p in perturbations
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _trace_hash(graph: MathProblemGraph) -> str:
    return hashlib.sha256(solve(graph).canonical_bytes()).hexdigest()


def test_generator_is_byte_deterministic_for_same_seed() -> None:
    case = _cases()[20]
    graph = _graph(case)
    first = generate_perturbations(case["problem"], graph, seed=_seed(case["id"]))
    second = generate_perturbations(case["problem"], graph, seed=_seed(case["id"]))
    assert _perturbation_bytes(first) == _perturbation_bytes(second)


def test_invariance_preserving_perturbations_keep_original_answer_value() -> None:
    for case, perturbation in _perturbations():
        if perturbation.kind != INVARIANCE_PRESERVING:
            continue
        original_answer = solve(_graph(case)).answer_value
        assert perturbation.expected_answer == original_answer, perturbation


def test_invariance_breaking_perturbations_match_predicted_graph_solve() -> None:
    for _, perturbation in _perturbations():
        if perturbation.kind != INVARIANCE_BREAKING:
            continue
        trace = solve(perturbation.expected_graph)
        assert perturbation.expected_answer == trace.answer_value
        assert perturbation.expected_unit == trace.answer_unit
        assert perturbation.transform_params["expected_trace_hash"] == _trace_hash(
            perturbation.expected_graph
        )


def test_aggregate_dev_rates_are_perfect_for_applicable_perturbations() -> None:
    preserving: list[bool] = []
    breaking: list[bool] = []
    for _, perturbation in _perturbations():
        ok, detail = score_perturbation(perturbation)
        assert ok, f"{perturbation.perturbation_id}: {detail}"
        if perturbation.kind == INVARIANCE_PRESERVING:
            preserving.append(ok)
        elif perturbation.kind == INVARIANCE_BREAKING:
            breaking.append(ok)

    assert preserving and sum(preserving) / len(preserving) == 1.0
    assert breaking and sum(breaking) / len(breaking) == 1.0


def test_verb_synonym_perturbations_use_a_different_verb() -> None:
    for _, perturbation in _perturbations():
        if perturbation.transform != "replace_verb_with_synonym":
            continue
        original = perturbation.transform_params["original_verb"]
        replacement = perturbation.transform_params["replacement_verb"]
        assert original is not None
        assert replacement != original
        assert f" {replacement} " in perturbation.problem_text


def test_reorder_initial_perturbations_change_sentence_order_but_preserve_answer() -> None:
    case = next(c for c in _cases() if c["id"] == "gpd-005")
    original_graph = _graph(case)
    perturbation = next(
        p
        for p in generate_perturbations(case["problem"], original_graph, seed=_seed(case["id"]))
        if p.transform == "reorder_independent_initial_possessions"
    )

    assert perturbation.problem_text != case["problem"]
    assert perturbation.expected_graph.initial_state == tuple(
        reversed(original_graph.initial_state)
    )
    assert perturbation.expected_answer == solve(original_graph).answer_value


def test_reorder_independent_operations_changes_sentence_order_but_not_answer() -> None:
    graph = MathProblemGraph(
        entities=("Tom", "Sara"),
        initial_state=(
            InitialPossession("Tom", Quantity(4, "apples")),
            InitialPossession("Sara", Quantity(7, "apples")),
        ),
        operations=(
            Operation("Tom", "add", Quantity(3, "apples")),
            Operation("Sara", "subtract", Quantity(2, "apples")),
        ),
        unknown=Unknown(entity=None, unit="apples"),
    )
    problem = (
        "Tom has 4 apples. Sara has 7 apples. Tom buys 3 more apples. "
        "Sara loses 2 apples. How many apples do they have in total?"
    )
    perturbation = next(
        p
        for p in generate_perturbations(problem, graph, seed=777)
        if p.transform == "reorder_independent_operations"
    )

    parsed = parse_problem(perturbation.problem_text)
    assert perturbation.problem_text.index("Sara loses") < perturbation.problem_text.index(
        "Tom buys"
    )
    assert parsed.operations == tuple(reversed(graph.operations))
    assert solve(parsed).answer_value == solve(graph).answer_value
