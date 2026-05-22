from __future__ import annotations

import json
import re
from pathlib import Path

from evals.gsm8k_parser_dev.ood_score import Case, score_public, score_variant
from generate.math_problem_graph import MathProblemGraph, graph_from_dict
from generate.math_solver import solve
from generate.ood_surface_generator import OODVariant, generate_ood_variants


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


def _variants() -> list[tuple[dict, OODVariant]]:
    out: list[tuple[dict, OODVariant]] = []
    for case in _cases():
        graph = _graph(case)
        for variant in generate_ood_variants(
            case["problem"], graph, seed=_seed(case["id"]), n=3
        ):
            out.append((case, variant))
    return out


def _variant_bytes(variants: list[OODVariant]) -> bytes:
    payload = [
        {
            "original_id": v.original_id,
            "variant_id": v.variant_id,
            "transform": v.transform,
            "transform_params": v.transform_params,
            "problem_text": v.problem_text,
            "expected_graph_after_unrename": json.loads(
                v.expected_graph_after_unrename.canonical_bytes()
            ),
            "expected_answer": v.expected_answer,
            "expected_unit": v.expected_unit,
        }
        for v in variants
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_generator_is_byte_deterministic_for_same_seed() -> None:
    case = _cases()[6]
    graph = _graph(case)
    first = generate_ood_variants(case["problem"], graph, seed=_seed(case["id"]), n=3)
    second = generate_ood_variants(case["problem"], graph, seed=_seed(case["id"]), n=3)
    assert _variant_bytes(first) == _variant_bytes(second)


def test_expected_graph_after_unrename_is_original_graph() -> None:
    for case, variant in _variants():
        assert (
            variant.expected_graph_after_unrename.canonical_bytes()
            == _graph(case).canonical_bytes()
        )


def test_live_parser_and_solver_match_each_variant_expected_answer() -> None:
    for _, variant in _variants():
        ok, detail = score_variant(variant)
        assert ok, f"{variant.variant_id}: {detail}\n{variant.problem_text}"


def test_ood_public_ratio_meets_gate_across_dev_set() -> None:
    cases = _cases()
    public_cases = [
        Case(
            case_id=c["id"],
            problem=c["problem"],
            expected_answer=c["expected_answer"],
            expected_unit=c["expected_unit"],
            graph=_graph(c),
        )
        for c in cases
    ]
    public_correct, public_total = score_public(public_cases)
    public_ratio = public_correct / public_total

    results = [score_variant(v)[0] for _, v in _variants()]
    ood_ratio = sum(results) / len(results)

    assert ood_ratio / public_ratio >= 0.95


def test_variants_do_not_use_public_entity_or_unit_strings() -> None:
    public_entities: set[str] = set()
    public_units: set[str] = set()
    for case in _cases():
        graph = _graph(case)
        public_entities.update(graph.entities)
        public_units.update(p.quantity.unit for p in graph.initial_state)
        public_units.update(o.operand.unit for o in graph.operations)
        public_units.add(graph.unknown.unit)

    for _, variant in _variants():
        words = set(re.findall(r"\b[A-Za-z]+\b", variant.problem_text))
        assert not (words & public_entities), variant.problem_text
        assert not ({w.lower() for w in words} & public_units), variant.problem_text


def test_scale_by_k_variants_scale_expected_answer_linearly() -> None:
    for case, variant in _variants():
        if variant.transform != "scale_numbers_by_k":
            continue
        original_trace = solve(_graph(case))
        k = variant.transform_params["k"]
        assert original_trace.answer_value * k == variant.expected_answer
