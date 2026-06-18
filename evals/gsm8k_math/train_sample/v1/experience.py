"""GSM8K bounded experience flywheel — PR-1 practice memory layer.

Deterministic, compact, append-only experience artifacts derived from sealed
scout runs.  Measurement-only: never mutates serving, report.json, packs,
teaching corpus, or sealed practice artifacts.

Trust boundary:
  - Reads scout summaries / rows only.
  - Emits SPECULATIVE experience records for operator reuse.
  - No auto-proposal, no corpus mutation, no serving promotion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from formation.hashing import canonical_json, sha256_of

from evals.gsm8k_math.practice.v1.runner import classify_operation
from evals.gsm8k_math.train_sample.v1.runner import _CASES_PATH, _load_cases
from evals.gsm8k_math.train_sample.v1.scout import (
    SealedAttemptScoutRow,
    build_scout_summary,
    classify_delta_kind,
)

_RECOGNIZED_NO_INJ = "candidate_graph: recognizer matched but produced no injection"
_CATEGORY_RE = re.compile(r"category=([a-zA-Z0-9_]+)")
_UNKNOWN_OPERATION_CLASS = "unknown"

SCHEMA_VERSION = 1
ADR = "experience_flywheel_pr1"

Status = Literal["correct", "wrong", "refused"]
PromotionStatus = Literal[
    "not_promotable",
    "candidate",
    "blocked_by_wrong_risk",
    "promoted_in_pr",
    "superseded",
]

_HIGH_FREQ_JOINT_THRESHOLD = 3

_HAZARD_BY_DELTA: dict[str, tuple[str, ...]] = {
    "elimination_refused_to_wrong": ("sealed_elimination", "wrong_risk"),
    "serving_wrong_sealed_correct": ("serving_wrong_boundary",),
    "serving_wrong_other": ("serving_wrong_boundary",),
    "serving_conservative_win": ("conservative_boundary",),
}

_BLOCKED_HAZARDS: frozenset[str] = frozenset(
    {
        "sealed_elimination",
        "wrong_risk",
        "serving_wrong_boundary",
        "unblocked_ambiguity",
        "unbound_target",
        "unbound_unit",
    }
)

_PRIMITIVE_BY_CATEGORY: dict[str, str] = {
    "discrete_count_statement": "relation_hypothesis",
    "multiplicative_aggregation": "multiplicative_aggregate",
    "temporal_aggregation": "temporal_tariff",
    "rate_with_currency": "rate_composition",
    "unit_partition": "unit_partition",
    "comparative_with_unit": "compare_multiplicative",
}


@dataclass(frozen=True, slots=True)
class ExperienceRecord:
    """One compact practice-memory record (no raw traces)."""

    record_id: str
    case_id: str
    serving_status: Status
    sealed_status: Status
    gold_answer: str
    sealed_answer: str | None
    serving_refusal_family: str
    sealed_failure_family: str
    candidate_family: str | None
    first_missing_primitive: str | None
    arithmetic_chain_signature: str
    positive_evidence_refs: tuple[str, ...]
    negative_evidence_refs: tuple[str, ...]
    hazard_tags: tuple[str, ...]
    recommended_action: str
    promotion_status: PromotionStatus
    source_run_id: str
    source_report_hash: str
    schema_version: int = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "case_id": self.case_id,
            "serving_status": self.serving_status,
            "sealed_status": self.sealed_status,
            "gold_answer": self.gold_answer,
            "sealed_answer": self.sealed_answer,
            "serving_refusal_family": self.serving_refusal_family,
            "sealed_failure_family": self.sealed_failure_family,
            "candidate_family": self.candidate_family,
            "first_missing_primitive": self.first_missing_primitive,
            "arithmetic_chain_signature": self.arithmetic_chain_signature,
            "positive_evidence_refs": list(self.positive_evidence_refs),
            "negative_evidence_refs": list(self.negative_evidence_refs),
            "hazard_tags": list(self.hazard_tags),
            "recommended_action": self.recommended_action,
            "promotion_status": self.promotion_status,
            "source_run_id": self.source_run_id,
            "source_report_hash": self.source_report_hash,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ExperienceRecord:
        return cls(
            record_id=payload["record_id"],
            case_id=payload["case_id"],
            serving_status=payload["serving_status"],
            sealed_status=payload["sealed_status"],
            gold_answer=str(payload["gold_answer"]),
            sealed_answer=payload.get("sealed_answer"),
            serving_refusal_family=payload["serving_refusal_family"],
            sealed_failure_family=payload["sealed_failure_family"],
            candidate_family=payload.get("candidate_family"),
            first_missing_primitive=payload.get("first_missing_primitive"),
            arithmetic_chain_signature=payload["arithmetic_chain_signature"],
            positive_evidence_refs=tuple(payload["positive_evidence_refs"]),
            negative_evidence_refs=tuple(payload["negative_evidence_refs"]),
            hazard_tags=tuple(payload["hazard_tags"]),
            recommended_action=payload["recommended_action"],
            promotion_status=payload["promotion_status"],
            source_run_id=payload["source_run_id"],
            source_report_hash=payload["source_report_hash"],
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class CompactedExperienceRecord:
    """Case-level record collapsed across duplicate signatures / runs."""

    dedupe_key: str
    record_id: str
    case_id: str
    serving_status: Status
    sealed_status: Status
    gold_answer: str
    sealed_answer: str | None
    serving_refusal_family: str
    sealed_failure_family: str
    candidate_family: str | None
    first_missing_primitive: str | None
    arithmetic_chain_signature: str
    positive_evidence_refs: tuple[str, ...]
    negative_evidence_refs: tuple[str, ...]
    hazard_tags: tuple[str, ...]
    recommended_action: str
    promotion_status: PromotionStatus
    count: int
    first_seen_run_id: str
    last_seen_run_id: str
    status_transitions: tuple[str, ...]
    source_report_hash: str
    schema_version: int = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "dedupe_key": self.dedupe_key,
            "record_id": self.record_id,
            "case_id": self.case_id,
            "serving_status": self.serving_status,
            "sealed_status": self.sealed_status,
            "gold_answer": self.gold_answer,
            "sealed_answer": self.sealed_answer,
            "serving_refusal_family": self.serving_refusal_family,
            "sealed_failure_family": self.sealed_failure_family,
            "candidate_family": self.candidate_family,
            "first_missing_primitive": self.first_missing_primitive,
            "arithmetic_chain_signature": self.arithmetic_chain_signature,
            "positive_evidence_refs": list(self.positive_evidence_refs),
            "negative_evidence_refs": list(self.negative_evidence_refs),
            "hazard_tags": list(self.hazard_tags),
            "recommended_action": self.recommended_action,
            "promotion_status": self.promotion_status,
            "count": self.count,
            "first_seen_run_id": self.first_seen_run_id,
            "last_seen_run_id": self.last_seen_run_id,
            "status_transitions": list(self.status_transitions),
            "source_report_hash": self.source_report_hash,
            "schema_version": self.schema_version,
        }


def _record_id_payload(record: ExperienceRecord) -> dict[str, Any]:
    return {
        "case_id": record.case_id,
        "serving_status": record.serving_status,
        "sealed_status": record.sealed_status,
        "gold_answer": record.gold_answer,
        "sealed_answer": record.sealed_answer,
        "serving_refusal_family": record.serving_refusal_family,
        "sealed_failure_family": record.sealed_failure_family,
        "candidate_family": record.candidate_family,
        "first_missing_primitive": record.first_missing_primitive,
        "arithmetic_chain_signature": record.arithmetic_chain_signature,
        "hazard_tags": list(record.hazard_tags),
        "promotion_status": record.promotion_status,
        "schema_version": record.schema_version,
    }


def compute_record_id(record: ExperienceRecord) -> str:
    return sha256_of(_record_id_payload(record))


def compute_dedupe_key(record: ExperienceRecord) -> str:
    payload = {
        "case_id": record.case_id,
        "candidate_family": record.candidate_family,
        "arithmetic_chain_signature": record.arithmetic_chain_signature,
        "hazard_tags": sorted(record.hazard_tags),
    }
    return sha256_of(payload)


def _extract_category(reason: str) -> str | None:
    """Pull (category=...) from recognized-no-injection refusal reasons."""
    if _RECOGNIZED_NO_INJ not in reason:
        return None
    match = _CATEGORY_RE.search(reason)
    return match.group(1) if match else None


def _scout_row_evidence(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Compact per-case scout evidence for provenance hashing (not raw traces)."""
    evidence: list[dict[str, Any]] = []
    for row in rows or []:
        evidence.append(
            {
                "case_id": row["case_id"],
                "served_status": row["served_status"],
                "aggressive_status": row["aggressive_status"],
                "failure_family": row["failure_family"],
                "trace_key": row["trace_key"],
                "candidate_lift_family": row.get("candidate_lift_family"),
                "first_failed_step": row.get("first_failed_step"),
            }
        )
    return sorted(evidence, key=lambda item: item["case_id"])


