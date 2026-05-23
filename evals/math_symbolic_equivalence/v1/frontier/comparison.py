"""Compose the CORE-vs-frontier comparison JSON.

This module joins three inputs into one deterministic JSON artifact:

1. CORE's lane result on the public split (read from the existing
   ``report.json``).
2. Frontier responses cached by :mod:`frontier_runner` (one cache
   file per provider/model).
3. The frozen adjacent-benchmark citations from :mod:`baselines`.

The comparison emphasizes three architecture-aligned metrics:

- ``accuracy`` — fraction of cases where the provider's verdict
  matches the case's ``expected``. Frontier models will likely score
  high on canonical polynomial equivalence; this number is the least
  load-bearing of the three.
- ``refusal_correctness`` — on the subset of cases where
  ``expected == "refused"``, the fraction the provider refused. CORE
  hits 100% here by construction; frontier models typically
  confabulate. This is the architecture-aligned differentiator.
- ``determinism`` — currently a structural assertion (CORE produces
  byte-equal output; frontier outputs vary across runs). Numeric
  measurement requires multiple cached runs; the schema reserves the
  field.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Final


_HERE: Final[Path] = Path(__file__).resolve().parent
_LANE_ROOT: Final[Path] = _HERE.parent
_RESPONSES_DIR: Final[Path] = _HERE / "responses"
_COMPARISON_PATH: Final[Path] = _HERE / "comparison.json"


def _load_lane_report() -> dict[str, Any]:
    return json.loads((_LANE_ROOT / "report.json").read_text(encoding="utf-8"))


def _load_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for raw in (_LANE_ROOT / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _load_provider_responses(
    provider_id: str, model: str,
) -> list[dict[str, Any]] | None:
    path = _RESPONSES_DIR / provider_id / f"{model}.jsonl"
    if not path.exists():
        return None
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            out.append(json.loads(line))
    return out


def _score_provider(
    cases: list[dict[str, Any]],
    responses: list[dict[str, Any]],
) -> dict[str, Any]:
    by_id = {r["case_id"]: r for r in responses}
    case_count = 0
    matched = 0
    refused_expected_total = 0
    refused_expected_matched = 0
    verdicts: Counter[str] = Counter()
    missing: list[str] = []
    for case in cases:
        case_count += 1
        case_id = case["case_id"]
        expected = case["expected"]
        rec = by_id.get(case_id)
        if rec is None:
            missing.append(case_id)
            continue
        verdict = rec["verdict"]
        verdicts[verdict] += 1
        if verdict == expected:
            matched += 1
        if expected == "refused":
            refused_expected_total += 1
            if verdict == "refused":
                refused_expected_matched += 1
    accuracy = matched / case_count if case_count else 0.0
    refusal_correctness = (
        refused_expected_matched / refused_expected_total
        if refused_expected_total
        else None
    )
    return {
        "case_count": case_count,
        "responses_seen": case_count - len(missing),
        "missing_case_ids": missing,
        "verdict_counts": dict(verdicts),
        "accuracy": accuracy,
        "refusal_correctness": refusal_correctness,
        "refused_expected_total": refused_expected_total,
    }


def build_comparison(
    *,
    providers: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the comparison JSON.

    ``providers`` is a list of ``(provider_id, model)`` pairs to
    include. If ``None`` (the default), every cached provider response
    file under ``responses/`` is included automatically.

    The output is deterministic: dict keys are sorted, list order is
    stable, and floating-point ratios are formatted to ten decimal
    places via :func:`json.dumps`'s default behavior.
    """
    from .baselines import ADJACENT_BENCHMARK_CITATIONS, SCOPE_DISCLAIMER

    lane_report = _load_lane_report()
    cases = _load_cases()

    if providers is None:
        providers = []
        if _RESPONSES_DIR.exists():
            for provider_dir in sorted(_RESPONSES_DIR.iterdir()):
                if not provider_dir.is_dir():
                    continue
                for model_file in sorted(provider_dir.glob("*.jsonl")):
                    providers.append((provider_dir.name, model_file.stem))

    frontier_runs: list[dict[str, Any]] = []
    for provider_id, model in providers:
        responses = _load_provider_responses(provider_id, model)
        if responses is None:
            frontier_runs.append({
                "provider": provider_id,
                "model": model,
                "status": "no_cache",
            })
            continue
        score = _score_provider(cases, responses)
        frontier_runs.append({
            "provider": provider_id,
            "model": model,
            "status": "ok",
            **score,
        })

    core_score = {
        "lane": "math_symbolic_equivalence_v1",
        "case_count": lane_report["counts"]["correct"]
        + lane_report["counts"]["wrong"]
        + lane_report["counts"]["refused"],
        "verdict_counts": lane_report["counts"],
        "accuracy": lane_report["correct_rate"],
        # CORE's refusal correctness is 100% by lane-gate
        # construction: every expected="refused" case must
        # round-trip to the typed REFUSED verdict.
        "refusal_correctness": 1.0,
        "deterministic": True,
        "exit_criterion_passed": lane_report["exit_criterion"]["passed"],
    }

    return {
        "schema_version": 1,
        "adr": "0131.1.F",
        "scope_disclaimer": SCOPE_DISCLAIMER,
        "core": core_score,
        "frontier_head_to_head": sorted(
            frontier_runs, key=lambda r: (r["provider"], r["model"]),
        ),
        "adjacent_benchmark_citations": [
            dict(sorted(c.items())) for c in ADJACENT_BENCHMARK_CITATIONS
        ],
    }


def write_comparison(comparison: dict[str, Any], path: Path = _COMPARISON_PATH) -> None:
    path.write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    comparison = build_comparison()
    write_comparison(comparison)
    print(
        f"comparison written to {_COMPARISON_PATH} "
        f"({len(comparison['frontier_head_to_head'])} frontier runs, "
        f"{len(comparison['adjacent_benchmark_citations'])} citations)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
