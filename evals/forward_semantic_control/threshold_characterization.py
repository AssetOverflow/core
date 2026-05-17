"""Phase 4 threshold characterization — ADR-0024 diagnostic, not tuning.

The Phase 2 report on the existing FSC v1 corpus surfaced
``exhaustion_rate=0.33 at t=0.0`` and ``exhaustion_rate=0.56 at
t=0.25`` — well above the 5% ceiling.  Before proposing a learned or
adaptive threshold, we need to know *whether the geometry permits a
clean threshold at all*.

This module produces a distribution-map diagnostic, NOT a tuned
threshold:

  * For each case in v1+dev, build the same region the inner-loop
    runner builds (chain outer-product over chain_tokens).
  * For every candidate index in the admissible set, compute its
    ``cga_inner`` score against the relation_blade.
  * Group scores by whether the candidate is "correct" (== the
    expected_endpoint) or "incorrect" (anything else admissible).
  * Sweep thresholds [-1.0, -0.5, 0.0, 0.1, 0.25, 0.5, 1.0] and
    report, per threshold:
        admitted_correct      / total_correct        (TP rate)
        admitted_incorrect    / total_incorrect      (FP rate)
        rejected_correct      / total_correct        (FN rate)
        rejected_incorrect    / total_incorrect      (TN rate)
        separation_quality    = TP_rate - FP_rate

  * Also report admitted-vs-rejected score *distribution* maps:
        admitted_score_mean / median / min / max  per correctness class
        rejected_score_mean / median / min / max  per correctness class
        score_overlap_ratio  = (max(correct_rejected_min, incorrect_admitted_min)
                                - min(correct_admitted_max, incorrect_rejected_max))
                              normalized

  * The headline finding is whether ANY threshold delivers
    ``separation_quality >= 0.8`` on the corpus.  If not, the
    relation_blade construction is geometrically under-resolved for
    static thresholding regardless of value.

This is a Phase 4 diagnostic that informs whether ADR-0025 should
even attempt static thresholds or move directly to relation-typed
or frame-derived schemes.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from algebra.cga import cga_inner, outer_product
from chat.runtime import ChatRuntime

THRESHOLDS = (-1.0, -0.5, 0.0, 0.1, 0.25, 0.5, 1.0)
SEPARATION_QUALITY_GATE = 0.8


@dataclass(slots=True)
class CharacterizationReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    per_threshold: dict[float, dict[str, Any]] = field(default_factory=dict)
    score_distributions: dict[str, dict[str, Any]] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _build_blade(vocab, chain_tokens: tuple[str, ...]) -> tuple[np.ndarray | None, list[int]]:
    indices: list[int] = []
    versors: list[np.ndarray] = []
    for raw in chain_tokens:
        token = raw.lower().strip()
        if not token:
            continue
        try:
            idx = vocab.index_of(token)
            versor = np.asarray(vocab.get_versor(token), dtype=np.float32)
        except (KeyError, AttributeError):
            continue
        indices.append(int(idx))
        versors.append(versor)
    if not versors:
        return None, []
    blade = versors[0]
    for nxt in versors[1:]:
        blade = outer_product(blade, nxt)
    return blade, indices


def _score_candidates(
    vocab,
    blade: np.ndarray,
    indices: list[int],
    expected_token: str,
) -> tuple[list[float], list[float]]:
    """Return (correct_scores, incorrect_scores) for candidates in admissible set."""
    correct: list[float] = []
    incorrect: list[float] = []
    expected_idx: int | None = None
    try:
        expected_idx = int(vocab.index_of(expected_token.lower().strip()))
    except (KeyError, AttributeError, ValueError):
        expected_idx = None
    for idx in indices:
        v = np.asarray(vocab.get_versor_at(idx), dtype=np.float32)
        score = float(cga_inner(v, blade))
        if expected_idx is not None and idx == expected_idx:
            correct.append(score)
        else:
            incorrect.append(score)
    return correct, incorrect


def _summarize(scores: list[float]) -> dict[str, Any]:
    if not scores:
        return {"count": 0}
    return {
        "count": len(scores),
        "mean": round(statistics.mean(scores), 4),
        "median": round(statistics.median(scores), 4),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "stdev": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
    }


def _blade_and_indices_for_case(
    vocab, case: dict[str, Any]
) -> tuple[np.ndarray | None, list[int], str]:
    """Build the blade + admissible indices for either schema.

    Returns ``(blade, indices, expected_token)`` or ``(None, [], "")``
    if the case cannot be grounded in the active vocab.
    """
    expected = case.get("expected_endpoint", "")
    # v2 schema: explicit admissible_tokens + relation_blade_token.
    if "admissible_tokens" in case and "relation_blade_token" in case:
        try:
            blade = np.asarray(
                vocab.get_versor(case["relation_blade_token"]), dtype=np.float32
            )
            indices = [int(vocab.index_of(tok)) for tok in case["admissible_tokens"]]
        except (KeyError, AttributeError, ValueError):
            return None, [], ""
        return blade, indices, expected
    # v1 schema: chain_tokens outer-product, or single-token fallback.
    chain_tokens = tuple(case.get("chain_tokens", ()))
    if not chain_tokens and expected:
        chain_tokens = (expected,)
    blade, indices = _build_blade(vocab, chain_tokens)
    return blade, indices, expected


def characterize(cases: list[dict[str, Any]]) -> CharacterizationReport:
    runtime = ChatRuntime()
    vocab = runtime.session.vocab

    case_details: list[dict[str, Any]] = []
    all_correct: list[float] = []
    all_incorrect: list[float] = []

    for case in cases:
        blade, indices, expected = _blade_and_indices_for_case(vocab, case)
        if blade is None or not indices:
            case_details.append({"id": case.get("id", ""), "skipped": True})
            continue
        correct, incorrect = _score_candidates(vocab, blade, indices, expected)
        all_correct.extend(correct)
        all_incorrect.extend(incorrect)
        case_details.append({
            "id": case.get("id", ""),
            "correct_scores": [round(s, 4) for s in correct],
            "incorrect_scores": [round(s, 4) for s in incorrect],
        })

    per_threshold: dict[float, dict[str, Any]] = {}
    for thr in THRESHOLDS:
        tp = sum(1 for s in all_correct if s >= thr)
        fn = sum(1 for s in all_correct if s < thr)
        fp = sum(1 for s in all_incorrect if s >= thr)
        tn = sum(1 for s in all_incorrect if s < thr)
        tot_c = max(len(all_correct), 1)
        tot_i = max(len(all_incorrect), 1)
        tp_rate = tp / tot_c
        fp_rate = fp / tot_i
        per_threshold[thr] = {
            "TP": tp, "FN": fn, "FP": fp, "TN": tn,
            "TP_rate": round(tp_rate, 4),
            "FP_rate": round(fp_rate, 4),
            "FN_rate": round(fn / tot_c, 4),
            "TN_rate": round(tn / tot_i, 4),
            "separation_quality": round(tp_rate - fp_rate, 4),
        }

    score_distributions = {
        "correct": _summarize(all_correct),
        "incorrect": _summarize(all_incorrect),
    }

    # Overlap diagnostic: is there *any* gap between the worst correct
    # and the best incorrect?
    overlap_ratio = 0.0
    if all_correct and all_incorrect:
        cmin = min(all_correct)
        imax = max(all_incorrect)
        full_range = max(all_correct + all_incorrect) - min(all_correct + all_incorrect)
        overlap = max(imax - cmin, 0.0)
        overlap_ratio = round(overlap / full_range, 4) if full_range > 0 else 0.0
        score_distributions["overlap"] = {
            "correct_min": round(cmin, 4),
            "incorrect_max": round(imax, 4),
            "overlap_size": round(overlap, 4),
            "full_range": round(full_range, 4),
            "overlap_ratio": overlap_ratio,
            "separable_by_static_threshold": cmin > imax,
        }

    best_thr = max(
        per_threshold.items(),
        key=lambda kv: kv[1]["separation_quality"],
    )
    metrics = {
        "thresholds_swept": list(THRESHOLDS),
        "best_threshold": best_thr[0],
        "best_separation_quality": best_thr[1]["separation_quality"],
        "separation_quality_gate": SEPARATION_QUALITY_GATE,
        "passes_separation_gate": best_thr[1]["separation_quality"] >= SEPARATION_QUALITY_GATE,
        "total_correct_candidates": len(all_correct),
        "total_incorrect_candidates": len(all_incorrect),
        "overlap_ratio": overlap_ratio,
        "case_count": len(cases),
        "skipped_count": sum(1 for d in case_details if d.get("skipped")),
        # Headline finding: can a STATIC threshold separate correct from
        # incorrect on this corpus?  If no, ADR-0025 must not propose
        # static thresholds.
        "geometry_supports_static_threshold": (
            best_thr[1]["separation_quality"] >= SEPARATION_QUALITY_GATE
        ),
    }
    return CharacterizationReport(
        metrics=metrics,
        per_threshold=per_threshold,
        score_distributions=score_distributions,
        case_details=case_details,
    )


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _serialize(report: CharacterizationReport) -> dict[str, Any]:
    return {
        "metrics": report.metrics,
        "per_threshold": {str(k): v for k, v in report.per_threshold.items()},
        "score_distributions": report.score_distributions,
        "case_details": report.case_details,
    }


def main() -> None:
    v1 = _load(Path("evals/forward_semantic_control/public/v1/cases.jsonl"))
    dev = _load(Path("evals/forward_semantic_control/dev/cases.jsonl"))
    v2 = _load(Path("evals/forward_semantic_control/public/v2/cases.jsonl"))

    out_dir = Path("evals/forward_semantic_control/results")
    out_dir.mkdir(parents=True, exist_ok=True)

    bundles = [
        ("v1_plus_dev", v1 + dev),
        ("v2", v2),
        ("combined", v1 + dev + v2),
    ]
    summary: dict[str, dict[str, Any]] = {}
    for label, cases in bundles:
        if not cases:
            summary[label] = {"empty": True}
            continue
        report = characterize(cases)
        out_path = out_dir / f"phase4_characterization_{label}.json"
        with out_path.open("w") as fh:
            json.dump(_serialize(report), fh, indent=2)
        summary[label] = report.metrics
        print(f"\n=== {label} ===")
        print(f"  cases: {report.metrics['case_count']}, "
              f"skipped: {report.metrics['skipped_count']}")
        print(f"  best_threshold: {report.metrics['best_threshold']}")
        print(f"  best_separation_quality: {report.metrics['best_separation_quality']}")
        print(f"  geometry_supports_static_threshold: "
              f"{report.metrics['geometry_supports_static_threshold']}")
        print(f"  overlap_ratio: {report.metrics['overlap_ratio']}")
    with (out_dir / "phase4_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nWrote summary: {out_dir / 'phase4_summary.json'}")


if __name__ == "__main__":
    main()