def compute_run_id(scout_summary: dict[str, Any]) -> str:
    """Identity of one scout run — includes per-case row evidence, not aggregates alone."""
    payload = {
        "schema_version": scout_summary.get("schema_version"),
        "adr": scout_summary.get("adr"),
        "cases_source": scout_summary.get("cases_source"),
        "sample_count": scout_summary.get("sample_count"),
        "serving_counts": scout_summary.get("serving_counts"),
        "sealed_counts": scout_summary.get("sealed_counts"),
        "delta_counts": scout_summary.get("delta_counts"),
        "rows": _scout_row_evidence(scout_summary.get("rows")),
    }
    return sha256_of(payload)


def compute_report_hash(scout_summary: dict[str, Any]) -> str:
    """Hash full load-bearing scout summary evidence, including compact row payloads."""
    payload = dict(scout_summary)
    if "rows" in payload:
        payload["rows"] = _scout_row_evidence(payload["rows"])
    return sha256_of(payload)


def _resolve_operation_class(raw_case: dict[str, Any]) -> str:
    expr = raw_case.get("answer_expression", "")
    if not expr:
        return _UNKNOWN_OPERATION_CLASS
    return classify_operation(expr)


def _arithmetic_chain_signature(
    *,
    delta_kind: str,
    operation_class: str,
    first_failed_step: str | None,
    trace_key: str,
) -> str:
    return "|".join(
        [
            delta_kind,
            operation_class,
            first_failed_step or "none",
            trace_key,
        ]
    )


