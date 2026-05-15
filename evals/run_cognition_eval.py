"""Run the cognition eval harness.

Loads cases from cognition_cases.jsonl, runs each through the
CognitiveTurnPipeline, and produces an EvalReport with deterministic
metrics. Each case gets a fresh pipeline instance for isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from evals.metrics import CaseResult, EvalReport
from generate.intent import IntentTag

_CASES_PATH = Path(__file__).parent / "cognition_cases.jsonl"


def load_cases(path: Path | None = None) -> list[dict]:
    p = path or _CASES_PATH
    cases = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _run_case(case: dict, pipeline: CognitiveTurnPipeline) -> CaseResult:
    prompt = case["prompt"]
    expected_intent = case["expected_intent"]
    expected_terms = case.get("expected_terms", [])
    expected_surface_contains = case.get("expected_surface_contains", [])

    result = pipeline.run(prompt, max_tokens=8)

    actual_intent = result.intent.tag if result.intent else IntentTag.UNKNOWN
    intent_correct = actual_intent.value == expected_intent

    surface_lower = result.surface.lower()
    terms_captured = tuple(
        t for t in expected_terms if t.lower() in surface_lower
    )
    surface_contains_pass = all(
        s.lower() in surface_lower for s in expected_surface_contains
    )

    versor_ok = result.versor_condition < 1e-6

    return CaseResult(
        case_id=case["id"],
        category=case.get("category", "unknown"),
        prompt=prompt,
        intent_correct=intent_correct,
        terms_captured=terms_captured,
        terms_expected=tuple(expected_terms),
        surface_contains_pass=surface_contains_pass,
        versor_closure=versor_ok,
        versor_condition=result.versor_condition,
        trace_hash=result.trace_hash,
        surface=result.surface,
    )


def run_eval(cases: list[dict] | None = None) -> EvalReport:
    if cases is None:
        cases = load_cases()

    report = EvalReport()

    for case in cases:
        runtime = ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime)
        case_result = _run_case(case, pipeline)

        report.total += 1
        if case_result.intent_correct:
            report.intent_correct += 1
        report.terms_expected += len(case_result.terms_expected)
        report.terms_captured += len(case_result.terms_captured)
        if case_result.surface_contains_pass:
            report.surface_grounded += 1
        if case_result.versor_closure:
            report.versor_closures += 1
        report.cases.append(case_result)
        report.trace_hashes[case_result.case_id] = case_result.trace_hash

    return report


def check_determinism(cases: list[dict] | None = None, runs: int = 2) -> bool:
    if cases is None:
        cases = load_cases()

    hashes_by_run: list[dict[str, str]] = []
    for _ in range(runs):
        report = run_eval(cases)
        hashes_by_run.append(dict(report.trace_hashes))

    first = hashes_by_run[0]
    for run_hashes in hashes_by_run[1:]:
        if run_hashes != first:
            return False
    return True
