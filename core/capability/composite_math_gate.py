"""ADR-0131.4 — Composite math-expert promotion gate (Benchmark 1+2+3).

Implements the *math-specific* revision of the ``expert`` promotion
contract that ADR-0131 introduces. The full ADR-0120 contract (10
ADR-0114a obligations + 3 composition gates) is NOT implemented
here — most of its substrate (perturbation, depth curve, adversarial,
OOD ratio) is not yet built for ``mathematics_logic``. This module
implements only the load-bearing piece ADR-0131 changes:

  ADR-0120 single-benchmark check
      `correct_rate ≥ 0.60` on public AND sealed GSM8K
  --------------------------------------------------- REPLACED BY ----
  ADR-0131 composite check (this module)
      Benchmark 1 (math_symbolic_equivalence/v1): public + sealed,
        each ``correct_rate ≥ 0.95 AND wrong == 0``
      Benchmark 2 (math_teaching_corpus/v1):
        ``correct_rate ≥ 0.95 AND wrong == 0``
      Benchmark 3 (math_bounded_grammar/v1):
        ``correct_rate ≥ 0.95 AND wrong == 0``

Plus honest disclosure: the GSM8K coverage probe's
``admitted_solved`` / ``admitted_wrong`` are reported in the
``expert_claims`` artifact under ``honest_disclosure`` — they do NOT
gate, per ADR-0131 ("GSM8K is retained as a stress-test lane that
the math expert runs but is not gated on. ... reported in the
expert-claims artifact as honest disclosure").

The gate is a pure function over already-committed lane report
JSON. No I/O beyond reading those reports. Deterministic — same
inputs produce byte-equal verdict (after sort_keys + indent=2
serialization).

This module composes with — but does not implement — the broader
ADR-0120 contract. A future ``core/capability/expert_promotion.py``
that implements all 10 ADR-0114a obligations will consume
:func:`evaluate_composite_math_gate` as the math-specific
substitute for the single-lane coverage check.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


# Thresholds pinned by ADR-0131's "Composite expert-promotion gate"
# table. Changing them requires a new ADR amending ADR-0131.
CORRECT_RATE_MIN: float = 0.95
WRONG_MAX: int = 0


# Repository root inferred from this module's location:
# core/capability/composite_math_gate.py -> ../../.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Default benchmark report paths. The evaluator accepts override
# paths so tests can point at fixture data without touching main's
# committed artifacts.
DEFAULT_B1_PUBLIC: Path = _REPO_ROOT / "evals" / "math_symbolic_equivalence" / "v1" / "report.json"
DEFAULT_B1_SEALED: Path = _REPO_ROOT / "evals" / "math_symbolic_equivalence" / "v1" / "sealed_report.json"
DEFAULT_B2: Path = _REPO_ROOT / "evals" / "math_teaching_corpus" / "v1" / "report.json"
DEFAULT_B3: Path = _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "report.json"
DEFAULT_GSM8K_PROBE: Path = _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "train_sample_coverage_report.json"


class CompositeMathGateError(Exception):
    """Raised when a benchmark report cannot be located, parsed, or
    canonicalized into the shape this gate consumes."""


@dataclass(frozen=True, slots=True)
class BenchmarkVerdict:
    """Single-benchmark gate outcome."""

    benchmark_id: str
    report_path: str
    correct: int
    wrong: int
    cases_total: int
    correct_rate: float
    correct_rate_passes: bool
    wrong_count_is_zero: bool
    passed: bool
    refusal_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "report_path": self.report_path,
            "correct": self.correct,
            "wrong": self.wrong,
            "cases_total": self.cases_total,
            "correct_rate": self.correct_rate,
            "correct_rate_passes": self.correct_rate_passes,
            "wrong_count_is_zero": self.wrong_count_is_zero,
            "passed": self.passed,
            "refusal_reason": self.refusal_reason,
        }


@dataclass(frozen=True, slots=True)
class CompositeMathGateVerdict:
    """Aggregate composite-gate outcome."""

    domain: str
    benchmarks: tuple[BenchmarkVerdict, ...]
    all_benchmarks_passed: bool
    composite_gate_passed: bool
    honest_disclosure: Mapping[str, Any]
    claim_digest: str
    thresholds: Mapping[str, Any] = field(default_factory=dict)
    refusal_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "adr": "0131.4",
            "schema_version": 1,
            "domain": self.domain,
            "thresholds": dict(self.thresholds),
            "benchmarks": [b.as_dict() for b in self.benchmarks],
            "all_benchmarks_passed": self.all_benchmarks_passed,
            "composite_gate_passed": self.composite_gate_passed,
            "honest_disclosure": dict(self.honest_disclosure),
            "claim_digest": self.claim_digest,
            "refusal_reason": self.refusal_reason,
        }


def _read_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CompositeMathGateError(
            f"benchmark report missing: {path}"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CompositeMathGateError(
            f"benchmark report not valid JSON: {path}: {exc}"
        ) from exc


def _extract_counts(report: dict[str, Any]) -> tuple[int, int, int]:
    """Return ``(correct, wrong, cases_total)`` from a heterogeneous
    lane report.

    B1 (public + sealed) and B2 emit ``counts: {correct, wrong, refused}``
    and ``sample_count`` (B1 sealed + B2) or ``counts`` totalable
    (B1 public). B3 emits ``metrics: {correct, wrong, cases_total}``.
    Refuse to extract if the shape is neither — fail loudly rather than
    guess.
    """
    counts = report.get("counts")
    metrics = report.get("metrics")
    if isinstance(counts, dict) and {"correct", "wrong"}.issubset(counts.keys()):
        correct = int(counts["correct"])
        wrong = int(counts["wrong"])
        # cases_total: sum of correct + wrong + refused, or sample_count
        # if available.
        refused = int(counts.get("refused", 0))
        cases_total = correct + wrong + refused
        if "sample_count" in report and cases_total != int(report["sample_count"]):
            # Trust sample_count when present (B1 sealed/B2 ship it).
            cases_total = int(report["sample_count"])
        return correct, wrong, cases_total
    if isinstance(metrics, dict) and {"correct", "wrong"}.issubset(metrics.keys()):
        return (
            int(metrics["correct"]),
            int(metrics["wrong"]),
            int(metrics.get("cases_total", metrics["correct"] + metrics["wrong"])),
        )
    raise CompositeMathGateError(
        "benchmark report has neither counts{correct,wrong} nor "
        "metrics{correct,wrong} at the top level"
    )


def _extract_correct_rate(report: dict[str, Any]) -> float:
    """Top-level ``correct_rate`` first, then ``metrics.correct_rate``,
    then derive from counts."""
    if "correct_rate" in report:
        return float(report["correct_rate"])
    metrics = report.get("metrics")
    if isinstance(metrics, dict) and "correct_rate" in metrics:
        return float(metrics["correct_rate"])
    correct, wrong, total = _extract_counts(report)
    if total == 0:
        return 0.0
    return correct / total


def _evaluate_one(benchmark_id: str, path: Path) -> BenchmarkVerdict:
    try:
        report = _read_report(path)
        correct, wrong, total = _extract_counts(report)
        rate = _extract_correct_rate(report)
    except CompositeMathGateError as exc:
        return BenchmarkVerdict(
            benchmark_id=benchmark_id,
            report_path=str(path),
            correct=0,
            wrong=0,
            cases_total=0,
            correct_rate=0.0,
            correct_rate_passes=False,
            wrong_count_is_zero=False,
            passed=False,
            refusal_reason=str(exc),
        )
    rate_passes = rate >= CORRECT_RATE_MIN
    wrong_zero = wrong <= WRONG_MAX
    return BenchmarkVerdict(
        benchmark_id=benchmark_id,
        report_path=str(path),
        correct=correct,
        wrong=wrong,
        cases_total=total,
        correct_rate=rate,
        correct_rate_passes=rate_passes,
        wrong_count_is_zero=wrong_zero,
        passed=rate_passes and wrong_zero,
        refusal_reason=(
            "" if (rate_passes and wrong_zero)
            else f"correct_rate={rate:.4f} (min {CORRECT_RATE_MIN}), wrong={wrong} (max {WRONG_MAX})"
        ),
    )


def _gsm8k_honest_disclosure(path: Path) -> dict[str, Any]:
    """Read the GSM8K coverage probe report and return the
    honest-disclosure subset. Per ADR-0131, GSM8K is reported but
    does NOT gate.
    """
    if not path.exists():
        return {
            "probe_path": str(path),
            "available": False,
            "note": "probe report missing; honest disclosure unavailable",
        }
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "probe_path": str(path),
            "available": False,
            "note": f"probe report unparseable: {exc}",
        }
    metrics = report.get("metrics", {})
    return {
        "probe_path": str(path),
        "available": True,
        "admitted_solved": metrics.get("admitted_solved", 0),
        "admitted_wrong": metrics.get("admitted_wrong", 0),
        "refused": metrics.get("refused", 0),
        "cases_total": metrics.get("cases_total", 0),
        "admission_rate": metrics.get("admission_rate", 0.0),
        "safety_rail_intact": metrics.get("safety_rail_intact", False),
        "substrate": report.get("substrate", "legacy"),
    }


def _compute_claim_digest(
    benchmarks: tuple[BenchmarkVerdict, ...],
    honest_disclosure: Mapping[str, Any],
) -> str:
    """Reproducible SHA-256 over the canonical evidence bundle.

    Per ADR-0120's "Signed expert_claims entry with reproducible
    digest" requirement — every reviewer should be able to compute
    the same digest from the same lane reports.
    """
    canonical = {
        "schema_version": 1,
        "adr": "0131.4",
        "benchmarks": [b.as_dict() for b in benchmarks],
        "honest_disclosure": dict(honest_disclosure),
        "thresholds": {
            "correct_rate_min": CORRECT_RATE_MIN,
            "wrong_max": WRONG_MAX,
        },
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evaluate_composite_math_gate(
    *,
    b1_public_path: Path = DEFAULT_B1_PUBLIC,
    b1_sealed_path: Path = DEFAULT_B1_SEALED,
    b2_path: Path = DEFAULT_B2,
    b3_path: Path = DEFAULT_B3,
    gsm8k_probe_path: Path = DEFAULT_GSM8K_PROBE,
) -> CompositeMathGateVerdict:
    """Evaluate the ADR-0131 composite math-expert gate.

    Returns a :class:`CompositeMathGateVerdict` with per-benchmark
    breakdown, the composite verdict, GSM8K honest-disclosure, and
    a reproducible claim digest. Pure function over file paths; no
    side effects.
    """
    benchmarks = (
        _evaluate_one("B1_public", b1_public_path),
        _evaluate_one("B1_sealed", b1_sealed_path),
        _evaluate_one("B2_teaching_corpus", b2_path),
        _evaluate_one("B3_bounded_grammar", b3_path),
    )
    all_passed = all(b.passed for b in benchmarks)
    honest = _gsm8k_honest_disclosure(gsm8k_probe_path)
    digest = _compute_claim_digest(benchmarks, honest)
    refusal = ""
    if not all_passed:
        failing = [b.benchmark_id for b in benchmarks if not b.passed]
        refusal = f"benchmarks failing the gate: {failing}"
    return CompositeMathGateVerdict(
        domain="mathematics_logic",
        benchmarks=benchmarks,
        all_benchmarks_passed=all_passed,
        composite_gate_passed=all_passed,
        honest_disclosure=honest,
        claim_digest=digest,
        thresholds={
            "correct_rate_min": CORRECT_RATE_MIN,
            "wrong_max": WRONG_MAX,
        },
        refusal_reason=refusal,
    )


def emit_expert_claims_artifact(
    verdict: CompositeMathGateVerdict,
    out_path: Path,
) -> None:
    """Write the deterministic ``expert_claims`` artifact.

    Per ADR-0120: "Signed expert_claims entry with reproducible
    digest". This emits the unsigned artifact; reviewer signature
    is added by a separate ADR-0092 reviewer-registry path that
    is out of scope for ADR-0131.4.
    """
    payload = verdict.as_dict()
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