def _infer_missing_primitive(
    *,
    category: str | None,
    candidate_family: str | None,
    failure_family: str,
) -> str | None:
    if category:
        return _PRIMITIVE_BY_CATEGORY.get(category, "diagnostic_hold")
    if candidate_family and ":" in candidate_family:
        return candidate_family.split(":", 1)[0]
    if failure_family.startswith("lift_skill_gap_recognized_no_injection_"):
        parts = failure_family.split("_")
        if parts and parts[-1] in _PRIMITIVE_BY_CATEGORY:
            return _PRIMITIVE_BY_CATEGORY[parts[-1]]
    return None


def _canonical_candidate_family(
    *,
    row_family: str | None,
    category: str | None,
    first_missing_primitive: str | None,
) -> str | None:
    """Return the shared recognizer-surface family key for lift and wrong-risk rows.

    Sealed-wrong rows often lack ``candidate_lift_family`` because they are not
    lift rows, but recognized no-injection failures still expose the same
    category/primitive surface as refused→correct lift rows.  Canonicalizing the
    surface here lets family summaries block a candidate when matching negative
    evidence exists.
    """
    if row_family:
        return row_family
    if category and first_missing_primitive:
        return f"{first_missing_primitive}:{category}"
    return None


def _hazard_tags(
    *,
    delta_kind: str,
    served_status: Status,
    sealed_status: Status,
    refusal_reason: str | None,
    failure_family: str,
) -> tuple[str, ...]:
    tags: list[str] = list(_HAZARD_BY_DELTA.get(delta_kind, ()))
    reason = (refusal_reason or "").lower()
    if "fraction" in reason or "half" in reason or "quarter" in reason:
        tags.append("fraction_surface")
    if "more than" in reason or "less than" in reason:
        tags.append("comparative_surface")
    if sealed_status == "wrong":
        tags.append("sealed_wrong")
    if served_status == "wrong":
        tags.append("serving_wrong")
    if failure_family == "joint_sealed_no_resolution":
        tags.append("joint_no_resolution")
    if "no admissible candidate for question" in reason:
        tags.append("unbound_target")
    if delta_kind == "joint_refusal" and not tags:
        tags.append("low_signal_joint")
    return tuple(sorted(set(tags)))


def _recommended_action(
    *,
    delta_kind: str,
    promotion_status: PromotionStatus,
    candidate_family: str | None,
    first_missing_primitive: str | None,
) -> str:
    if promotion_status == "blocked_by_wrong_risk":
        return (
            "blocked: sealed wrong shares recognizer surface; build confusers "
            "before any serving promotion"
        )
    if promotion_status == "promoted_in_pr":
        return "preserved: serving correct; monitor for regression"
    if delta_kind == "lift_refused_to_correct" and first_missing_primitive:
        return (
            f"pursue narrow serving organ for primitive={first_missing_primitive} "
            f"family={candidate_family or 'unclassified'} with confuser matrix"
        )
    if delta_kind == "elimination_refused_to_wrong":
        return "negative evidence: sealed attempt wrong; do not promote surface"
    if delta_kind == "joint_refusal":
        return "diagnostic hold: joint refusal; await family cluster or new signal"
    if delta_kind == "serving_conservative_win":
        return "conservative boundary: serving correct where sealed did not commit"
    return "not_promotable: insufficient lift signal"


