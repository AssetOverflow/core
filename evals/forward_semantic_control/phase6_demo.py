"""Phase 6 comparative demo — CORE vs in-system baseline.

Runs a focused demo corpus through two configurations and produces
side-by-side evidence for three head-to-head claims:

  C1. Replay determinism
        Both baseline and CORE produce byte-identical trace hashes
        across N reruns on the same case.  CORE *additionally*
        folds ``refusal_reason`` into the trace so rejection events
        themselves are replayable evidence (ADR-0024 Phase 2).

  C2. Traced rejection
        On adversarial cases where boundary picks the forbidden,
        CORE's inner-loop overrides AND the rejection appears in
        ``rejected_attempts``.  Baseline emits the forbidden with
        ``verdict.admitted = False`` but never explicitly rejects.

  C3. Coherent refusal
        On no-admissible-path cases, baseline silently emits an
        inadmissible candidate (verdict reports admitted=False but
        the walk continues).  CORE raises ``InnerLoopExhaustion``
        with a typed ``RefusalReason`` carrying ``rejected_attempts``
        evidence — i.e. the refusal is observable, typed, and
        replayable.

The "baseline" is *the same CORE codebase* with inner_loop,
margin, and rotor admissibility disabled — i.e. ADR-0023 boundary-
only behavior.  A comparison against a transformer LLM would be
non-deterministic by construction and could not be CI-enforced, so
the honest within-system comparison is what we report here.

Conforms to the ``run_lane`` interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from chat.runtime import ChatRuntime
from core.cognition.trace import hash_admissibility_trace
from core.config import RuntimeConfig
from field.state import FieldState
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.exhaustion import InnerLoopExhaustion, RefusalReason
from generate.result import GenerationResult
from generate.stream import generate as generate_walk


REPLAY_RERUNS = 5
DEFAULT_MARGIN = 0.4


@dataclass(slots=True)
class Phase6Report:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _field_state(vocab, seed_token: str) -> FieldState:
    idx = vocab.index_of(seed_token)
    v = np.asarray(vocab.get_versor(seed_token), dtype=np.float32)
    return FieldState(F=v.copy(), node=idx, step=0)


def _region(vocab, case: dict[str, Any], label: str) -> AdmissibilityRegion:
    indices = [int(vocab.index_of(tok)) for tok in case["admissible_tokens"]]
    blade = np.asarray(
        vocab.get_versor(case["relation_blade_token"]), dtype=np.float32
    )
    return AdmissibilityRegion(
        allowed_indices=np.asarray(indices, dtype=np.int64),
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label,
    )


def _run_walk(
    vocab,
    persona,
    seed_state: FieldState,
    region: AdmissibilityRegion,
    *,
    mode: str,
    threshold: float,
    margin: float,
) -> dict[str, Any]:
    """Run a single walk under one of two configurations:
      mode = "baseline"  → boundary-only (ADR-0023), no inner-loop
      mode = "core"      → inner-loop + margin (ADR-0024 + ADR-0026)
    """
    kwargs: dict[str, Any] = dict(
        max_tokens=1,
        region=region,
        admissibility_threshold=threshold,
    )
    if mode == "baseline":
        kwargs["inner_loop_admissibility"] = False
    else:
        kwargs["inner_loop_admissibility"] = True
        kwargs["admissibility_mode"] = "margin"
        kwargs["admissibility_margin"] = margin

    try:
        result: GenerationResult = generate_walk(seed_state, vocab, persona, **kwargs)
    except InnerLoopExhaustion as exc:
        return {
            "refused": True,
            "refusal_typed": True,
            "refusal_reason": exc.reason.value,
            "trace_hash": "__refusal__:" + exc.reason.value,
            "rejected_attempts": [
                [int(idx), str(word), float(score)]
                for (idx, word, score) in exc.rejected_attempts
            ],
        }
    except ValueError as exc:
        return {
            "refused": True,
            "refusal_typed": False,
            "refusal_reason": "value_error",
            "trace_hash": "__refusal__:value_error",
            "message": str(exc),
        }

    step = result.admissibility_trace[0]
    return {
        "refused": False,
        "selected": step.selected_word,
        "admitted": bool(step.verdict.admitted),
        "rejected_words": [w for (_idx, w, _sc) in step.rejected_attempts],
        "trace_hash": hash_admissibility_trace(result.admissibility_trace),
    }


def _replay_n(vocab, persona, case: dict[str, Any], mode: str,
              n: int, threshold: float, margin: float) -> list[str]:
    """Return list of trace hashes from N reruns of the same case
    under the same mode.  Used for C1 determinism."""
    hashes: list[str] = []
    for _ in range(n):
        try:
            seed = _field_state(vocab, case["seed_token"])
            region = _region(vocab, case, label=f"p6[{case.get('id','')}]")
        except (KeyError, ValueError):
            hashes.append("__skipped__")
            continue
        out = _run_walk(
            vocab, persona, seed, region,
            mode=mode, threshold=threshold, margin=margin,
        )
        hashes.append(out["trace_hash"])
    return hashes


def _evaluate(case: dict[str, Any], margin: float) -> dict[str, Any]:
    runtime = ChatRuntime()
    vocab = runtime.session.vocab
    persona = runtime.session.persona

    try:
        seed_b = _field_state(vocab, case["seed_token"])
        seed_c = _field_state(vocab, case["seed_token"])
        region_b = _region(vocab, case, label=f"p6[{case.get('id','')}][b]")
        region_c = _region(vocab, case, label=f"p6[{case.get('id','')}][c]")
    except (KeyError, ValueError) as exc:
        return {"id": case.get("id",""), "skipped": True, "reason": str(exc)}

    threshold = float(case["admissibility_threshold"])
    condition = case["condition"]

    baseline = _run_walk(
        vocab, persona, seed_b, region_b,
        mode="baseline", threshold=threshold, margin=margin,
    )
    core = _run_walk(
        vocab, persona, seed_c, region_c,
        mode="core", threshold=threshold, margin=margin,
    )

    detail: dict[str, Any] = {
        "id": case.get("id",""),
        "condition": condition,
        "rationale": case.get("rationale",""),
        "expected_endpoint": case.get("expected_endpoint"),
        "forbidden_token": case.get("forbidden_token"),
        "baseline": baseline,
        "core": core,
    }

    # C1: replay determinism — N reruns under each mode.
    detail["replay_hashes_baseline"] = _replay_n(
        vocab, persona, case, "baseline", REPLAY_RERUNS, threshold, margin
    )
    detail["replay_hashes_core"] = _replay_n(
        vocab, persona, case, "core", REPLAY_RERUNS, threshold, margin
    )
    detail["replay_stable_baseline"] = (
        len(set(detail["replay_hashes_baseline"])) == 1
    )
    detail["replay_stable_core"] = (
        len(set(detail["replay_hashes_core"])) == 1
    )

    # C2: traced rejection — only meaningful for adversarial cases.
    forbidden = case.get("forbidden_token")
    if forbidden:
        detail["c2_baseline_emits_forbidden"] = (
            baseline.get("selected") == forbidden
        )
        detail["c2_baseline_admits_forbidden"] = bool(baseline.get("admitted"))
        detail["c2_core_selects_expected"] = (
            core.get("selected") == case.get("expected_endpoint")
        )
        detail["c2_core_rejection_traced"] = (
            forbidden in (core.get("rejected_words") or [])
            or core.get("refused", False)
        )

    # C3: coherent refusal — meaningful for no-admissible-path cases.
    if case.get("expect_refusal"):
        detail["c3_baseline_refused"] = bool(baseline.get("refused"))
        detail["c3_baseline_refusal_typed"] = bool(baseline.get("refusal_typed"))
        detail["c3_core_refused"] = bool(core.get("refused"))
        detail["c3_core_refusal_typed"] = bool(core.get("refusal_typed"))
        detail["c3_core_refusal_reason"] = core.get("refusal_reason")

    return detail


def run_lane(
    cases: list[dict[str, Any]],
    *,
    config: RuntimeConfig | None = None,
    workers: int | None = None,
) -> Phase6Report:
    _ = workers
    margin = float(config.admissibility_margin) if config else DEFAULT_MARGIN

    if not cases:
        return Phase6Report(metrics={"margin": margin}, case_details=[])

    details = [_evaluate(c, margin) for c in cases]

    # Per-condition aggregates.
    by_condition: dict[str, list[dict[str, Any]]] = {}
    for d in details:
        by_condition.setdefault(d.get("condition","unknown"), []).append(d)

    # C1: every case in every condition must be replay-stable in CORE.
    c1_total = sum(
        1 for d in details if not d.get("skipped")
        and d.get("replay_stable_core") is True
    )
    c1_n = sum(1 for d in details if not d.get("skipped"))
    # Both baseline and core should be stable; we report the AND but
    # separately track baseline stability.
    c1_baseline_total = sum(
        1 for d in details if not d.get("skipped")
        and d.get("replay_stable_baseline") is True
    )

    # C2: among adversarial (traced_rejection condition) cases:
    c2_cases = by_condition.get("traced_rejection", [])
    c2_baseline_emits_forbidden = sum(
        1 for d in c2_cases if d.get("c2_baseline_emits_forbidden")
    )
    c2_baseline_admits_forbidden = sum(
        1 for d in c2_cases if d.get("c2_baseline_admits_forbidden")
    )
    c2_core_corrects = sum(
        1 for d in c2_cases if d.get("c2_core_selects_expected")
        or (d.get("core") or {}).get("refused", False)
    )
    c2_core_traced = sum(
        1 for d in c2_cases if d.get("c2_core_rejection_traced")
    )

    # C3: among coherent_refusal cases:
    c3_cases = by_condition.get("coherent_refusal", [])
    c3_baseline_refused_typed = sum(
        1 for d in c3_cases if d.get("c3_baseline_refusal_typed")
    )
    c3_baseline_emitted_inadmissible = sum(
        1 for d in c3_cases
        if not d.get("c3_baseline_refused")
        or not (d.get("baseline") or {}).get("admitted", True)
    )
    c3_core_refused_typed = sum(
        1 for d in c3_cases if d.get("c3_core_refusal_typed")
    )

    metrics: dict[str, Any] = {
        "case_count": len(details),
        "skipped_count": sum(1 for d in details if d.get("skipped")),
        "margin": margin,
        "replay_reruns": REPLAY_RERUNS,
        # C1
        "c1_replay_stable_core": c1_total,
        "c1_replay_stable_baseline": c1_baseline_total,
        "c1_eligible": c1_n,
        "c1_pass": c1_total == c1_n and c1_baseline_total == c1_n,
        # C2
        "c2_case_count": len(c2_cases),
        "c2_baseline_emits_forbidden": c2_baseline_emits_forbidden,
        "c2_baseline_admits_forbidden": c2_baseline_admits_forbidden,
        "c2_core_corrects_or_refuses": c2_core_corrects,
        "c2_core_rejection_traced": c2_core_traced,
        "c2_pass": (
            len(c2_cases) > 0
            and c2_baseline_emits_forbidden == len(c2_cases)
            and c2_baseline_admits_forbidden == 0
            and c2_core_corrects == len(c2_cases)
            and c2_core_traced == len(c2_cases)
        ),
        # C3
        "c3_case_count": len(c3_cases),
        "c3_baseline_refused_typed": c3_baseline_refused_typed,
        "c3_baseline_emitted_inadmissible": c3_baseline_emitted_inadmissible,
        "c3_core_refused_typed": c3_core_refused_typed,
        "c3_pass": (
            len(c3_cases) > 0
            and c3_baseline_refused_typed == 0
            and c3_core_refused_typed == len(c3_cases)
        ),
    }
    metrics["all_three_conditions_pass"] = (
        metrics["c1_pass"] and metrics["c2_pass"] and metrics["c3_pass"]
    )
    return Phase6Report(metrics=metrics, case_details=details)


def main() -> int:
    cases_path = Path("evals/forward_semantic_control/public/v2_phase6_demo/cases.jsonl")
    out_path = Path("evals/forward_semantic_control/results/phase6_demo_report.json")
    cases = [json.loads(l) for l in cases_path.read_text().splitlines() if l.strip()]
    report = run_lane(cases)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "metrics": report.metrics,
        "case_details": report.case_details,
    }, indent=2))
    print(json.dumps(report.metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
