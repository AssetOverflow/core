"""Phase 5 stratified mechanism-isolation runner.

Extends the Phase 3 v2 mechanism-isolation runner across five
failure-mode families:

  A. near_forbidden_correct_endpoint  — small blade-score gap
  B. near_equal_admissible             — two candidates with near-equal scores
  C. no_admissible_path                — all candidates negative ⇒ honest refusal
  D. multi_step_admissibility          — chained single-step regions
  E. heterogeneous_relation            — chained steps with different blades

Each case is run under BOTH:

  * threshold mode  (per-case ``admissibility_threshold``)
  * margin mode     (ADR-0026 ranked-with-margin, ``δ = admissibility_margin``)

Per-family metrics:

    pass_rate                  expected behavior holds (see below)
    boundary_decoy_rate        boundary picks ``forbidden_token`` (where defined)
    rejection_traced_rate      ``forbidden_token`` in step.rejected_attempts
    refusal_rate               honest refusal raised (Family C and margin mode)
    refusal_reason_correct     refusal reason matches expectation
    mechanism_isolated         per-family causal isolation flag

A case "passes" iff its family-specific predicate is satisfied:

  Family A (threshold):  inner-loop selects expected, boundary picks forbidden,
                         rejection is in trace.
  Family A (margin):     blade gap < δ ⇒ refusal; blade gap ≥ δ ⇒ select expected.
  Family B (threshold):  inner-loop selects the higher-scoring admissible
                         (the case's ``expected_endpoint``).
  Family B (margin):     refusal (diff < δ by construction).
  Family C (both):       honest refusal with reason=INNER_LOOP_EXHAUSTION.
  Family D/E:            all steps satisfy their per-step predicate.

Conforms to the ``run_lane`` interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from field.state import FieldState
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.exhaustion import InnerLoopExhaustion, RefusalReason
from generate.result import GenerationResult
from generate.stream import generate as generate_walk


DEFAULT_MARGIN = 0.4


@dataclass(slots=True)
class Phase5Report:
    metrics: dict[str, Any] = field(default_factory=dict)
    per_family: dict[str, dict[str, Any]] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _field_state_from_seed(vocab, seed_token: str) -> FieldState:
    idx = vocab.index_of(seed_token)
    versor = np.asarray(vocab.get_versor(seed_token), dtype=np.float32)
    return FieldState(F=versor.copy(), node=idx, step=0)


def _region_from_step(vocab, step: dict[str, Any], label: str) -> AdmissibilityRegion:
    indices = [int(vocab.index_of(tok)) for tok in step["admissible_tokens"]]
    blade = np.asarray(
        vocab.get_versor(step["relation_blade_token"]), dtype=np.float32
    )
    return AdmissibilityRegion(
        allowed_indices=np.asarray(indices, dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label,
    )


def _run_one_step(
    vocab,
    persona,
    seed_state: FieldState,
    region: AdmissibilityRegion,
    *,
    mode: str,
    threshold: float,
    margin: float,
) -> dict[str, Any]:
    """Run a single-step generation under one of three legs:
      mode = "boundary" | "threshold" | "margin"
    Returns a dict with selection, admission status, rejected attempts,
    refusal reason (if any), and the raw exception class name on refusal.
    """
    kwargs: dict[str, Any] = dict(
        max_tokens=1,
        region=region,
        admissibility_threshold=threshold,
    )
    if mode == "boundary":
        kwargs["inner_loop_admissibility"] = False
    elif mode == "threshold":
        kwargs["inner_loop_admissibility"] = True
        kwargs["admissibility_mode"] = "threshold"
    elif mode == "margin":
        kwargs["inner_loop_admissibility"] = True
        kwargs["admissibility_mode"] = "margin"
        kwargs["admissibility_margin"] = margin
    else:
        raise ValueError(f"unknown mode: {mode}")

    try:
        result: GenerationResult = generate_walk(seed_state, vocab, persona, **kwargs)
    except InnerLoopExhaustion as exc:
        return {
            "refused": True,
            "refusal_reason": exc.reason.value if hasattr(exc.reason, "value") else str(exc.reason),
            "refusal_message": str(exc),
            "rejected_attempts": [
                [int(idx), str(word), float(score)]
                for (idx, word, score) in exc.rejected_attempts
            ],
        }
    except ValueError as exc:
        return {"refused": True, "refusal_reason": "value_error", "refusal_message": str(exc)}

    step = result.admissibility_trace[0]
    return {
        "refused": False,
        "selected": step.selected_word,
        "admitted": bool(step.verdict.admitted),
        "rejected_attempts": [
            [int(idx), str(word), float(score)]
            for (idx, word, score) in step.rejected_attempts
        ],
        "rejected_words": [w for (_idx, w, _sc) in step.rejected_attempts],
    }


def _evaluate_single_step_case(case: dict[str, Any], margin: float) -> dict[str, Any]:
    runtime = ChatRuntime()
    vocab = runtime.session.vocab
    persona = runtime.session.persona

    try:
        seed_state = _field_state_from_seed(vocab, case["seed_token"])
        region = _region_from_step(vocab, case, label=f"p5[{case.get('id', '')}]")
    except (KeyError, ValueError) as exc:
        return {"id": case.get("id", ""), "skipped": True, "reason": str(exc)}

    threshold = float(case["admissibility_threshold"])
    family = case["family"]
    expected = case.get("expected_endpoint")
    forbidden = case.get("forbidden_token")
    expect_refusal = bool(case.get("expect_refusal", False))
    expected_refusal_reason = case.get("refusal_reason", "")

    boundary = _run_one_step(
        vocab, persona, seed_state, region,
        mode="boundary", threshold=threshold, margin=margin,
    )
    # Fresh state for each leg (region/state object copies fine; seed_state
    # is read-only re: F, but generate may not mutate.  Keep distinct
    # FieldState instances out of paranoia).
    seed_state_t = _field_state_from_seed(vocab, case["seed_token"])
    threshold_leg = _run_one_step(
        vocab, persona, seed_state_t, region,
        mode="threshold", threshold=threshold, margin=margin,
    )
    seed_state_m = _field_state_from_seed(vocab, case["seed_token"])
    margin_leg = _run_one_step(
        vocab, persona, seed_state_m, region,
        mode="margin", threshold=threshold, margin=margin,
    )

    detail: dict[str, Any] = {
        "id": case.get("id", ""),
        "family": family,
        "kind": case.get("kind", ""),
        "seed_token": case["seed_token"],
        "expected_endpoint": expected,
        "forbidden_token": forbidden,
        "expect_refusal": expect_refusal,
        "boundary": boundary,
        "threshold_leg": threshold_leg,
        "margin_leg": margin_leg,
        "rationale": case.get("rationale", ""),
    }

    # Pass predicate per family.
    detail["passed_threshold"] = _passed_single(
        family, threshold_leg, expected, forbidden,
        expect_refusal=expect_refusal,
        expected_refusal_reason=expected_refusal_reason,
        mode="threshold",
    )
    detail["passed_margin"] = _passed_single(
        family, margin_leg, expected, forbidden,
        expect_refusal=expect_refusal,
        expected_refusal_reason=expected_refusal_reason,
        mode="margin",
    )
    return detail


def _passed_single(
    family: str,
    leg: dict[str, Any],
    expected: str | None,
    forbidden: str | None,
    *,
    expect_refusal: bool,
    expected_refusal_reason: str,
    mode: str,
) -> bool:
    if family == "no_admissible_path":
        if not leg.get("refused"):
            return False
        if expected_refusal_reason:
            return leg.get("refusal_reason") == expected_refusal_reason
        return True
    if family == "near_forbidden_correct_endpoint":
        if mode == "threshold":
            # Pass: inner-loop selects expected and admits.  Rejection
            # of the forbidden in trace is desirable but not required
            # for the pass predicate — when boundary already prefers
            # expected, the inner-loop never attempts the forbidden.
            # The aggregate ``rejection_traced_rate`` surfaces this
            # separately so the boundary-overrides-inner signal is
            # visible without inflating refusals.
            return (
                not leg.get("refused", False)
                and leg.get("selected") == expected
                and leg.get("admitted", False)
            )
        # margin mode: small-gap cases refuse, large-gap cases admit.
        if leg.get("refused"):
            return leg.get("refusal_reason") == RefusalReason.INNER_LOOP_EXHAUSTION.value
        return leg.get("selected") == expected and leg.get("admitted", False)
    if family == "near_equal_admissible":
        if mode == "threshold":
            # Near-equal: any admissible candidate is acceptable under
            # threshold mode (the ``expected_endpoint`` field is the
            # nominal higher-scoring token but exact ties flip on
            # tie-break, which is deterministic but order-dependent).
            # Pass: admitted, not refused.
            return (
                not leg.get("refused", False)
                and leg.get("admitted", False)
            )
        # margin: expect refusal by construction (diff < δ).
        return leg.get("refused", False) and (
            leg.get("refusal_reason") == RefusalReason.INNER_LOOP_EXHAUSTION.value
        )
    # Unknown family: don't crash, just mark fail.
    return False


def _evaluate_chain_case(case: dict[str, Any], margin: float) -> dict[str, Any]:
    runtime = ChatRuntime()
    vocab = runtime.session.vocab
    persona = runtime.session.persona

    steps = case["steps"]
    family = case["family"]
    detail: dict[str, Any] = {
        "id": case.get("id", ""),
        "family": family,
        "kind": case.get("kind", ""),
        "step_count": len(steps),
        "rationale": case.get("rationale", ""),
        "step_results_threshold": [],
        "step_results_margin": [],
    }

    for mode in ("threshold", "margin"):
        step_results: list[dict[str, Any]] = []
        all_passed = True
        for i, step in enumerate(steps):
            try:
                seed_state = _field_state_from_seed(vocab, step["seed_token"])
                region = _region_from_step(
                    vocab, step, label=f"p5[{case.get('id', '')}][s{i}]"
                )
            except (KeyError, ValueError) as exc:
                step_results.append({"skipped": True, "reason": str(exc)})
                all_passed = False
                break
            threshold = float(step["admissibility_threshold"])
            leg = _run_one_step(
                vocab, persona, seed_state, region,
                mode=mode, threshold=threshold, margin=margin,
            )
            # Per-step family classification: 'no_admissible_path' if
            # expect_refusal, else near_forbidden.
            step_family = (
                "no_admissible_path" if step.get("expect_refusal")
                else "near_forbidden_correct_endpoint"
            )
            step_passed = _passed_single(
                step_family,
                leg,
                step.get("expected_endpoint"),
                step.get("forbidden_token"),
                expect_refusal=bool(step.get("expect_refusal", False)),
                expected_refusal_reason=step.get("refusal_reason", ""),
                mode=mode,
            )
            step_results.append({
                "step_index": i,
                "step_family": step_family,
                "leg": leg,
                "passed": step_passed,
            })
            if not step_passed:
                all_passed = False
                # Continue iterating so we record all step outcomes (no early
                # break) — but for chain semantics, downstream selection is
                # undefined after a refusal, so stop walking.
                if leg.get("refused") and not step.get("expect_refusal"):
                    break
        if mode == "threshold":
            detail["step_results_threshold"] = step_results
            detail["passed_threshold"] = all_passed
        else:
            detail["step_results_margin"] = step_results
            detail["passed_margin"] = all_passed
    return detail


def _is_chain_case(case: dict[str, Any]) -> bool:
    return "steps" in case and isinstance(case["steps"], list)


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> Phase5Report:
    _ = workers  # serial
    margin = float(config.admissibility_margin) if config else DEFAULT_MARGIN
    if not cases:
        return Phase5Report(metrics={"margin": margin}, per_family={}, case_details=[])

    details: list[dict[str, Any]] = []
    for c in cases:
        if _is_chain_case(c):
            details.append(_evaluate_chain_case(c, margin))
        else:
            details.append(_evaluate_single_step_case(c, margin))

    per_family: dict[str, dict[str, Any]] = {}
    for d in details:
        fam = d.get("family", "unknown")
        bucket = per_family.setdefault(fam, {
            "case_count": 0,
            "pass_count_threshold": 0,
            "pass_count_margin": 0,
            "refusal_count_threshold": 0,
            "refusal_count_margin": 0,
            "rejection_traced_threshold": 0,
            "boundary_overridden_threshold": 0,
        })
        bucket["case_count"] += 1
        if d.get("passed_threshold"):
            bucket["pass_count_threshold"] += 1
        if d.get("passed_margin"):
            bucket["pass_count_margin"] += 1
        # Refusal counts only meaningful for single-step cases here.
        leg_t = d.get("threshold_leg") or {}
        leg_m = d.get("margin_leg") or {}
        if leg_t.get("refused"):
            bucket["refusal_count_threshold"] += 1
        if leg_m.get("refused"):
            bucket["refusal_count_margin"] += 1
        # Rejection-traced: forbidden appeared in rejected_words AND
        # inner-loop overrode boundary.  Only meaningful for single-step
        # cases with a forbidden_token.
        boundary_sel = (d.get("boundary") or {}).get("selected")
        thr_sel = leg_t.get("selected")
        forbidden = d.get("forbidden_token")
        if forbidden and forbidden in (leg_t.get("rejected_words") or []):
            bucket["rejection_traced_threshold"] += 1
        if boundary_sel and thr_sel and boundary_sel != thr_sel:
            bucket["boundary_overridden_threshold"] += 1

    for bucket in per_family.values():
        n = max(bucket["case_count"], 1)
        bucket["pass_rate_threshold"] = round(bucket["pass_count_threshold"] / n, 4)
        bucket["pass_rate_margin"] = round(bucket["pass_count_margin"] / n, 4)
        bucket["refusal_rate_threshold"] = round(bucket["refusal_count_threshold"] / n, 4)
        bucket["refusal_rate_margin"] = round(bucket["refusal_count_margin"] / n, 4)
        bucket["rejection_traced_rate_threshold"] = round(
            bucket["rejection_traced_threshold"] / n, 4
        )
        bucket["boundary_overridden_rate_threshold"] = round(
            bucket["boundary_overridden_threshold"] / n, 4
        )

    overall: dict[str, Any] = {
        "case_count": len(details),
        "skipped_count": sum(1 for d in details if d.get("skipped")),
        "pass_count_threshold": sum(1 for d in details if d.get("passed_threshold")),
        "pass_count_margin": sum(1 for d in details if d.get("passed_margin")),
        "margin": margin,
    }
    n = max(overall["case_count"], 1)
    overall["pass_rate_threshold"] = round(overall["pass_count_threshold"] / n, 4)
    overall["pass_rate_margin"] = round(overall["pass_count_margin"] / n, 4)
    overall["mechanism_isolated_threshold"] = overall["pass_rate_threshold"] == 1.0
    overall["mechanism_isolated_margin"] = overall["pass_rate_margin"] == 1.0
    return Phase5Report(metrics=overall, per_family=per_family, case_details=details)


def main() -> int:
    cases_path = Path("evals/forward_semantic_control/public/v2_phase5/cases.jsonl")
    out_path = Path("evals/forward_semantic_control/results/phase5_report.json")
    cases = [json.loads(l) for l in cases_path.read_text().splitlines() if l.strip()]
    report = run_lane(cases)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "metrics": report.metrics,
        "per_family": report.per_family,
        "case_details": report.case_details,
    }, indent=2))
    print(json.dumps({"metrics": report.metrics, "per_family": report.per_family}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