def _classify_promotion_status(
    *,
    delta_kind: str,
    served_status: Status,
    sealed_status: Status,
    candidate_family: str | None,
    first_missing_primitive: str | None,
    hazard_tags: tuple[str, ...],
    category: str | None,
) -> PromotionStatus:
    if delta_kind == "already_served" and served_status == "correct":
        return "promoted_in_pr"
    if delta_kind in ("elimination_refused_to_wrong", "serving_wrong_other"):
        return "blocked_by_wrong_risk"
    if delta_kind == "serving_wrong_sealed_correct":
        return "blocked_by_wrong_risk"
    if sealed_status == "wrong":
        return "blocked_by_wrong_risk"
    if any(tag in _BLOCKED_HAZARDS for tag in hazard_tags):
        if delta_kind == "lift_refused_to_correct":
            return "blocked_by_wrong_risk"
    if delta_kind == "lift_refused_to_correct":
        if not candidate_family or not first_missing_primitive:
            return "not_promotable"
        if category is None and "unbound_target" in hazard_tags:
            return "blocked_by_wrong_risk"
        return "candidate"
    return "not_promotable"


def _positive_evidence_refs(
    *,
    case_id: str,
    trace_key: str,
    candidate_family: str | None,
    delta_kind: str,
) -> tuple[str, ...]:
    refs = [f"scout:case_id={case_id}", f"scout:trace_key={trace_key}"]
    if candidate_family:
        refs.append(f"scout:candidate_family={candidate_family}")
    if delta_kind == "lift_refused_to_correct":
        refs.append("scout:delta=lift_refused_to_correct")
    return tuple(refs)


def _negative_evidence_refs(
    *,
    case_id: str,
    delta_kind: str,
    sealed_status: Status,
    sealed_answer: str | None,
    gold_answer: str,
) -> tuple[str, ...]:
    refs: list[str] = []
    if delta_kind == "elimination_refused_to_wrong" or sealed_status == "wrong":
        refs.append(f"scout:sealed_wrong:case_id={case_id}")
        if sealed_answer is not None:
            refs.append(f"scout:sealed_answer={sealed_answer}:gold={gold_answer}")
    return tuple(refs)


def _high_frequency_joint_families(rows: tuple[SealedAttemptScoutRow, ...]) -> set[str]:
    counts: dict[str, int] = {}
    for row in rows:
        delta = classify_delta_kind(row.served_status, row.aggressive_status)
        if delta == "joint_refusal":
            counts[row.failure_family] = counts.get(row.failure_family, 0) + 1
    return {fam for fam, n in counts.items() if n >= _HIGH_FREQ_JOINT_THRESHOLD}


def should_retain_row(
    row: SealedAttemptScoutRow,
    *,
    delta_kind: str,
    high_freq_joint_families: set[str],
) -> bool:
    if delta_kind in (
        "lift_refused_to_correct",
        "elimination_refused_to_wrong",
        "serving_wrong_sealed_correct",
        "serving_wrong_other",
    ):
        return True
    if delta_kind == "already_served" and row.served_status == "correct":
        return True
    if delta_kind == "serving_conservative_win":
        return True
    if delta_kind == "joint_refusal":
        return row.failure_family in high_freq_joint_families
    return False


