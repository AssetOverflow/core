"""Calibration eval lane runner.

Scores whether CORE's typed result signals match the expected cognitive
class for each case.

  no_grounding        — result.vault_hits == 0 (gate fired, no recall)
  coherent            — result.vault_hits > 0 (vault recall fired)
  correction_proposed — result.pack_mutation_proposal is not None

Each case runs on its own fresh CognitiveTurnPipeline so field-state
drift from prior cases does not poison the gate / recall geometry.

See contract.md for the structural claim; see gaps.md for the
architectural findings underlying the choice of signals.

Conforms to the framework interface: run_lane(cases, config=None) -> report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.cognition.result import CognitiveTurnResult
from core.config import RuntimeConfig

VALID_CLASSES = frozenset({"no_grounding", "coherent", "correction_proposed"})


@dataclass(slots=True)
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _infer_class(result: CognitiveTurnResult) -> str:
    if result.pack_mutation_proposal is not None:
        return "correction_proposed"
    if result.vault_hits > 0:
        return "coherent"
    return "no_grounding"


def _run_case(case: dict[str, Any], config: RuntimeConfig | None) -> dict[str, Any]:
    runtime = ChatRuntime(config=config) if config else ChatRuntime()
    pipeline = CognitiveTurnPipeline(runtime)

    for prime_prompt in case.get("prime", []):
        try:
            pipeline.run(prime_prompt, max_tokens=8)
        except ValueError:
            pass

    expected = case.get("expected_class", "")
    prompt = case["prompt"]

    try:
        result = pipeline.run(prompt, max_tokens=8)
        inferred = _infer_class(result)
        vault_hits = result.vault_hits
        proposal_present = result.pack_mutation_proposal is not None
    except ValueError:
        inferred = "no_grounding"
        vault_hits = 0
        proposal_present = False

    passed = inferred == expected
    return {
        "id": case.get("id", ""),
        "expected_class": expected,
        "inferred_class": inferred,
        "vault_hits": vault_hits,
        "proposal_present": proposal_present,
        "passed": passed,
    }


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
) -> LaneReport:
    if not cases:
        return LaneReport(metrics={}, case_details=[])

    invalid = [c.get("id", "?") for c in cases if c.get("expected_class") not in VALID_CLASSES]
    if invalid:
        raise ValueError(f"Unknown expected_class in cases: {invalid}")

    case_details: list[dict[str, Any]] = []
    class_correct: dict[str, int] = {c: 0 for c in VALID_CLASSES}
    class_total: dict[str, int] = {c: 0 for c in VALID_CLASSES}

    for case in cases:
        detail = _run_case(case, config)
        case_details.append(detail)
        ec = detail["expected_class"]
        class_total[ec] += 1
        if detail["passed"]:
            class_correct[ec] += 1

    def acc(cls: str) -> float | None:
        total = class_total[cls]
        if total == 0:
            return None
        return class_correct[cls] / total

    total_cases = len(case_details)
    total_correct = sum(1 for d in case_details if d["passed"])
    overall_accuracy = total_correct / total_cases if total_cases > 0 else 0.0

    ng_acc = acc("no_grounding")
    co_acc = acc("coherent")
    cp_acc = acc("correction_proposed")

    def _passes(a: float | None) -> bool:
        return a is None or a >= 0.80

    overall_pass = (
        _passes(ng_acc)
        and _passes(co_acc)
        and _passes(cp_acc)
        and overall_accuracy >= 0.80
    )

    metrics: dict[str, Any] = {
        "no_grounding_accuracy": round(ng_acc, 4) if ng_acc is not None else None,
        "coherent_accuracy": round(co_acc, 4) if co_acc is not None else None,
        "correction_proposed_accuracy": round(cp_acc, 4) if cp_acc is not None else None,
        "overall_accuracy": round(overall_accuracy, 4),
        "class_counts": {c: class_total[c] for c in VALID_CLASSES},
        "overall_pass": overall_pass,
    }

    return LaneReport(metrics=metrics, case_details=case_details)
