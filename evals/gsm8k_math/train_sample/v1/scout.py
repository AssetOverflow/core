"""GSM8K train-sample sealed attempt scout — measurement-only (ADR-0175 S1).

Dual-scores each train_sample case with the conservative serving scorer and the
sealed ``resolve_pooled`` aggressive scorer. Emits deterministic lift-target
evidence without mutating serving, report.json, or practice artifacts.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from evals.gsm8k_math.practice.v1.propose_runner import resolve_pooled_scorer
from evals.gsm8k_math.practice.v1.runner import classify_operation, diagnose_refusal
from evals.gsm8k_math.runner import CaseOutcome, _score_one_candidate_graph
from evals.gsm8k_math.train_sample.v1.runner import _adapt, _load_cases, _CASES_PATH
from scripts.gsm8k_frontier_report import _classify_reason, _extract_category

Status = Literal["correct", "wrong", "refused"]

_DELTA_KINDS: tuple[str, ...] = (
    "already_served",
    "serving_conservative_win",
    "serving_wrong_sealed_correct",
    "serving_wrong_other",
    "lift_refused_to_correct",
    "elimination_refused_to_wrong",
    "joint_refusal",
)

_BUCKET_PRIORITY: dict[str, int] = {
    "recognized_no_injection": 0,
    "no_admissible_statement": 1,
    "no_admissible_question": 2,
    "no_solvable_branch": 3,
    "incomplete_reading": 4,
    "other_refused": 5,
    "other": 6,
}

_PRIMITIVE_BY_NO_INJ_CATEGORY: dict[str, str] = {
    "discrete_count_statement": "relation_hypothesis",
    "multiplicative_aggregation": "multiplicative_aggregate",
    "temporal_aggregation": "temporal_tariff",
    "rate_with_currency": "rate_composition",
    "unit_partition": "unit_partition",
    "comparative_with_unit": "compare_multiplicative",
}

_EVIDENCE_SNIPPET_RE = re.compile(r"\d|half|quarter|third|twice|each|per|every", re.I)


@dataclass(frozen=True, slots=True)
class SealedAttemptScoutRow:
    case_id: str
    served_status: Status
    aggressive_status: Status
    aggressive_answer: str | None
    gold_answer: str
    refusal_reason: str | None
    failure_family: str
    candidate_lift_family: str | None
    first_failed_step: str | None
    trace_key: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "served_status": self.served_status,
            "aggressive_status": self.aggressive_status,
            "aggressive_answer": self.aggressive_answer,
            "gold_answer": self.gold_answer,
            "refusal_reason": self.refusal_reason,
            "failure_family": self.failure_family,
            "candidate_lift_family": self.candidate_lift_family,
            "first_failed_step": self.first_failed_step,
            "trace_key": self.trace_key,
        }


@dataclass(frozen=True, slots=True)
class LiftRecommendation:
    rank: int
    failure_family: str
    serving_bucket: str
    serving_no_injection_category: str | None
    operation_class: str
    lift_count: int
    case_ids: tuple[str, ...]
    candidate_primitive: str
    expected_movement: str
    safe_next_action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "failure_family": self.failure_family,
            "serving_bucket": self.serving_bucket,
            "serving_no_injection_category": self.serving_no_injection_category,
            "operation_class": self.operation_class,
            "lift_count": self.lift_count,
            "case_ids": self.case_ids,
            "candidate_primitive": self.candidate_primitive,
            "expected_movement": self.expected_movement,
            "safe_next_action": self.safe_next_action,
        }


def adapt_train_sample_case(raw: dict[str, Any]) -> dict[str, Any]:
    return _adapt(raw)


def _evidence_snippet(question: str, *, limit: int = 96) -> str:
    text = (question or "").strip()
    if len(text) <= limit:
        return text
    m = _EVIDENCE_SNIPPET_RE.search(text)
    if m is None:
        return text[:limit]
    start = max(0, m.start() - 20)
    return text[start : start + limit].strip()


def _trace_key(case_id: str, served_reason: str, sealed_reason: str) -> str:
    payload = f"{case_id}|{served_reason}|{sealed_reason}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def classify_delta_kind(served: Status, aggressive: Status) -> str:
    if served == "correct" and aggressive == "correct":
        return "already_served"
    if served == "correct" and aggressive != "correct":
        return "serving_conservative_win"
    if served == "wrong" and aggressive == "correct":
        return "serving_wrong_sealed_correct"
    if served == "wrong":
        return "serving_wrong_other"
    if served == "refused" and aggressive == "correct":
        return "lift_refused_to_correct"
    if served == "refused" and aggressive == "wrong":
        return "elimination_refused_to_wrong"
    return "joint_refusal"


def _candidate_lift_family(
    *,
    delta_kind: str,
    serving_bucket: str,
    category: str | None,
) -> str | None:
    if delta_kind != "lift_refused_to_correct":
        return None
    if category:
        primitive = _PRIMITIVE_BY_NO_INJ_CATEGORY.get(category, "diagnostic_hold")
        return f"{primitive}:{category}"
    if serving_bucket == "no_admissible_question":
        return "question_binding:peer_or_conditional"
    if serving_bucket == "incomplete_reading":
        return "completeness:unconsumed_quantity"
    return "unclassified"


def classify_failure_family(
    *,
    delta_kind: str,
    served_status: Status,
    served_reason: str,
    served_bucket: str,
    served_category: str | None,
    sealed_reason: str,
) -> str:
    diagnosis = (
        diagnose_refusal(served_reason) if served_status == "refused" else "n/a"
    )
    if delta_kind == "already_served":
        return "already_served"
    if delta_kind == "serving_conservative_win":
        return "conservative_boundary"
    if delta_kind in ("serving_wrong_sealed_correct", "serving_wrong_other"):
        return "serving_wrong_boundary"
    if delta_kind == "elimination_refused_to_wrong":
        return "sealed_elimination"
    if delta_kind == "lift_refused_to_correct":
        parts = ["lift", diagnosis, served_bucket]
        if served_category:
            parts.append(served_category)
        return "_".join(parts)
    if delta_kind == "joint_refusal":
        if "no resolution" in (sealed_reason or "").lower():
            return "joint_sealed_no_resolution"
        parts = ["joint", diagnosis, served_bucket]
        if served_category:
            parts.append(served_category)
        return "_".join(parts)
    return "unclassified"


def _first_failed_step(served_status: Status, served_reason: str) -> str | None:
    if served_status != "refused":
        return None
    low = (served_reason or "").lower()
    if "no admissible candidate for question" in low:
        return "question_parse"
    if "no admissible candidate for statement" in low:
        return "statement_parse"
    if "produced no injection" in low:
        return "recognizer_injection"
    if "no branch produced a solvable" in low:
        return "graph_solve"
    if "incomplete reading" in low:
        return "completeness_guard"
    return "unclassified"


def score_case_dual(
    raw: dict[str, Any],
    *,
    serving_scorer: Callable[[dict[str, Any]], CaseOutcome] = _score_one_candidate_graph,
    sealed_scorer: Callable[[dict[str, Any]], CaseOutcome] = resolve_pooled_scorer,
) -> tuple[CaseOutcome, CaseOutcome]:
    adapted = adapt_train_sample_case(raw)
    return serving_scorer(adapted), sealed_scorer(adapted)


def build_scout_row(
    raw: dict[str, Any],
    served: CaseOutcome,
    sealed: CaseOutcome,
) -> SealedAttemptScoutRow:
    served_status: Status = served.outcome  # type: ignore[assignment]
    aggressive_status: Status = sealed.outcome  # type: ignore[assignment]
    served_reason = served.reason or ""
    sealed_reason = sealed.reason or ""
    served_bucket = _classify_reason(served_reason)
    served_category = _extract_category(served_reason)
    delta_kind = classify_delta_kind(served_status, aggressive_status)
    failure_family = classify_failure_family(
        delta_kind=delta_kind,
        served_status=served_status,
        served_reason=served_reason,
        served_bucket=served_bucket,
        served_category=served_category,
        sealed_reason=sealed_reason,
    )
    aggressive_answer = (
        None
        if sealed.actual_answer is None
        else str(sealed.actual_answer)
    )
    return SealedAttemptScoutRow(
        case_id=raw["case_id"],
        served_status=served_status,
        aggressive_status=aggressive_status,
        aggressive_answer=aggressive_answer,
        gold_answer=str(raw["answer_numeric"]),
        refusal_reason=served_reason if served_status == "refused" else None,
        failure_family=failure_family,
        candidate_lift_family=_candidate_lift_family(
            delta_kind=delta_kind,
            serving_bucket=served_bucket,
            category=served_category,
        ),
        first_failed_step=_first_failed_step(served_status, served_reason),
        trace_key=_trace_key(raw["case_id"], served_reason, sealed_reason),
    )


def build_scout_rows(
    cases: list[dict[str, Any]],
    *,
    serving_scorer: Callable[[dict[str, Any]], CaseOutcome] | None = None,
    sealed_scorer: Callable[[dict[str, Any]], CaseOutcome] | None = None,
) -> tuple[SealedAttemptScoutRow, ...]:
    serving = serving_scorer or _score_one_candidate_graph
    sealed = sealed_scorer or resolve_pooled_scorer
    rows: list[SealedAttemptScoutRow] = []
    for raw in sorted(cases, key=lambda c: c["case_id"]):
        served, aggressive = score_case_dual(
            raw, serving_scorer=serving, sealed_scorer=sealed
        )
        rows.append(build_scout_row(raw, served, aggressive))
    return tuple(rows)


def _aggregate_counts(rows: tuple[SealedAttemptScoutRow, ...]) -> dict[str, Any]:
    serving_counts = {"correct": 0, "wrong": 0, "refused": 0}
    sealed_counts = {"correct": 0, "wrong": 0, "refused": 0}
    delta_counts: dict[str, int] = {k: 0 for k in _DELTA_KINDS}
    failure_family_counts: dict[str, int] = {}
    diagnosis_counts: dict[str, int] = {}

    for row in rows:
        serving_counts[row.served_status] += 1
        sealed_counts[row.aggressive_status] += 1
        delta_kind = classify_delta_kind(row.served_status, row.aggressive_status)
        delta_counts[delta_kind] = delta_counts.get(delta_kind, 0) + 1
        failure_family_counts[row.failure_family] = (
            failure_family_counts.get(row.failure_family, 0) + 1
        )
        if row.served_status == "refused":
            diag = diagnose_refusal(row.refusal_reason or "")
            diagnosis_counts[diag] = diagnosis_counts.get(diag, 0) + 1

    return {
        "serving_counts": serving_counts,
        "sealed_counts": sealed_counts,
        "delta_counts": dict(sorted(delta_counts.items())),
        "failure_family_counts": dict(sorted(failure_family_counts.items())),
        "diagnosis_counts": dict(sorted(diagnosis_counts.items())),
    }


def build_lift_recommendations(
    rows: tuple[SealedAttemptScoutRow, ...],
    cases_by_id: dict[str, dict[str, Any]],
    *,
    top: int | None = None,
) -> tuple[LiftRecommendation, ...]:
    lift_rows = [
        r
        for r in rows
        if r.served_status == "refused" and r.aggressive_status == "correct"
    ]
    groups: dict[tuple[str, str, str | None, str], list[SealedAttemptScoutRow]] = {}
    for row in lift_rows:
        raw = cases_by_id[row.case_id]
        op_class = classify_operation(raw.get("answer_expression", ""))
        served_bucket = _classify_reason(row.refusal_reason or "")
        category = _extract_category(row.refusal_reason or "")
        key = (row.failure_family, served_bucket, category, op_class)
        groups.setdefault(key, []).append(row)

    recs: list[LiftRecommendation] = []
    for (failure_family, bucket, category, op_class), grouped in groups.items():
        case_ids = tuple(sorted(r.case_id for r in grouped))
        primitive = (
            _PRIMITIVE_BY_NO_INJ_CATEGORY.get(category or "", "diagnostic_hold")
            if category
            else "diagnostic_hold"
        )
        movement = (
            "downstream_reclassification"
            if bucket == "recognized_no_injection" and category
            else "diagnostic_only"
        )
        action = (
            f"Injector/recognizer gap for category={category}: sealed resolve_pooled "
            f"commits correctly on {len(grouped)} train_sample cases; pursue targeted "
            f"injector lift — never wire resolve_pooled wholesale to serving."
            if category
            else (
                f"Serving refused but sealed correct on {len(grouped)} cases "
                f"({failure_family}); pursue narrow family lift with confusers."
            )
        )
        recs.append(
            LiftRecommendation(
                rank=0,
                failure_family=failure_family,
                serving_bucket=bucket,
                serving_no_injection_category=category,
                operation_class=op_class,
                lift_count=len(grouped),
                case_ids=case_ids,
                candidate_primitive=primitive,
                expected_movement=movement,
                safe_next_action=action,
            )
        )

    recs.sort(
        key=lambda rec: (
            -rec.lift_count,
            _BUCKET_PRIORITY.get(rec.serving_bucket, 99),
            rec.failure_family,
            rec.serving_no_injection_category or "",
            rec.operation_class,
        )
    )
    ranked = tuple(
        LiftRecommendation(
            rank=idx,
            failure_family=rec.failure_family,
            serving_bucket=rec.serving_bucket,
            serving_no_injection_category=rec.serving_no_injection_category,
            operation_class=rec.operation_class,
            lift_count=rec.lift_count,
            case_ids=rec.case_ids,
            candidate_primitive=rec.candidate_primitive,
            expected_movement=rec.expected_movement,
            safe_next_action=rec.safe_next_action,
        )
        for idx, rec in enumerate(recs, start=1)
    )
    if top is not None:
        return ranked[:top]
    return ranked


def build_scout_summary(
    cases: list[dict[str, Any]] | None = None,
    *,
    cases_source: str = "evals/gsm8k_math/train_sample/v1/cases.jsonl",
    serving_scorer: Callable[[dict[str, Any]], CaseOutcome] | None = None,
    sealed_scorer: Callable[[dict[str, Any]], CaseOutcome] | None = None,
    include_rows: bool = True,
    top_recommendations: int | None = None,
) -> dict[str, Any]:
    loaded = cases if cases is not None else _load_cases(_CASES_PATH)
    rows = build_scout_rows(
        loaded, serving_scorer=serving_scorer, sealed_scorer=sealed_scorer
    )
    cases_by_id = {c["case_id"]: c for c in loaded}
    aggregates = _aggregate_counts(rows)
    recommendations = build_lift_recommendations(
        rows, cases_by_id, top=top_recommendations
    )
    summary: dict[str, Any] = {
        "schema_version": 1,
        "adr": "0175",
        "regime": "sealed_attempt_scout",
        "cases_source": cases_source,
        "sample_count": len(loaded),
        **aggregates,
        "lift_recommendations": [r.as_dict() for r in recommendations],
    }
    if include_rows:
        summary["rows"] = [r.as_dict() for r in rows]
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = [
        "# GSM8K sealed attempt scout (deterministic report)",
        "",
        f"- sample: {summary['sample_count']} ({summary['cases_source']})",
    ]
    sc = summary["serving_counts"]
    ac = summary["sealed_counts"]
    lines.append(
        f"- serving: correct={sc['correct']} wrong={sc['wrong']} refused={sc['refused']}"
    )
    lines.append(
        f"- sealed (resolve_pooled): correct={ac['correct']} wrong={ac['wrong']} "
        f"refused={ac['refused']}"
    )
    lines.append("")
    lines.append("## Cross-regime deltas")
    for key, val in summary["delta_counts"].items():
        if val:
            lines.append(f"- {key}: {val}")
    lines.append("")
    lines.append("## Top lift recommendations")
    for rec in summary.get("lift_recommendations", [])[:5]:
        lines.append(
            f"- #{rec['rank']} {rec['failure_family']} (n={rec['lift_count']}, "
            f"primitive={rec['candidate_primitive']})"
        )
    lines.append("")
    lines.append(
        "safe_action: targeted injector lift only; resolve_pooled remains sealed."
    )
    return "\n".join(lines)


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")