def scout_row_to_experience_record(
    row: SealedAttemptScoutRow,
    *,
    source_run_id: str,
    source_report_hash: str,
    operation_class: str,
    category: str | None,
    high_freq_joint_families: set[str],
) -> ExperienceRecord | None:
    delta_kind = classify_delta_kind(row.served_status, row.aggressive_status)
    if not should_retain_row(
        row, delta_kind=delta_kind, high_freq_joint_families=high_freq_joint_families
    ):
        return None

    chain_sig = _arithmetic_chain_signature(
        delta_kind=delta_kind,
        operation_class=operation_class,
        first_failed_step=row.first_failed_step,
        trace_key=row.trace_key,
    )
    hazards = _hazard_tags(
        delta_kind=delta_kind,
        served_status=row.served_status,
        sealed_status=row.aggressive_status,
        refusal_reason=row.refusal_reason,
        failure_family=row.failure_family,
    )
    missing = _infer_missing_primitive(
        category=category,
        candidate_family=row.candidate_lift_family,
        failure_family=row.failure_family,
    )
    candidate_family = _canonical_candidate_family(
        row_family=row.candidate_lift_family,
        category=category,
        first_missing_primitive=missing,
    )
    promotion = _classify_promotion_status(
        delta_kind=delta_kind,
        served_status=row.served_status,
        sealed_status=row.aggressive_status,
        candidate_family=candidate_family,
        first_missing_primitive=missing,
        hazard_tags=hazards,
        category=category,
    )
    serving_family = row.failure_family if row.served_status == "refused" else "n/a"
    record = ExperienceRecord(
        record_id="",
        case_id=row.case_id,
        serving_status=row.served_status,
        sealed_status=row.aggressive_status,
        gold_answer=row.gold_answer,
        sealed_answer=row.aggressive_answer,
        serving_refusal_family=serving_family,
        sealed_failure_family=row.failure_family,
        candidate_family=candidate_family,
        first_missing_primitive=missing,
        arithmetic_chain_signature=chain_sig,
        positive_evidence_refs=_positive_evidence_refs(
            case_id=row.case_id,
            trace_key=row.trace_key,
            candidate_family=candidate_family,
            delta_kind=delta_kind,
        ),
        negative_evidence_refs=_negative_evidence_refs(
            case_id=row.case_id,
            delta_kind=delta_kind,
            sealed_status=row.aggressive_status,
            sealed_answer=row.aggressive_answer,
            gold_answer=row.gold_answer,
        ),
        hazard_tags=hazards,
        recommended_action=_recommended_action(
            delta_kind=delta_kind,
            promotion_status=promotion,
            candidate_family=candidate_family,
            first_missing_primitive=missing,
        ),
        promotion_status=promotion,
        source_run_id=source_run_id,
        source_report_hash=source_report_hash,
    )
    rid = compute_record_id(record)
    return ExperienceRecord(
        record_id=rid,
        case_id=record.case_id,
        serving_status=record.serving_status,
        sealed_status=record.sealed_status,
        gold_answer=record.gold_answer,
        sealed_answer=record.sealed_answer,
        serving_refusal_family=record.serving_refusal_family,
        sealed_failure_family=record.sealed_failure_family,
        candidate_family=record.candidate_family,
        first_missing_primitive=record.first_missing_primitive,
        arithmetic_chain_signature=record.arithmetic_chain_signature,
        positive_evidence_refs=record.positive_evidence_refs,
        negative_evidence_refs=record.negative_evidence_refs,
        hazard_tags=record.hazard_tags,
        recommended_action=record.recommended_action,
        promotion_status=record.promotion_status,
        source_run_id=record.source_run_id,
        source_report_hash=record.source_report_hash,
    )


def records_from_scout_summary(
    scout_summary: dict[str, Any],
    cases_by_id: dict[str, dict[str, Any]] | None = None,
) -> tuple[ExperienceRecord, ...]:
    rows_data = scout_summary.get("rows")
    if rows_data is None:
        raise ValueError("scout_summary must include rows for experience extraction")
    rows = tuple(
        SealedAttemptScoutRow(
            case_id=r["case_id"],
            served_status=r["served_status"],
            aggressive_status=r["aggressive_status"],
            aggressive_answer=r.get("aggressive_answer"),
            gold_answer=str(r["gold_answer"]),
            refusal_reason=r.get("refusal_reason"),
            failure_family=r["failure_family"],
            candidate_lift_family=r.get("candidate_lift_family"),
            first_failed_step=r.get("first_failed_step"),
            trace_key=r["trace_key"],
        )
        for r in rows_data
    )
    return records_from_scout_rows(
        rows,
        scout_summary=scout_summary,
        cases_by_id=cases_by_id,
    )


def records_from_scout_rows(
    rows: tuple[SealedAttemptScoutRow, ...],
    *,
    scout_summary: dict[str, Any],
    cases_by_id: dict[str, dict[str, Any]] | None = None,
) -> tuple[ExperienceRecord, ...]:
    run_id = compute_run_id(scout_summary)
    report_hash = compute_report_hash(scout_summary)
    high_freq = _high_frequency_joint_families(rows)
    out: list[ExperienceRecord] = []
    for row in rows:
        raw_case = (cases_by_id or {}).get(row.case_id, {})
        op_class = _resolve_operation_class(raw_case)
        category = (
            _extract_category(row.refusal_reason or "")
            if row.refusal_reason
            else None
        )
        rec = scout_row_to_experience_record(
            row,
            source_run_id=run_id,
            source_report_hash=report_hash,
            operation_class=op_class,
            category=category,
            high_freq_joint_families=high_freq,
        )
        if rec is not None:
            out.append(rec)
    return tuple(sorted(out, key=lambda r: (r.case_id, r.record_id)))


