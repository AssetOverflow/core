"""Phase 3 mechanism-isolation runner — ADR-0024 v2 adversarial cases.

Synthetic cases where boundary-only is *expected* to select a forbidden
decoy and inner-loop is *expected* to reject it and select the correct
endpoint.  The case schema specifies its own region (admissible token
set + relation blade token) so the geometric setup is fully controlled
and reproducible.

A case passes iff *all* of the following hold under the same field
state:

    boundary-only:
        selected == forbidden_token
        verdict.admitted is False  (the rejection is visible in trace)

    inner-loop (admissibility_threshold from the case):
        selected == expected_endpoint
        verdict.admitted is True
        forbidden_token appears in step.rejected_attempts

Each case's seed_token sets the initial FieldState.F.  No priming —
the geometric configuration is given.  This is mechanism isolation,
not corpus observation; pair with ``inner_loop_runner.py`` (Phase 2)
for the corpus side.

Reports per case + aggregate proof_rate and rejection_causally_traced
counts.  Conforms to the ``run_lane`` interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from field.state import FieldState
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.result import GenerationResult
from generate.stream import generate as generate_walk


@dataclass(slots=True)
class V2Report:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _field_state_from_seed(vocab, seed_token: str) -> FieldState:
    idx = vocab.index_of(seed_token)
    versor = np.asarray(vocab.get_versor(seed_token), dtype=np.float32)
    return FieldState(F=versor.copy(), node=idx, step=0)


def _region_from_case(vocab, case: dict[str, Any]) -> AdmissibilityRegion:
    indices = [int(vocab.index_of(tok)) for tok in case["admissible_tokens"]]
    blade = np.asarray(
        vocab.get_versor(case["relation_blade_token"]), dtype=np.float32
    )
    return AdmissibilityRegion(
        allowed_indices=np.asarray(indices, dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=f"v2[{case.get('id', '')}]",
    )


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    runtime = ChatRuntime()
    vocab = runtime.session.vocab
    persona = runtime.session.persona

    try:
        seed_state = _field_state_from_seed(vocab, case["seed_token"])
        region = _region_from_case(vocab, case)
    except (KeyError, ValueError) as exc:
        return {"id": case.get("id", ""), "skipped": True, "reason": str(exc)}

    threshold = float(case["admissibility_threshold"])
    expected = case["expected_endpoint"]
    forbidden = case["forbidden_token"]

    # Boundary-only leg.
    boundary: GenerationResult = generate_walk(
        seed_state, vocab, persona,
        max_tokens=1, region=region,
        inner_loop_admissibility=False,
        admissibility_threshold=threshold,
    )
    b_step = boundary.admissibility_trace[0]
    boundary_selected = b_step.selected_word
    boundary_admitted = b_step.verdict.admitted
    # Boundary expectation: selects the forbidden decoy and verdict is
    # NOT admitted (the rejection is visible in trace but the walk
    # still emits it — this is ADR-0023 boundary-only behavior).
    boundary_picks_forbidden = boundary_selected == forbidden
    boundary_verdict_rejects = not boundary_admitted

    # Inner-loop leg.
    inner: GenerationResult | None = None
    inner_exhaust_reason = ""
    try:
        inner = generate_walk(
            seed_state, vocab, persona,
            max_tokens=1, region=region,
            inner_loop_admissibility=True,
            admissibility_threshold=threshold,
        )
    except ValueError as exc:
        inner_exhaust_reason = str(exc)

    if inner is None:
        return {
            "id": case.get("id", ""),
            "skipped": False,
            "passed": False,
            "boundary_selected": boundary_selected,
            "boundary_picks_forbidden": boundary_picks_forbidden,
            "boundary_verdict_rejects": boundary_verdict_rejects,
            "inner_selected": None,
            "inner_admitted": None,
            "inner_exhausted": True,
            "inner_exhaust_reason": inner_exhaust_reason,
            "rejection_in_trace": False,
            "rejected_attempts": (),
            "rationale": case.get("rationale", ""),
        }

    i_step = inner.admissibility_trace[0]
    inner_selected = i_step.selected_word
    inner_admitted = i_step.verdict.admitted
    rejected_words = tuple(word for (_idx, word, _score) in i_step.rejected_attempts)
    rejection_in_trace = forbidden in rejected_words

    passed = (
        boundary_picks_forbidden
        and boundary_verdict_rejects
        and inner_selected == expected
        and inner_admitted
        and rejection_in_trace
    )

    return {
        "id": case.get("id", ""),
        "skipped": False,
        "passed": passed,
        "semantic_pair": case.get("semantic_pair", ""),
        "expected_endpoint": expected,
        "forbidden_token": forbidden,
        "boundary_selected": boundary_selected,
        "boundary_picks_forbidden": boundary_picks_forbidden,
        "boundary_verdict_rejects": boundary_verdict_rejects,
        "inner_selected": inner_selected,
        "inner_admitted": inner_admitted,
        "inner_exhausted": False,
        "rejection_in_trace": rejection_in_trace,
        "rejected_attempts": [
            [int(idx), str(word), float(score)]
            for (idx, word, score) in i_step.rejected_attempts
        ],
        "rationale": case.get("rationale", ""),
    }


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> V2Report:
    _ = config
    _ = workers  # serial — v2 corpus is small

    if not cases:
        return V2Report(metrics={}, case_details=[])

    details = [_run_case(c) for c in cases]
    n = len(details)
    skipped = sum(1 for d in details if d.get("skipped"))
    eligible = [d for d in details if not d.get("skipped")]
    passed = sum(1 for d in eligible if d.get("passed"))
    boundary_picks_forbidden_count = sum(
        1 for d in eligible if d.get("boundary_picks_forbidden")
    )
    rejection_in_trace_count = sum(
        1 for d in eligible if d.get("rejection_in_trace")
    )

    pass_rate = passed / max(len(eligible), 1)
    boundary_decoy_rate = boundary_picks_forbidden_count / max(len(eligible), 1)
    rejection_traced_rate = rejection_in_trace_count / max(len(eligible), 1)

    metrics: dict[str, Any] = {
        "case_count": n,
        "skipped_count": skipped,
        "eligible_count": len(eligible),
        "pass_count": passed,
        "pass_rate": round(pass_rate, 4),
        "boundary_decoy_rate": round(boundary_decoy_rate, 4),
        "rejection_traced_rate": round(rejection_traced_rate, 4),
        # Headline: do we have causal evidence that inner-loop rejection
        # is responsible for the selection difference?
        "mechanism_isolated": (
            pass_rate == 1.0
            and boundary_decoy_rate == 1.0
            and rejection_traced_rate == 1.0
        ),
    }
    return V2Report(metrics=metrics, case_details=details)
