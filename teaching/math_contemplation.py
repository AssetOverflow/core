"""ADR-0167 W2-A / W2-B + ADR-0172 W2 — Audit-corpus decomposition.

ADR-0167 W2-A deliverable: :func:`audit_to_evidence` and
:func:`audit_problem_to_evidence` convert :class:`AuditRow` sequences into
typed :class:`MathReaderRefusalEvidence` teaching-corridor records.

ADR-0167 W2-B deliverable: For ``sub_type == "lexical"`` evidence,
``claim_signature`` is computed via :func:`lexical_claim_signature` and the
``evidence_hash`` is recomputed to incorporate the signature.  All other
sub_types leave ``claim_signature == ""``.

ADR-0172 W2 deliverable: :func:`decompose_audit` reads
``audit_brief_11.json``, groups refusal rows by
``(refusal_reason, missing_operator)``, and emits one
:class:`MathReaderRefusalShapeProposal` per group of ≥2 rows.  Each
proposal carries a 4-step :class:`ReasoningTrace`
(observation → grouping → hypothesis → conclusion).  Pure read-only:
the audit file is not mutated, no proposal is written to disk, and no
teaching-store hook fires.

Pure module.  No filesystem writes, no network calls, no global mutation.
Deterministic: same inputs → byte-identical output across all reruns.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension.audit import AuditRow, audit_problem
from teaching.math_claim_signature import lexical_claim_signature
from teaching.math_contemplation_proposal import (
    MathReaderRefusalShapeProposal,
    build_proposal,
)
from teaching.math_evidence import (
    MathReaderRefusalEvidence,
    SUB_TYPE_FOR_OPERATOR,
    from_audit_row,
)
from teaching.math_reasoning_trace import (
    ReasoningStep,
    ReasoningTrace,
    build_trace,
)


def audit_to_evidence(
    audit_rows: Iterable[AuditRow],
) -> tuple[MathReaderRefusalEvidence, ...]:
    """Convert audit rows into typed teaching-corridor evidence records.

    Pure function.  Deterministic.  No filesystem, no network, no mutation.
    Sub-type assignment from :data:`teaching.math_evidence.SUB_TYPE_FOR_OPERATOR`.
    Skips rows with ``missing_operator=None`` (no sub_type → no candidate).

    For ``sub_type == "lexical"``, :func:`lexical_claim_signature` fills the
    ``claim_signature`` field and the ``evidence_hash`` incorporates it.
    For all other sub_types, ``claim_signature`` remains ``""`` (deferred).

    Input order is preserved.

    Parameters
    ----------
    audit_rows:
        Iterable of :class:`AuditRow` instances (e.g. from :func:`audit_problem`).

    Returns
    -------
    tuple[MathReaderRefusalEvidence, ...]
        One record per row whose ``missing_operator`` maps to a known sub_type.
    """
    results: list[MathReaderRefusalEvidence] = []
    for row in audit_rows:
        if row.missing_operator is None:
            continue
        sub_type = SUB_TYPE_FOR_OPERATOR.get(row.missing_operator)
        if sub_type is None:
            continue
        if sub_type == "lexical":
            sig = lexical_claim_signature(
                surface=row.token_text,
                refusal_detail=row.refusal_detail,
            )
        else:
            sig = ""
        evidence = from_audit_row(row, sub_type, claim_signature=sig)
        results.append(evidence)
    return tuple(results)


def audit_problem_to_evidence(
    problem_text: str,
    *,
    case_id: str,
) -> tuple[MathReaderRefusalEvidence, ...]:
    """Run the reader over *problem_text* and return evidence records.

    Convenience wrapper that calls :func:`audit_problem` and pipes the
    resulting :class:`AuditRow` list through :func:`audit_to_evidence`.
    Useful for tests and downstream pipeline work (W3-A).

    Parameters
    ----------
    problem_text:
        Raw GSM8K-style problem string.
    case_id:
        Identifier attached to every :class:`AuditRow` (e.g. ``"probe"``).

    Returns
    -------
    tuple[MathReaderRefusalEvidence, ...]
        Evidence records for any refusals encountered.  Empty tuple on full
        admission or if the text produced no sentences.
    """
    _result, rows = audit_problem(problem_text, case_id=case_id)
    return audit_to_evidence(rows)


# ---------------------------------------------------------------------------
# ADR-0172 W2 — Audit-corpus decomposer
# ---------------------------------------------------------------------------


# Widened dispatch (ADR-0172 tightening follow-up #2): the original
# single-key heuristic (refusal_reason only) collapsed every audit_brief_11
# group to injector_sub_shape because the reader's actual refusal_reasons
# (unexpected_category, unresolved_pronoun, …) never matched the legacy
# keys.  The (refusal_reason × missing_operator) pair carries the
# information needed to route to the queued handlers from
# docs/handoff/ADR-0167-FOLLOWUPS.md §1.
_CHANGE_KIND_BY_PAIR: dict[tuple[str, str], str] = {
    ("unexpected_category", "pre_frame_filler_sentence"): "matcher_extension",
    ("unexpected_category", "fraction_percentage_literal"): "matcher_extension",
    ("unresolved_pronoun", "pronoun_resolution"): "matcher_extension",
    # ADR-0169 CC-3: route CompositionClaim audit groups (20 of 47 cases —
    # `quantity_extraction` = 12 + `multi_quantity_composition` = 8) to the
    # new CompositionClaim handler.  Previously these fell through to
    # `injector_sub_shape` because no pair entry existed.
    ("incomplete_operation", "quantity_extraction"): "composition_reclassification",
    ("incomplete_operation", "multi_quantity_composition"): "composition_reclassification",
    # ADR-0169 CC-3 demotion: the prior two `frame_reclassification` routes
    # for (unexpected_category, multi_subject_sentence) and
    # (unexpected_category, descriptive_frame_question) were proven at the
    # 2026-05-27 end-to-end demo to be handler mismatches — those refusals
    # need ReferenceClaim/CompositionClaim and SlotClaim respectively, not
    # FrameClaim (whose SAFE_FRAME_CATEGORIES allowlist is quantity/ownership
    # frames).  Until SlotClaim and ReferenceClaim handlers ship, they fall
    # through to `injector_sub_shape` (the catch-all) so the workbench stops
    # emitting handler-mismatched FrameClaim proposals.
}

# Single-key fallback retained for completeness — covers reader refusals
# that share a refusal_reason regardless of missing_operator.
_CHANGE_KIND_BY_REFUSAL_REASON: dict[str, str] = {
    "lexicon_entry": "vocabulary_addition",
    "narrowness_violation": "matcher_extension",
    "frame_unrecognized": "frame_reclassification",
}


def _audit_row_from_case(case: dict) -> AuditRow:
    """Reconstruct an :class:`AuditRow` from one ``per_case`` JSON entry.

    Defensive about missing fields: the audit JSON only carries the
    columns it had to populate.  Empty/missing fields default to the
    natural zero for their declared type.
    """

    return AuditRow(
        case_id=str(case["case_id"]),
        sentence_index=int(case.get("sentence_index", 0)),
        token_index=int(case.get("token_index", 0)),
        token_text=str(case.get("token_text", "")),
        recognized_terms=tuple(case.get("recognized_terms", ())),
        skipped_frame=case.get("skipped_frame"),
        missing_operator=case.get("missing_operator"),
        refusal_reason=str(case.get("refusal_reason", "")),
        refusal_detail=str(case.get("refusal_detail", "")),
    )


def _change_kind_for_group(refusal_reason: str, missing_operator: str) -> str:
    """Dispatch on (refusal_reason, missing_operator) pair, then refusal_reason.

    Per ADR-0172 tightening follow-up #2: the pair-based table covers the
    GSM8K train-sample audit groups that route to queued handlers
    (matcher_extension, frame_reclassification).  The single-key fallback
    preserves the original ADR-0172 §"Six open questions" #1 mapping for
    reader refusals that share a refusal_reason regardless of operator.
    """

    paired = _CHANGE_KIND_BY_PAIR.get((refusal_reason, missing_operator))
    if paired is not None:
        return paired
    return _CHANGE_KIND_BY_REFUSAL_REASON.get(
        refusal_reason, "injector_sub_shape"
    )


def _modal_anchor_payload(
    *,
    refusal_reason: str,
    missing_operator: str,
    evidence: tuple[MathReaderRefusalEvidence, ...],
) -> dict:
    """Build a deterministic, JSON-safe placeholder payload for the group."""

    return {
        "evidence_count": len(evidence),
        "group_key": {
            "missing_operator": missing_operator,
            "refusal_reason": refusal_reason,
        },
        "modal_sub_type": evidence[0].sub_type,
    }


def _build_reasoning_trace(
    *,
    refusal_reason: str,
    missing_operator: str,
    evidence: tuple[MathReaderRefusalEvidence, ...],
    change_kind: str,
) -> ReasoningTrace:
    """Construct the 4-step contemplation trace for one group."""

    case_ids = tuple(ev.case_id for ev in evidence)
    group_payload = {
        "missing_operator": missing_operator,
        "refusal_reason": refusal_reason,
    }
    observation = ReasoningStep(
        step_index=0,
        step_kind="observation",
        input_pointers=case_ids,
        claim=(
            f"{len(evidence)} refusal rows share "
            f"(refusal_reason={refusal_reason!r}, "
            f"missing_operator={missing_operator!r})"
        ),
        justification=(
            "Decomposer iterated audit_brief_11.json per_case rows and "
            "found a group whose shared key meets the ≥2-evidence floor."
        ),
        output_payload={
            "case_ids": list(case_ids),
            "evidence_count": len(evidence),
        },
    )
    grouping = ReasoningStep(
        step_index=1,
        step_kind="grouping",
        input_pointers=case_ids,
        claim=(
            "Group key encodes the shared (refusal_reason, missing_operator) "
            "tuple under which these rows refused."
        ),
        justification=(
            "Per ADR-0172 §'Six open questions' #1, the naive grouping is "
            "exact equality on the refusal_reason × missing_operator pair."
        ),
        output_payload=group_payload,
    )
    hypothesis = ReasoningStep(
        step_index=2,
        step_kind="hypothesis",
        input_pointers=case_ids,
        claim=(
            f"The structural change kind for this group is {change_kind!r}."
        ),
        justification=(
            "Dispatched via the (refusal_reason, missing_operator) pair table: "
            "(unexpected_category, pre_frame_filler_sentence|"
            "fraction_percentage_literal) → matcher_extension; "
            "(unresolved_pronoun, pronoun_resolution) → matcher_extension; "
            "(incomplete_operation, quantity_extraction|"
            "multi_quantity_composition) → composition_reclassification "
            "(ADR-0169 CC-3). "
            "(unexpected_category, multi_subject_sentence|"
            "descriptive_frame_question) demoted from frame_reclassification "
            "to injector_sub_shape (ADR-0169 CC-3): the FrameClaim "
            "SAFE_FRAME_CATEGORIES allowlist does not cover those shapes; "
            "they await ReferenceClaim/SlotClaim handlers. "
            "Refusal-reason fallback: lexicon_entry → vocabulary_addition; "
            "narrowness_violation → matcher_extension; "
            "frame_unrecognized → frame_reclassification; "
            "default → injector_sub_shape."
        ),
        output_payload={"proposed_change_kind": change_kind},
    )
    conclusion = ReasoningStep(
        step_index=3,
        step_kind="conclusion",
        input_pointers=case_ids,
        claim=(
            f"Propose a {change_kind!r} structural change covering "
            f"{len(evidence)} evidence rows."
        ),
        justification=(
            "Evidence-only proposal; the wrong=0 surface ratification "
            "handler decides whether to apply, not this decomposer."
        ),
        output_payload={
            "proposed_change_kind": change_kind,
            "evidence_count": len(evidence),
        },
    )
    return build_trace(
        (observation, grouping, hypothesis, conclusion)
    )


def _build_proposal_for_group(
    *,
    refusal_reason: str,
    missing_operator: str,
    evidence: tuple[MathReaderRefusalEvidence, ...],
) -> MathReaderRefusalShapeProposal:
    """Assemble one :class:`MathReaderRefusalShapeProposal` for a group."""

    change_kind = _change_kind_for_group(refusal_reason, missing_operator)
    payload = _modal_anchor_payload(
        refusal_reason=refusal_reason,
        missing_operator=missing_operator,
        evidence=evidence,
    )
    trace = _build_reasoning_trace(
        refusal_reason=refusal_reason,
        missing_operator=missing_operator,
        evidence=evidence,
        change_kind=change_kind,
    )
    replay_seed = json.dumps(
        {
            "evidence_hashes": sorted(ev.evidence_hash for ev in evidence),
            "missing_operator": missing_operator,
            "refusal_reason": refusal_reason,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    replay_equivalence_hash = hashlib.sha256(replay_seed).hexdigest()
    structural_commonality = (
        f"{len(evidence)} refusals share "
        f"refusal_reason={refusal_reason!r} ∧ "
        f"missing_operator={missing_operator!r}"
    )
    wrong_zero_assertion = (
        "Proposal is evidence-only; ratification handler is the wrong=0 "
        "surface, not this proposal."
    )
    # Structural gap (ADR-0172 tightening follow-up #3): the evidence record
    # carries `sub_type` but not `shape_category`, so the proposal cannot
    # derive shape_category from the evidence today.  All groups emit
    # UNCATEGORIZED until a future wave adds shape_category to
    # MathReaderRefusalEvidence (or the reader's ShapeCategory inference is
    # plumbed through the audit row).  Do NOT invent a shape_category here.
    return build_proposal(
        shape_category=ShapeCategory.UNCATEGORIZED,
        structural_commonality=structural_commonality,
        evidence_pointers=evidence,
        proposed_change_kind=change_kind,
        proposed_change_payload=payload,
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash=replay_equivalence_hash,
        reasoning_trace=trace,
    )


def decompose_audit(
    audit_path: Path,
) -> tuple[MathReaderRefusalShapeProposal, ...]:
    """Decompose an audit brief into refusal-shape proposals.

    Read ``audit_path`` (expected schema: ``audit_brief_11.json``), group
    ``per_case`` refusal rows by ``(refusal_reason, missing_operator)``,
    and emit one :class:`MathReaderRefusalShapeProposal` per group with
    ≥2 evidence rows.  Each proposal carries a 4-step
    :class:`ReasoningTrace` (observation → grouping → hypothesis →
    conclusion).

    Determinism contract
    --------------------
    - Group iteration order is sorted by ``(refusal_reason,
      missing_operator)``.
    - Evidence per group is sorted by ``case_id``.
    - Output tuple is sorted by ``proposal_id``.
    - The same input file produces a byte-identical proposal stream
      across every rerun.

    Trust boundary
    --------------
    Pure read-only.  ``audit_path`` is read once; no file is written.
    Decomposer is teaching-layer code only — does not import from
    ``chat``/``field``/``generate.stream``/``algebra``.
    """

    raw = audit_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    per_case = data.get("per_case", []) or []

    rows: list[AuditRow] = []
    for case in per_case:
        if not isinstance(case, dict):
            continue
        if not case.get("case_id"):
            continue
        rows.append(_audit_row_from_case(case))

    evidence_records = audit_to_evidence(rows)

    groups: dict[tuple[str, str], list[MathReaderRefusalEvidence]] = {}
    for ev in evidence_records:
        if ev.missing_operator is None:
            continue
        key = (ev.refusal_reason, ev.missing_operator)
        groups.setdefault(key, []).append(ev)

    proposals: list[MathReaderRefusalShapeProposal] = []
    for key in sorted(groups.keys()):
        refusal_reason, missing_operator = key
        group_evs = tuple(sorted(groups[key], key=lambda e: e.case_id))
        if len(group_evs) < 2:
            continue
        proposals.append(
            _build_proposal_for_group(
                refusal_reason=refusal_reason,
                missing_operator=missing_operator,
                evidence=group_evs,
            )
        )

    return tuple(sorted(proposals, key=lambda p: p.proposal_id))


__all__ = [
    "audit_to_evidence",
    "audit_problem_to_evidence",
    "decompose_audit",
]