def _merge_record_refs(records: list[ExperienceRecord], attr: str) -> tuple[str, ...]:
    values: set[str] = set()
    for rec in records:
        values.update(getattr(rec, attr))
    return tuple(sorted(values))


def compact_records(
    records: tuple[ExperienceRecord, ...],
) -> tuple[CompactedExperienceRecord, ...]:
    """Compact duplicate records while preserving caller-provided run order.

    ``source_run_id`` is a content hash, not chronology.  For records that share
    a dedupe key, first/last status and transition order follow the order passed
    by the caller.  Use ``merge_compacted_runs`` for explicit cross-run merges.
    """
    groups: dict[str, list[ExperienceRecord]] = {}
    for rec in records:
        key = compute_dedupe_key(rec)
        groups.setdefault(key, []).append(rec)

    compacted: list[CompactedExperienceRecord] = []
    for dedupe_key, group in sorted(groups.items()):
        first = group[0]
        last = group[-1]
        transitions: list[str] = []
        for rec in group:
            transition = f"{rec.serving_status}/{rec.sealed_status}:{rec.promotion_status}"
            if not transitions or transitions[-1] != transition:
                transitions.append(transition)
        compacted.append(
            CompactedExperienceRecord(
                dedupe_key=dedupe_key,
                record_id=first.record_id,
                case_id=first.case_id,
                serving_status=last.serving_status,
                sealed_status=last.sealed_status,
                gold_answer=last.gold_answer,
                sealed_answer=last.sealed_answer,
                serving_refusal_family=last.serving_refusal_family,
                sealed_failure_family=last.sealed_failure_family,
                candidate_family=last.candidate_family,
                first_missing_primitive=last.first_missing_primitive,
                arithmetic_chain_signature=last.arithmetic_chain_signature,
                positive_evidence_refs=_merge_record_refs(group, "positive_evidence_refs"),
                negative_evidence_refs=_merge_record_refs(group, "negative_evidence_refs"),
                hazard_tags=tuple(sorted(set().union(*(r.hazard_tags for r in group)))),
                recommended_action=last.recommended_action,
                promotion_status=last.promotion_status,
                count=len(group),
                first_seen_run_id=first.source_run_id,
                last_seen_run_id=last.source_run_id,
                status_transitions=tuple(transitions),
                source_report_hash=last.source_report_hash,
            )
        )
    return tuple(sorted(compacted, key=lambda c: (c.case_id, c.dedupe_key)))


