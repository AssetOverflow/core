"""ADR-0172 W2 — Audit-corpus decomposer tests.

Pins :func:`teaching.math_contemplation.decompose_audit` against:

- the real ``evals/gsm8k_math/train_sample/v1/audit_brief_11.json`` audit;
- a synthetic mini-audit covering the four change-kind branches;
- determinism (10x rerun identity);
- evidence-floor (≥2-row threshold);
- sort contracts on evidence and proposal output;
- empty-input → empty-output;
- pure read-only behavior (no filesystem mutation).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from teaching.math_contemplation import decompose_audit
from teaching.math_contemplation_proposal import (
    MathReaderRefusalShapeProposal,
)

REAL_AUDIT_PATH = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "audit_brief_11.json"
)


# ---------------------------------------------------------------------------
# Helpers — synthetic audit fixtures
# ---------------------------------------------------------------------------


def _case(
    *,
    case_id: str,
    refusal_reason: str,
    missing_operator: str,
    sentence_index: int = 0,
    token_index: int = 0,
    token_text: str = "x",
    refusal_detail: str = "",
) -> dict:
    return {
        "case_id": case_id,
        "outcome": "refused",
        "refusal_reason": refusal_reason,
        "missing_operator": missing_operator,
        "refusal_detail": refusal_detail,
        "sentence_index": sentence_index,
        "token_index": token_index,
        "token_text": token_text,
        "recognized_terms": [],
        "skipped_frame": None,
    }


def _write_audit(tmp_path: Path, per_case: list[dict]) -> Path:
    audit = {
        "schema_version": 1,
        "brief": "synthetic-test",
        "case_count": len(per_case),
        "per_case": per_case,
    }
    target = tmp_path / "audit.json"
    target.write_text(json.dumps(audit), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_decompose_audit_emits_at_least_one_proposal() -> None:
    """Real audit_brief_11.json contains ≥1 multi-row group."""
    assert REAL_AUDIT_PATH.exists(), REAL_AUDIT_PATH
    proposals = decompose_audit(REAL_AUDIT_PATH)
    assert len(proposals) >= 1
    for p in proposals:
        assert isinstance(p, MathReaderRefusalShapeProposal)
        assert len(p.evidence_pointers) >= 2


def test_decompose_audit_deterministic_across_reruns() -> None:
    """Same input → byte-identical proposal stream across 10 reruns."""
    first = decompose_audit(REAL_AUDIT_PATH)
    first_ids = tuple(p.proposal_id for p in first)
    for _ in range(9):
        rerun = decompose_audit(REAL_AUDIT_PATH)
        assert tuple(p.proposal_id for p in rerun) == first_ids
        for left, right in zip(first, rerun):
            assert left == right
            assert left.reasoning_trace.trace_id == right.reasoning_trace.trace_id


def test_decompose_audit_minimum_evidence_threshold(tmp_path: Path) -> None:
    """Singleton groups MUST NOT emit a proposal."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="solo-0001",
                refusal_reason="unknown_word",
                missing_operator="lexicon_entry",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert proposals == ()


def test_decompose_audit_change_kind_dispatch(tmp_path: Path) -> None:
    """Each refusal_reason branch yields the expected change_kind.

    The dispatch heuristic keys on ``refusal_reason``.  We use the literal
    strings from the brief plus an ``other`` row that should fall through
    to ``injector_sub_shape``.  Each branch gets 2 rows so it actually
    emits a proposal.
    """
    branches = [
        ("lexicon_entry", "lexicon_entry", "vocabulary_addition"),
        ("narrowness_violation", "multi_quantity_composition", "matcher_extension"),
        ("frame_unrecognized", "pre_frame_filler_sentence", "frame_reclassification"),
        # ADR-0169 CC-3: (incomplete_operation, quantity_extraction) routes
        # to composition_reclassification via the pair table (formerly
        # fell through to injector_sub_shape).
        ("incomplete_operation", "quantity_extraction", "composition_reclassification"),
    ]
    per_case: list[dict] = []
    for refusal_reason, missing_operator, _kind in branches:
        per_case.append(
            _case(
                case_id=f"{refusal_reason}-a",
                refusal_reason=refusal_reason,
                missing_operator=missing_operator,
            )
        )
        per_case.append(
            _case(
                case_id=f"{refusal_reason}-b",
                refusal_reason=refusal_reason,
                missing_operator=missing_operator,
            )
        )
    audit = _write_audit(tmp_path, per_case)

    proposals = decompose_audit(audit)
    by_reason = {
        p.evidence_pointers[0].refusal_reason: p for p in proposals
    }
    for refusal_reason, _missing, expected_kind in branches:
        assert refusal_reason in by_reason, refusal_reason
        assert by_reason[refusal_reason].proposed_change_kind == expected_kind


