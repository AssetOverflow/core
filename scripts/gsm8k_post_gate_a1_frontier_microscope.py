#!/usr/bin/env python3
"""Post-Gate-A1 live frontier microscope for GSM8K train_sample.

Builds an ephemeral ``build_report(cases)`` snapshot (never writes
``report.json``) and classifies every refused case into stable buckets
and implementation-slice candidate families.

Docs/tooling only — no runtime mutation.  Rules are deterministic
string predicates; no LLM, no embeddings, no clocks.

Usage:
    uv run python scripts/gsm8k_post_gate_a1_frontier_microscope.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evals.gsm8k_math.train_sample.v1.runner import build_report
from evals.refusal_taxonomy.shape_categories import ShapeCategory, categorize
from scripts.gsm8k_frontier_report import _extract_category

_RECOGNIZED_NO_INJ = "candidate_graph: recognizer matched but produced no injection"

_MICROSCOPE_BUCKET_PATTERNS: tuple[tuple[str, str], ...] = (
    ("wrong", "wrong"),
    ("fast-path", "fast_path_correct"),
    ("no admissible candidate for question", "no_admissible_question"),
    ("no admissible candidate for statement", "no_admissible_statement"),
    ("no branch produced a solvable graph", "no_solvable_branch"),
    ("no solvable branch", "no_solvable_branch"),
    ("incomplete reading", "incomplete_reading"),
    (_RECOGNIZED_NO_INJ, "recognized_no_injection"),
)


def _classify_reason(reason: str) -> str:
    if not reason:
        return "other_refused"
    lowered = reason.lower()
    for needle, bucket in _MICROSCOPE_BUCKET_PATTERNS:
        if needle.lower() in lowered:
            return bucket
    if "refused" in lowered or not reason.strip():
        return "other_refused"
    return "other"

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES_PATH = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
_EXPECTED_COUNT = 50

# --- subfamily needles (stable, sorted for determinism) -------------------

_NO_ADM_STMT_SUBFAMILIES: tuple[tuple[str, str], ...] = (
    ("nested_fraction_partition", r"half of .+ (?:going|are)"),
    ("affine_equation_fraction_delta", r"1/\d+ more than|more than what .+ has"),
    ("affine_equation_fraction_target", r"decrease to \d+/\d+\s+of"),
    ("each_binding_currency", r"each saved up \$"),
    ("numeric_expression_duration", r"\d+-hour (?:drive|trip|walk)"),
    ("numeric_expression_recurrence", r"every (?:other )?(?:day|week)"),
    ("partition_statement_parser_gap", r"split|splits|sections|pieces"),
)

_NO_ADM_QUEST_SUBFAMILIES: tuple[tuple[str, str], ...] = (
    ("inverse_residual_more", r"how many more"),
    ("multiplicative_peer_pick", r"friends? pick"),
    ("ratio_times_entity", r"times (?:the )?number of"),
    ("production_yield_question", r"how many \w+ (?:will|be able to)"),
    ("conditional_aggregate_total", r" if .+, how many"),
)

_NO_SOLVABLE_SUBFAMILIES: tuple[tuple[str, str], ...] = (
    ("rate_graph_unsolvable", r"\$|per (?:day|hour|kg|cup)"),
    ("composition_branch_exhausted", r".*"),
)

_DCS_NO_INJ_SUBFAMILIES: tuple[tuple[str, str], ...] = (
    ("dcs_misroute_unit_partition", r"\d+-(?:foot|feet|inch|yard|mile|meter)"),
    ("dcs_misroute_comparative_multiplicative", r"times (?:her|his|their|as many|as much)"),
    ("dcs_misroute_comparative_additive", r" more than | less than "),
    ("dcs_misroute_rate_surface", r"\$| per | an hour|/hour|/day|/kg"),
    ("dcs_misroute_temporal", r"each day|every day|per day|one-hour|in \d+ (?:minute|hour)"),
    ("dcs_misroute_fraction_change", r"half of|75%|10%|ate half"),
    ("dcs_composition_wall", r".*"),
)

_SLICE_CANDIDATE_RULES: tuple[tuple[str, str], ...] = (
    ("partition_chunking", r"split|sections|\d+-(?:foot|feet)|partition|per box|in each"),
    ("additive_comparative", r" more than | less than |as much as|as many as"),
    ("affine_equation", r"1/\d+ more than|decrease to \d+/\d+ of|half of .+ (?:going|are)"),
    ("numeric_expression", r"\d+-hour|every (?:other )?(?:day|week)|each way"),
    ("rate_follow_up", r"\$| per |overtime|an hour|/day|/kg|for one cup"),
    ("multiplicative_comparative_follow_up", r"twice|thrice|\d+ times (?:her|his|their)"),
)

_BLOCKING_LAYER_BY_BUCKET: dict[str, str] = {
    "recognized_no_injection": "recognizer_injector",
    "no_admissible_statement": "statement_parser",
    "no_admissible_question": "question_parser",
    "no_solvable_branch": "graph_composition",
    "incomplete_reading": "reading_completeness",
    "other_refused": "unknown",
    "other": "unknown",
}

_PRIMITIVE_BY_SUBFAMILY: dict[str, str] = {
    "dcs_misroute_unit_partition": "unit_partition",
    "dcs_misroute_comparative_additive": "compare_additive",
    "dcs_misroute_comparative_multiplicative": "compare_multiplicative",
    "dcs_misroute_rate_surface": "rate_composition",
    "dcs_misroute_temporal": "temporal_aggregation",
    "dcs_misroute_fraction_change": "fraction_of_prior",
    "dcs_composition_wall": "derivation_composer",
    "no_injection_currency_amount": "currency_mutation",
    "no_injection_descriptive_setup_no_quantity": "relation_hypothesis",
    "no_injection_multiplicative_aggregation": "multiplicative_aggregate",
    "no_injection_temporal_aggregation": "temporal_tariff",
    "nested_fraction_partition": "fraction_partition",
    "affine_equation_fraction_delta": "affine_equation",
    "affine_equation_fraction_target": "fractional_delta",
    "each_binding_currency": "each_entity_binding",
    "numeric_expression_duration": "duration_multiplier",
    "numeric_expression_recurrence": "recurrence_frame",
    "partition_statement_parser_gap": "unit_partition",
    "unclassified": "diagnostic_hold",
    "inverse_residual_more": "inverse_residual_question",
    "ratio_times_entity": "ratio_question_frame",
    "production_yield_question": "yield_question_frame",
    "conditional_aggregate_total": "conditional_aggregate_question",
    "multiplicative_peer_pick": "peer_partition_question",
    "rate_graph_unsolvable": "rate_composition",
}

_EVIDENCE_SNIPPET_MAX = 96


def _padded_lower(text: str) -> str:
    return " " + text.lower().replace("\n", " ") + " "


def _first_subfamily(
    text: str,
    rules: tuple[tuple[str, str], ...],
) -> str:
    hay = _padded_lower(text)
    for name, pattern in rules:
        if re.search(pattern, hay, flags=re.IGNORECASE):
            return name
    if rules and rules[-1][1] == r".*":
        return rules[-1][0]
    return "unclassified"


def _extract_quoted_clause(reason: str, label: str) -> str:
    """Extract ``for <label>: '...'`` / ``"..."`` including embedded apostrophes."""
    patterns = (
        rf"for {label}: '(.+?)'(?: \(category=|\s*$)",
        rf'for {label}: "(.+?)"(?: \(category=|\s*$)',
    )
    for pattern in patterns:
        m = re.search(pattern, reason, flags=re.DOTALL)
        if m:
            return m.group(1).replace("\\'", "'").replace('\\"', '"')
    return ""


def _extract_statement(reason: str) -> str:
    return _extract_quoted_clause(reason, "statement")


def _extract_question(reason: str) -> str:
    return _extract_quoted_clause(reason, "question")


def _load_cases(path: Path = _CASES_PATH) -> list[dict[str, Any]]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != _EXPECTED_COUNT:
        raise ValueError(
            f"train sample must contain exactly {_EXPECTED_COUNT} cases; "
            f"found {len(records)} at {path}"
        )
    return records


@dataclass(frozen=True, slots=True)
class RefusalRecord:
    case_id: str
    verdict: str
    reason: str
    question: str
    top_bucket: str
    no_injection_category: str | None
    failing_text: str
    statement_shape: str
    question_shape: str
    subfamily: str
    slice_candidates: tuple[str, ...]
    first_blocking_layer: str
    candidate_next_primitive: str
    expected_movement: str
    evidence_snippet: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "verdict": self.verdict,
            "reason": self.reason,
            "top_refusal_bucket": self.top_bucket,
            "subfamily": self.subfamily,
            "matched_recognizer_category": self.no_injection_category,
            "first_blocking_layer": self.first_blocking_layer,
            "candidate_next_primitive": self.candidate_next_primitive,
            "expected_movement": self.expected_movement,
            "evidence_snippet": self.evidence_snippet,
            "failing_text": self.failing_text,
            "statement_shape": self.statement_shape,
            "question_shape": self.question_shape,
            "slice_candidates": list(self.slice_candidates),
        }


def _evidence_snippet(question: str, failing_text: str) -> str:
    source = (failing_text or question).strip()
    if not source:
        return ""
    # Prefer the sentence containing the load-bearing surface.
    for part in re.split(r"(?<=[.!?])\s+", source):
        part = part.strip()
        if part:
            source = part
            break
    source = re.sub(r"\s+", " ", source)
    if len(source) <= _EVIDENCE_SNIPPET_MAX:
        return source
    return source[: _EVIDENCE_SNIPPET_MAX - 3].rstrip() + "..."


def _candidate_next_primitive(subfamily: str, slice_candidates: tuple[str, ...]) -> str:
    if subfamily in _PRIMITIVE_BY_SUBFAMILY:
        return _PRIMITIVE_BY_SUBFAMILY[subfamily]
    if "partition_chunking" in slice_candidates:
        return "unit_partition"
    if "additive_comparative" in slice_candidates:
        return "compare_additive"
    if "affine_equation" in slice_candidates:
        return "affine_equation"
    if "numeric_expression" in slice_candidates:
        return "numeric_expression_frame"
    if "rate_follow_up" in slice_candidates:
        return "rate_composition"
    if "multiplicative_comparative_follow_up" in slice_candidates:
        return "compare_multiplicative"
    return "diagnostic_hold"


def _expected_movement(
    *,
    subfamily: str,
    top_bucket: str,
    candidate_primitive: str,
) -> str:
    if subfamily == "dcs_misroute_unit_partition":
        return "downstream_reclassification"
    if subfamily == "dcs_composition_wall":
        return "diagnostic_only"
    if top_bucket == "no_solvable_branch":
        return "downstream_reclassification"
    if top_bucket == "no_admissible_question" and subfamily in {
        "inverse_residual_more",
        "ratio_times_entity",
        "multiplicative_peer_pick",
        "production_yield_question",
        "conditional_aggregate_total",
    }:
        return "downstream_reclassification"
    if top_bucket == "no_admissible_statement" and candidate_primitive in {
        "unit_partition",
        "duration_multiplier",
        "recurrence_frame",
        "each_entity_binding",
    }:
        return "downstream_reclassification"
    if subfamily in {
        "dcs_misroute_comparative_additive",
        "dcs_misroute_comparative_multiplicative",
    }:
        return "downstream_reclassification"
    if candidate_primitive == "derivation_composer":
        return "diagnostic_only"
    return "diagnostic_only"


def _slice_candidates(question: str, failing_text: str) -> tuple[str, ...]:
    hay = _padded_lower(f"{question} {failing_text}")
    hits: list[str] = []
    for name, pattern in _SLICE_CANDIDATE_RULES:
        if re.search(pattern, hay, flags=re.IGNORECASE):
            hits.append(name)
    return tuple(hits)


def _assign_subfamily(
    *,
    top_bucket: str,
    no_inj_cat: str | None,
    failing_text: str,
    question: str,
) -> str:
    text = failing_text or question
    if top_bucket == "recognized_no_injection" and no_inj_cat == "discrete_count_statement":
        return _first_subfamily(text, _DCS_NO_INJ_SUBFAMILIES)
    if top_bucket == "no_admissible_statement":
        return _first_subfamily(text, _NO_ADM_STMT_SUBFAMILIES)
    if top_bucket == "no_admissible_question":
        q = failing_text or question
        return _first_subfamily(q, _NO_ADM_QUEST_SUBFAMILIES)
    if top_bucket == "no_solvable_branch":
        return _first_subfamily(question, _NO_SOLVABLE_SUBFAMILIES)
    if top_bucket == "recognized_no_injection" and no_inj_cat:
        return f"no_injection_{no_inj_cat}"
    return top_bucket


def classify_refusal(
    *,
    case_id: str,
    reason: str,
    question: str,
    verdict: str = "refused",
) -> RefusalRecord:
    top_bucket = _classify_reason(reason)
    no_inj_cat = _extract_category(reason) if top_bucket == "recognized_no_injection" else None
    failing_stmt = _extract_statement(reason)
    failing_q = _extract_question(reason)
    failing_text = failing_stmt or failing_q or question
    subfamily = _assign_subfamily(
        top_bucket=top_bucket,
        no_inj_cat=no_inj_cat,
        failing_text=failing_text,
        question=question,
    )
    slices = _slice_candidates(question, failing_text)
    primitive = _candidate_next_primitive(subfamily, slices)
    return RefusalRecord(
        case_id=case_id,
        verdict=verdict,
        reason=reason,
        question=question,
        top_bucket=top_bucket,
        no_injection_category=no_inj_cat,
        failing_text=failing_text,
        statement_shape=categorize(failing_stmt).value if failing_stmt else "",
        question_shape=categorize(question).value,
        subfamily=subfamily,
        slice_candidates=slices,
        first_blocking_layer=_BLOCKING_LAYER_BY_BUCKET.get(top_bucket, "unknown"),
        candidate_next_primitive=primitive,
        expected_movement=_expected_movement(
            subfamily=subfamily,
            top_bucket=top_bucket,
            candidate_primitive=primitive,
        ),
        evidence_snippet=_evidence_snippet(question, failing_text),
    )


def build_microscope_report(
    cases: list[dict[str, Any]] | None = None,
    *,
    cases_path: Path = _CASES_PATH,
) -> dict[str, Any]:
    """Ephemeral live frontier microscope — never writes report.json."""
    loaded = cases if cases is not None else _load_cases(cases_path)
    report = build_report(loaded)
    case_by_id = {c["case_id"]: c for c in loaded}

    records: list[RefusalRecord] = []
    for row in report.get("per_case", []):
        if str(row.get("verdict", "")).lower() != "refused":
            continue
        cid = str(row["case_id"])
        records.append(
            classify_refusal(
                case_id=cid,
                reason=str(row.get("reason", "") or ""),
                question=str(case_by_id[cid]["question"]),
            )
        )
    records.sort(key=lambda r: r.case_id)

    def _count_by(getter) -> dict[str, int]:
        tallies: dict[str, int] = defaultdict(int)
        for rec in records:
            tallies[str(getter(rec))] += 1
        return dict(sorted(tallies.items()))

    def _cases_for(predicate) -> list[str]:
        return [r.case_id for r in records if predicate(r)]

    recognized_by_cat = _count_by(
        lambda r: (
            r.no_injection_category or "uncategorized"
            if r.top_bucket == "recognized_no_injection"
            else "__skip__"
        )
    )
    recognized_by_cat.pop("__skip__", None)
    downstream_rate = _cases_for(
        lambda r: (
            r.top_bucket != "recognized_no_injection"
            and (
                r.question_shape == ShapeCategory.RATE_WITH_CURRENCY.value
                or ShapeCategory.RATE_WITH_CURRENCY.value in r.slice_candidates
                or "rate_follow_up" in r.slice_candidates
            )
        )
    )
    downstream_comparative = _cases_for(
        lambda r: (
            r.top_bucket != "recognized_no_injection"
            and (
                r.statement_shape == ShapeCategory.COMPARATIVE_WITH_UNIT.value
                or r.question_shape == ShapeCategory.COMPARATIVE_WITH_UNIT.value
                or "additive_comparative" in r.slice_candidates
                or "multiplicative_comparative_follow_up" in r.slice_candidates
            )
        )
    )
    partition_cases = _cases_for(lambda r: "partition_chunking" in r.slice_candidates)
    numeric_cases = _cases_for(lambda r: "numeric_expression" in r.slice_candidates)
    affine_cases = _cases_for(lambda r: "affine_equation" in r.slice_candidates)
    additive_cases = _cases_for(lambda r: "additive_comparative" in r.slice_candidates)
    rate_follow_cases = _cases_for(lambda r: "rate_follow_up" in r.slice_candidates)

    dcs_subfamilies = _count_by(
        lambda r: r.subfamily
        if r.no_injection_category == "discrete_count_statement"
        else "__skip__"
    )
    dcs_subfamilies.pop("__skip__", None)

    no_adm_stmt = _count_by(
        lambda r: r.subfamily if r.top_bucket == "no_admissible_statement" else "__skip__"
    )
    no_adm_stmt.pop("__skip__", None)

    no_adm_q = _count_by(
        lambda r: r.subfamily if r.top_bucket == "no_admissible_question" else "__skip__"
    )
    no_adm_q.pop("__skip__", None)

    no_solvable = _count_by(
        lambda r: r.subfamily if r.top_bucket == "no_solvable_branch" else "__skip__"
    )
    no_solvable.pop("__skip__", None)

    slice_histogram = _count_by(
        lambda r: "|".join(r.slice_candidates) if r.slice_candidates else "none"
    )

    refusal_table = [r.as_dict() for r in records]

    return {
        "schema_version": "gsm8k_post_gate_a1_frontier_microscope_v2",
        "recommended_next_ratification_candidate": "Gate A2a unit_partition / chunking primitive",
        "source": "ephemeral_build_report",
        "cases_path": str(cases_path),
        "counts": report["counts"],
        "top_buckets": _count_by(lambda r: r.top_bucket),
        "recognized_no_injection_by_category": recognized_by_cat,
        "no_admissible_statement_subfamilies": no_adm_stmt,
        "no_admissible_question_subfamilies": no_adm_q,
        "no_solvable_branch_subfamilies": no_solvable,
        "dcs_no_injection_subfamilies": dcs_subfamilies,
        "downstream_rate_refusals": {
            "count": len(downstream_rate),
            "case_ids": downstream_rate,
        },
        "downstream_comparative_refusals": {
            "count": len(downstream_comparative),
            "case_ids": downstream_comparative,
        },
        "implementation_slice_candidates": {
            "partition_chunking": {
                "count": len(partition_cases),
                "case_ids": partition_cases,
            },
            "numeric_expression": {
                "count": len(numeric_cases),
                "case_ids": numeric_cases,
            },
            "affine_equation": {"count": len(affine_cases), "case_ids": affine_cases},
            "additive_comparative_gate_a1b": {
                "count": len(additive_cases),
                "case_ids": additive_cases,
            },
            "rate_follow_up": {
                "count": len(rate_follow_cases),
                "case_ids": rate_follow_cases,
            },
        },
        "slice_candidate_histogram": slice_histogram,
        "refusal_table": refusal_table,
        "per_case": refusal_table,
        "closed_injector_buckets": {
            "rate_with_currency_no_injection": recognized_by_cat.get(
                "rate_with_currency", 0
            ),
            "comparative_with_unit_no_injection": recognized_by_cat.get(
                "comparative_with_unit", 0
            ),
            "unit_partition_no_injection": recognized_by_cat.get(
                "unit_partition", 0
            ),
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# GSM8K post-Gate-A1 frontier microscope (live ephemeral)")
    lines.append("")
    c = summary["counts"]
    lines.append(f"- correct: {c.get('correct', 0)}")
    lines.append(f"- refused: {c.get('refused', 0)}")
    lines.append(f"- wrong: {c.get('wrong', 0)}")
    lines.append("")
    lines.append("## Top refusal buckets")
    for k, v in summary["top_buckets"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## recognized_no_injection by category")
    for k, v in summary["recognized_no_injection_by_category"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## DCS no-injection subfamilies")
    for k, v in summary["dcs_no_injection_subfamilies"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Implementation slice candidates (overlap allowed)")
    for name, block in summary["implementation_slice_candidates"].items():
        lines.append(f"- {name}: {block['count']} ({', '.join(block['case_ids'])})")
    lines.append("")
    lines.append(
        f"## Recommended next ratification candidate: "
        f"{summary.get('recommended_next_ratification_candidate', 'pending')}"
    )
    lines.append("")
    lines.append("## Case-level refusal table")
    lines.append("")
    lines.append(
        "| case_id | verdict | top bucket | subfamily | recognizer cat | "
        "blocking layer | next primitive | movement | evidence | reason (truncated) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for row in summary.get("refusal_table", []):
        short_id = row["case_id"].rsplit("-", 1)[-1]
        cat = row.get("matched_recognizer_category") or "—"
        reason = row.get("reason", "")
        if len(reason) > 72:
            reason = reason[:69] + "..."
        lines.append(
            f"| {short_id} | {row['verdict']} | {row['top_refusal_bucket']} | "
            f"{row['subfamily']} | {cat} | {row['first_blocking_layer']} | "
            f"{row['candidate_next_primitive']} | {row['expected_movement']} | "
            f"{row['evidence_snippet']} | {reason} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    del argv
    summary = build_microscope_report()
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("\n---\n")
    print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())