def _merge_evidence_refs(
    prior: tuple[str, ...],
    new: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(sorted(set(prior) | set(new)))


def _append_status_transitions(
    prior: tuple[str, ...],
    new: tuple[str, ...],
) -> tuple[str, ...]:
    merged = list(prior)
    for transition in new:
        if not merged or merged[-1] != transition:
            merged.append(transition)
    return tuple(merged)


def _merge_compacted_pair(
    prior: CompactedExperienceRecord,
    new: CompactedExperienceRecord,
) -> CompactedExperienceRecord:
    return CompactedExperienceRecord(
        dedupe_key=prior.dedupe_key,
        record_id=new.record_id,
        case_id=new.case_id,
        serving_status=new.serving_status,
        sealed_status=new.sealed_status,
        gold_answer=new.gold_answer,
        sealed_answer=new.sealed_answer,
        serving_refusal_family=new.serving_refusal_family,
        sealed_failure_family=new.sealed_failure_family,
        candidate_family=new.candidate_family,
        first_missing_primitive=new.first_missing_primitive,
        arithmetic_chain_signature=new.arithmetic_chain_signature,
        positive_evidence_refs=_merge_evidence_refs(
            prior.positive_evidence_refs, new.positive_evidence_refs
        ),
        negative_evidence_refs=_merge_evidence_refs(
            prior.negative_evidence_refs, new.negative_evidence_refs
        ),
        hazard_tags=new.hazard_tags,
        recommended_action=new.recommended_action,
        promotion_status=new.promotion_status,
        count=prior.count + new.count,
        first_seen_run_id=prior.first_seen_run_id,
        last_seen_run_id=new.last_seen_run_id,
        status_transitions=_append_status_transitions(
            prior.status_transitions, new.status_transitions
        ),
        source_report_hash=new.source_report_hash,
    )


def merge_compacted_runs(
    prior: tuple[CompactedExperienceRecord, ...],
    new_records: tuple[ExperienceRecord, ...],
) -> tuple[CompactedExperienceRecord, ...]:
    """Merge prior compacted state with records from a new scout run.

    O(number of compacted records) — never re-expands prior counts.
    """
    new_compacted = compact_records(new_records)
    merged: dict[str, CompactedExperienceRecord] = {
        record.dedupe_key: record for record in prior
    }
    for new_record in new_compacted:
        existing = merged.get(new_record.dedupe_key)
        if existing is None:
            merged[new_record.dedupe_key] = new_record
        else:
            merged[new_record.dedupe_key] = _merge_compacted_pair(existing, new_record)
    return tuple(sorted(merged.values(), key=lambda c: (c.case_id, c.dedupe_key)))


def build_family_summaries(
    compacted: tuple[CompactedExperienceRecord, ...],
) -> tuple[dict[str, Any], ...]:
    families: dict[str, list[CompactedExperienceRecord]] = {}
    for rec in compacted:
        fam = rec.candidate_family or rec.sealed_failure_family
        families.setdefault(fam, []).append(rec)

    summaries: list[dict[str, Any]] = []
    for family, group in sorted(families.items()):
        refused_to_correct = sum(
            1
            for r in group
            if r.promotion_status == "candidate"
            and r.serving_status == "refused"
            and r.sealed_status == "correct"
        )
        sealed_wrong = sum(
            1 for r in group if "sealed_wrong" in r.hazard_tags
        )
        joint_refusal = sum(
            1 for r in group if "low_signal_joint" in r.hazard_tags or "joint_no_resolution" in r.hazard_tags
        )
        promoted = sum(1 for r in group if r.promotion_status == "promoted_in_pr")
        blocked = sum(1 for r in group if r.promotion_status == "blocked_by_wrong_risk")
        primitives: dict[str, int] = {}
        for r in group:
            if r.first_missing_primitive:
                primitives[r.first_missing_primitive] = (
                    primitives.get(r.first_missing_primitive, 0) + r.count
                )
        top_primitives = [
            p for p, _ in sorted(primitives.items(), key=lambda x: (-x[1], x[0]))
        ][:3]
        promotion_status = "not_promotable"
        if blocked and refused_to_correct:
            promotion_status = "blocked_by_wrong_risk"
        elif refused_to_correct and not blocked:
            promotion_status = "candidate"
        elif blocked:
            promotion_status = "blocked_by_wrong_risk"
        summaries.append(
            {
                "family": family,
                "case_ids": sorted({r.case_id for r in group}),
                "refused_to_correct_count": refused_to_correct,
                "sealed_wrong_count": sealed_wrong,
                "joint_refusal_count": joint_refusal,
                "promoted_count": promoted,
                "blocked_count": blocked,
                "top_missing_primitives": top_primitives,
                "promotion_status": promotion_status,
                "recommended_next_action": _family_next_action(
                    family=family,
                    promotion_status=promotion_status,
                    refused_to_correct=refused_to_correct,
                    blocked=blocked,
                ),
            }
        )
    return tuple(summaries)


def _family_next_action(
    *,
    family: str,
    promotion_status: str,
    refused_to_correct: int,
    blocked: int,
) -> str:
    if promotion_status == "candidate":
        return (
            f"design narrow serving organ for family={family} "
            f"({refused_to_correct} refused_to_correct) with confuser matrix"
        )
    if promotion_status == "blocked_by_wrong_risk":
        return (
            f"blocked: family={family} has {blocked} wrong-risk records; "
            "strengthen confusers before promotion"
        )
    return f"diagnostic hold: family={family} lacks promotable lift signal"


def build_hazard_summaries(
    compacted: tuple[CompactedExperienceRecord, ...],
) -> tuple[dict[str, Any], ...]:
    hazards: dict[str, list[str]] = {}
    for rec in compacted:
        for tag in rec.hazard_tags:
            hazards.setdefault(tag, []).append(rec.case_id)
    return tuple(
        {
            "hazard": tag,
            "case_ids": sorted(set(case_ids)),
            "count": len(set(case_ids)),
        }
        for tag, case_ids in sorted(hazards.items())
    )


def build_promotion_candidate_summary(
    family_summaries: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        s
        for s in family_summaries
        if s["promotion_status"] in ("candidate", "blocked_by_wrong_risk")
    )


def build_experience_report(
    scout_summary: dict[str, Any] | None = None,
    *,
    cases: list[dict[str, Any]] | None = None,
    prior_compacted: tuple[CompactedExperienceRecord, ...] | None = None,
    include_raw_records: bool = False,
) -> dict[str, Any]:
    loaded_cases = cases
    if scout_summary is None:
        if loaded_cases is None:
            loaded_cases = _load_cases(_CASES_PATH)
        scout_summary = build_scout_summary(loaded_cases, include_rows=True)
    elif "rows" not in scout_summary:
        raise ValueError("scout_summary must include rows")

    cases_by_id = {c["case_id"]: c for c in (loaded_cases or [])}

    records = records_from_scout_summary(scout_summary, cases_by_id)
    if prior_compacted:
        compacted = merge_compacted_runs(prior_compacted, records)
    else:
        compacted = compact_records(records)

    family_summaries = build_family_summaries(compacted)
    hazard_summaries = build_hazard_summaries(compacted)
    promotion_summary = build_promotion_candidate_summary(family_summaries)
    run_id = compute_run_id(scout_summary)
    report_hash = compute_report_hash(scout_summary)

    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "adr": ADR,
        "regime": "gsm8k_experience_flywheel",
        "source_run_id": run_id,
        "source_report_hash": report_hash,
        "scout_serving_counts": scout_summary.get("serving_counts"),
        "scout_sealed_counts": scout_summary.get("sealed_counts"),
        "retained_record_count": len(records),
        "compacted_record_count": len(compacted),
        "case_records": [c.as_dict() for c in compacted],
        "family_summaries": list(family_summaries),
        "hazard_summaries": list(hazard_summaries),
        "promotion_candidates": list(promotion_summary),
    }
    if include_raw_records:
        body["raw_records"] = [r.as_dict() for r in records]
    body["experience_report_hash"] = sha256_of(
        {k: v for k, v in body.items() if k != "experience_report_hash"}
    )
    return body