def test_decompose_audit_reasoning_trace_has_four_steps(tmp_path: Path) -> None:
    """Every emitted proposal carries an exactly-4-step trace."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="t-0001",
                refusal_reason="lexicon_entry",
                missing_operator="lexicon_entry",
            ),
            _case(
                case_id="t-0002",
                refusal_reason="lexicon_entry",
                missing_operator="lexicon_entry",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    trace = proposals[0].reasoning_trace
    assert len(trace.steps) == 4
    assert [s.step_kind for s in trace.steps] == [
        "observation",
        "grouping",
        "hypothesis",
        "conclusion",
    ]


def test_decompose_audit_evidence_sorted_by_case_id(tmp_path: Path) -> None:
    """Evidence ordering inside a proposal is case_id-sorted."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="zzz-last",
                refusal_reason="lexicon_entry",
                missing_operator="lexicon_entry",
            ),
            _case(
                case_id="aaa-first",
                refusal_reason="lexicon_entry",
                missing_operator="lexicon_entry",
            ),
            _case(
                case_id="mmm-mid",
                refusal_reason="lexicon_entry",
                missing_operator="lexicon_entry",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    ids = [ev.case_id for ev in proposals[0].evidence_pointers]
    assert ids == sorted(ids)
    assert ids == ["aaa-first", "mmm-mid", "zzz-last"]


def test_decompose_audit_proposal_ids_sorted(tmp_path: Path) -> None:
    """Output tuple is sorted by proposal_id."""
    per_case: list[dict] = []
    for group in ("lexicon_entry", "narrowness_violation", "frame_unrecognized"):
        per_case.append(
            _case(
                case_id=f"{group}-0001",
                refusal_reason=group,
                missing_operator="lexicon_entry"
                if group == "lexicon_entry"
                else (
                    "multi_quantity_composition"
                    if group == "narrowness_violation"
                    else "pre_frame_filler_sentence"
                ),
            )
        )
        per_case.append(
            _case(
                case_id=f"{group}-0002",
                refusal_reason=group,
                missing_operator="lexicon_entry"
                if group == "lexicon_entry"
                else (
                    "multi_quantity_composition"
                    if group == "narrowness_violation"
                    else "pre_frame_filler_sentence"
                ),
            )
        )
    audit = _write_audit(tmp_path, per_case)
    proposals = decompose_audit(audit)
    ids = [p.proposal_id for p in proposals]
    assert len(ids) >= 2
    assert ids == sorted(ids)


def test_decompose_audit_empty_file_returns_empty_tuple(tmp_path: Path) -> None:
    """Audit with ``per_case == []`` yields ``()``."""
    audit = _write_audit(tmp_path, [])
    assert decompose_audit(audit) == ()


def test_decompose_audit_no_runtime_mutation(tmp_path: Path) -> None:
    """Decomposer is read-only: audit file bytes unchanged, no sibling files."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="ro-0001",
                refusal_reason="lexicon_entry",
                missing_operator="lexicon_entry",
            ),
            _case(
                case_id="ro-0002",
                refusal_reason="lexicon_entry",
                missing_operator="lexicon_entry",
            ),
        ],
    )
    before_bytes = audit.read_bytes()
    before_listing = sorted(p.name for p in tmp_path.iterdir())

    _ = decompose_audit(audit)

    assert audit.read_bytes() == before_bytes
    after_listing = sorted(p.name for p in tmp_path.iterdir())
    assert after_listing == before_listing


def test_decompose_audit_skips_rows_without_known_operator(tmp_path: Path) -> None:
    """Rows whose missing_operator is unmapped (or null) are dropped silently."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="skip-0001",
                refusal_reason="lexicon_entry",
                missing_operator="not_a_real_operator",
            ),
            _case(
                case_id="skip-0002",
                refusal_reason="lexicon_entry",
                missing_operator="not_a_real_operator",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert proposals == ()


def test_decompose_audit_missing_file_raises(tmp_path: Path) -> None:
    """A non-existent audit path raises (no silent empty-tuple swallow)."""
    with pytest.raises(FileNotFoundError):
        decompose_audit(tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# ADR-0172 tightening follow-up #2 — pair-based dispatch table
# ---------------------------------------------------------------------------


def test_decompose_audit_pair_dispatch_unexpected_category_matcher(
    tmp_path: Path,
) -> None:
    """(unexpected_category, pre_frame_filler_sentence) → matcher_extension."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="pf-001",
                refusal_reason="unexpected_category",
                missing_operator="pre_frame_filler_sentence",
            ),
            _case(
                case_id="pf-002",
                refusal_reason="unexpected_category",
                missing_operator="pre_frame_filler_sentence",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    assert proposals[0].proposed_change_kind == "matcher_extension"


def test_decompose_audit_pair_dispatch_multi_subject_sentence_injector(
    tmp_path: Path,
) -> None:
    """(unexpected_category, multi_subject_sentence) → injector_sub_shape (ADR-0169 CC-3).

    Demoted from frame_reclassification at the 2026-05-27 end-to-end demo:
    the FrameClaim SAFE_FRAME_CATEGORIES allowlist (increment_frame,
    decrement_frame, transfer_frame, remainder_frame) does not cover
    multi_subject_sentence shapes — those need ReferenceClaim /
    CompositionClaim, not FrameClaim.  Until those handlers ship, this
    pair falls through to injector_sub_shape.
    """
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="ms-001",
                refusal_reason="unexpected_category",
                missing_operator="multi_subject_sentence",
            ),
            _case(
                case_id="ms-002",
                refusal_reason="unexpected_category",
                missing_operator="multi_subject_sentence",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    assert proposals[0].proposed_change_kind == "injector_sub_shape"


def test_decompose_audit_pair_dispatch_descriptive_frame_question_injector(
    tmp_path: Path,
) -> None:
    """(unexpected_category, descriptive_frame_question) → injector_sub_shape (ADR-0169 CC-3).

    Demoted from frame_reclassification: needs SlotClaim, not FrameClaim.
    """
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="dfq-001",
                refusal_reason="unexpected_category",
                missing_operator="descriptive_frame_question",
            ),
            _case(
                case_id="dfq-002",
                refusal_reason="unexpected_category",
                missing_operator="descriptive_frame_question",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    assert proposals[0].proposed_change_kind == "injector_sub_shape"


def test_quantity_extraction_routes_to_composition_reclassification(
    tmp_path: Path,
) -> None:
    """(incomplete_operation, quantity_extraction) → composition_reclassification (ADR-0169 CC-3)."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="qe-001",
                refusal_reason="incomplete_operation",
                missing_operator="quantity_extraction",
            ),
            _case(
                case_id="qe-002",
                refusal_reason="incomplete_operation",
                missing_operator="quantity_extraction",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    assert proposals[0].proposed_change_kind == "composition_reclassification"


def test_multi_quantity_composition_routes_to_composition_reclassification(
    tmp_path: Path,
) -> None:
    """(incomplete_operation, multi_quantity_composition) → composition_reclassification (ADR-0169 CC-3)."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="mqc-001",
                refusal_reason="incomplete_operation",
                missing_operator="multi_quantity_composition",
            ),
            _case(
                case_id="mqc-002",
                refusal_reason="incomplete_operation",
                missing_operator="multi_quantity_composition",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    assert proposals[0].proposed_change_kind == "composition_reclassification"


def test_decompose_audit_pair_dispatch_pronoun(tmp_path: Path) -> None:
    """(unresolved_pronoun, pronoun_resolution) → matcher_extension."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="pr-001",
                refusal_reason="unresolved_pronoun",
                missing_operator="pronoun_resolution",
            ),
            _case(
                case_id="pr-002",
                refusal_reason="unresolved_pronoun",
                missing_operator="pronoun_resolution",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    assert proposals[0].proposed_change_kind == "matcher_extension"


def test_decompose_audit_real_audit_change_kind_distribution() -> None:
    """Against the real audit_brief_11.json, dispatch yields the expected mix.

    Per ADR-0169 CC-3, the tightened heuristic must produce on the
    train-sample audit:
      - 3 matcher_extension proposals (pre_frame_filler, fraction_percentage,
        unresolved_pronoun)
      - 2 composition_reclassification proposals (quantity_extraction,
        multi_quantity_composition) — 20 of 47 cases
      - 3 injector_sub_shape proposals (multi_subject_sentence and
        descriptive_frame_question demoted per CC-3, plus
        unattached_quantity/unit_binding catch-all)
      - 0 frame_reclassification proposals (the two prior routes were
        demoted; audit_brief_11.json has no frame_unrecognized rows)
    """
    proposals = decompose_audit(REAL_AUDIT_PATH)
    kinds = [p.proposed_change_kind for p in proposals]
    matcher = sum(1 for k in kinds if k == "matcher_extension")
    composition = sum(1 for k in kinds if k == "composition_reclassification")
    frame = sum(1 for k in kinds if k == "frame_reclassification")
    injector = sum(1 for k in kinds if k == "injector_sub_shape")
    assert matcher == 3, f"expected 3 matcher_extension, got {matcher}: {kinds}"
    assert composition == 2, (
        f"expected 2 composition_reclassification, got {composition}: {kinds}"
    )
    assert frame == 0, f"expected 0 frame_reclassification, got {frame}: {kinds}"
    assert injector == 3, f"expected 3 injector_sub_shape, got {injector}: {kinds}"


# ---------------------------------------------------------------------------
# ADR-0172 tightening follow-up #3 — shape_category structural gap
# ---------------------------------------------------------------------------


def test_decompose_audit_shape_category_is_uncategorized(tmp_path: Path) -> None:
    """Until shape_category is added to MathReaderRefusalEvidence, all proposals
    emit ShapeCategory.UNCATEGORIZED — do NOT invent values."""
    from evals.refusal_taxonomy.shape_categories import ShapeCategory

    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="sc-001",
                refusal_reason="unexpected_category",
                missing_operator="pre_frame_filler_sentence",
            ),
            _case(
                case_id="sc-002",
                refusal_reason="unexpected_category",
                missing_operator="pre_frame_filler_sentence",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert proposals
    assert all(p.shape_category == ShapeCategory.UNCATEGORIZED for p in proposals)