def write_experience_jsonl(
    report: dict[str, Any],
    path: Path,
    *,
    records_key: str = "case_records",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in report.get(records_key, []):
            fh.write(canonical_json(row).decode("utf-8") + "\n")


def write_experience_json(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(report) + b"\n")


def load_compacted_from_report(payload: dict[str, Any]) -> tuple[CompactedExperienceRecord, ...]:
    return tuple(
        CompactedExperienceRecord(
            dedupe_key=c["dedupe_key"],
            record_id=c["record_id"],
            case_id=c["case_id"],
            serving_status=c["serving_status"],
            sealed_status=c["sealed_status"],
            gold_answer=str(c["gold_answer"]),
            sealed_answer=c.get("sealed_answer"),
            serving_refusal_family=c["serving_refusal_family"],
            sealed_failure_family=c["sealed_failure_family"],
            candidate_family=c.get("candidate_family"),
            first_missing_primitive=c.get("first_missing_primitive"),
            arithmetic_chain_signature=c["arithmetic_chain_signature"],
            positive_evidence_refs=tuple(c["positive_evidence_refs"]),
            negative_evidence_refs=tuple(c["negative_evidence_refs"]),
            hazard_tags=tuple(c["hazard_tags"]),
            recommended_action=c["recommended_action"],
            promotion_status=c["promotion_status"],
            count=int(c["count"]),
            first_seen_run_id=c["first_seen_run_id"],
            last_seen_run_id=c["last_seen_run_id"],
            status_transitions=tuple(c["status_transitions"]),
            source_report_hash=c["source_report_hash"],
            schema_version=int(c.get("schema_version", SCHEMA_VERSION)),
        )
        for c in payload.get("case_records", [])
    )


__all__ = [
    "ADR",
    "CompactedExperienceRecord",
    "ExperienceRecord",
    "PromotionStatus",
    "SCHEMA_VERSION",
    "build_experience_report",
    "build_family_summaries",
    "build_hazard_summaries",
    "build_promotion_candidate_summary",
    "compact_records",
    "compute_dedupe_key",
    "compute_record_id",
    "compute_report_hash",
    "compute_run_id",
    "_extract_category",
    "load_compacted_from_report",
    "merge_compacted_runs",
    "records_from_scout_rows",
    "records_from_scout_summary",
    "scout_row_to_experience_record",
    "should_retain_row",
    "write_experience_json",
    "write_experience_jsonl",
]
