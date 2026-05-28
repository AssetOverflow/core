"""Brief B — Ratifiable payload tests for contemplation proposals.

Pins that ``decompose_audit`` emits ``proposed_change_payload`` fields that
satisfy ``apply_composition_claim()`` preconditions directly, with no
operator-side field synthesis.

Coverage:
1.  quantity_extraction group → payload carries composition_category,
    surface_pattern, polarity.
2.  multi_quantity_composition group → payload carries the additive fields.
3.  Legacy fields (evidence_count, group_key, modal_sub_type) still present
    (backward-compat schema regression).
4.  Non-composition change kinds (matcher_extension, injector_sub_shape,
    frame_reclassification) do NOT get the enriched fields.
5.  Enriched payload fields satisfy apply_composition_claim preconditions.
6.  Round-trip: real audit composition proposal → apply_composition_claim
    without any field synthesis.
7.  polarity is always "affirms" in the enriched payload.
8.  Determinism: payload is identical across reruns.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from generate.comprehension import lexicon as comprehension_lexicon
from generate.comprehension import lifecycle
from teaching.math_composition_ratification import (
    SAFE_COMPOSITION_CATEGORIES,
    apply_composition_claim,
)
from teaching.math_contemplation import decompose_audit


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPO_ROOT / "language_packs" / "data" / "en_core_math_v1"
REAL_AUDIT_PATH = (
    REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "audit_brief_11.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _case(
    *,
    case_id: str,
    refusal_reason: str,
    missing_operator: str,
    token_text: str = "x",
) -> dict:
    return {
        "case_id": case_id,
        "outcome": "refused",
        "refusal_reason": refusal_reason,
        "missing_operator": missing_operator,
        "refusal_detail": "",
        "sentence_index": 0,
        "token_index": 0,
        "token_text": token_text,
        "recognized_terms": [],
        "skipped_frame": None,
    }


def _write_audit(tmp_path: Path, per_case: list[dict]) -> Path:
    audit = {
        "schema_version": 1,
        "brief": "synthetic-ratifiable-payload-test",
        "case_count": len(per_case),
        "per_case": per_case,
    }
    target = tmp_path / "audit.json"
    target.write_text(json.dumps(audit), encoding="utf-8")
    return target


@pytest.fixture()
def pack_copy(tmp_path: Path) -> Path:
    target = tmp_path / "en_core_math_v1"
    shutil.copytree(PACK_ROOT, target)
    (target / "compositions").mkdir(exist_ok=True)
    # ensure additive_composition.jsonl exists for round-trip
    (target / "compositions" / "additive_composition.jsonl").write_text(
        "", encoding="utf-8"
    )
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()
    yield target
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()


# ---------------------------------------------------------------------------
# 1. quantity_extraction payload
# ---------------------------------------------------------------------------


def test_quantity_extraction_payload_has_ratifiable_fields(tmp_path: Path) -> None:
    """quantity_extraction group payload carries composition_category, surface_pattern, polarity."""
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
    payload = proposals[0].proposed_change_payload
    assert isinstance(payload, dict)
    assert payload["composition_category"] == "multiplicative_composition"
    assert payload["surface_pattern"] == "bound(count) × bound(unit_cost)"
    assert payload["polarity"] == "affirms"


# ---------------------------------------------------------------------------
# 2. multi_quantity_composition payload
# ---------------------------------------------------------------------------


def test_multi_quantity_composition_payload_has_ratifiable_fields(
    tmp_path: Path,
) -> None:
    """multi_quantity_composition group payload carries the additive fields."""
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
    payload = proposals[0].proposed_change_payload
    assert isinstance(payload, dict)
    assert payload["composition_category"] == "additive_composition"
    assert payload["surface_pattern"] == "bound(qty_a) + bound(qty_b)"
    assert payload["polarity"] == "affirms"


# ---------------------------------------------------------------------------
# 3. Legacy fields preserved (backward-compat schema regression)
# ---------------------------------------------------------------------------


def test_composition_payload_preserves_legacy_fields(tmp_path: Path) -> None:
    """evidence_count, group_key, modal_sub_type must still be present."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="leg-001",
                refusal_reason="incomplete_operation",
                missing_operator="quantity_extraction",
            ),
            _case(
                case_id="leg-002",
                refusal_reason="incomplete_operation",
                missing_operator="quantity_extraction",
            ),
            _case(
                case_id="leg-003",
                refusal_reason="incomplete_operation",
                missing_operator="quantity_extraction",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    payload = proposals[0].proposed_change_payload
    assert isinstance(payload, dict)
    assert payload["evidence_count"] == 3
    assert payload["group_key"] == {
        "missing_operator": "quantity_extraction",
        "refusal_reason": "incomplete_operation",
    }
    assert "modal_sub_type" in payload


def test_multi_qty_payload_preserves_legacy_fields(tmp_path: Path) -> None:
    """multi_quantity_composition also preserves legacy fields."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="mql-001",
                refusal_reason="incomplete_operation",
                missing_operator="multi_quantity_composition",
            ),
            _case(
                case_id="mql-002",
                refusal_reason="incomplete_operation",
                missing_operator="multi_quantity_composition",
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    payload = proposals[0].proposed_change_payload
    assert "evidence_count" in payload
    assert "group_key" in payload
    assert "modal_sub_type" in payload


# ---------------------------------------------------------------------------
# 4. Non-composition kinds do NOT get enriched fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "refusal_reason,missing_operator",
    [
        ("unexpected_category", "pre_frame_filler_sentence"),
        ("unexpected_category", "multi_subject_sentence"),
        ("narrowness_violation", "multi_quantity_composition"),
    ],
)
def test_non_composition_payload_not_enriched(
    tmp_path: Path, refusal_reason: str, missing_operator: str
) -> None:
    """Non-composition change kinds must not carry composition_category etc."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="nc-001",
                refusal_reason=refusal_reason,
                missing_operator=missing_operator,
            ),
            _case(
                case_id="nc-002",
                refusal_reason=refusal_reason,
                missing_operator=missing_operator,
            ),
        ],
    )
    proposals = decompose_audit(audit)
    assert len(proposals) == 1
    payload = proposals[0].proposed_change_payload
    assert isinstance(payload, dict)
    assert "composition_category" not in payload
    assert "surface_pattern" not in payload
    assert "polarity" not in payload


# ---------------------------------------------------------------------------
# 5. Enriched fields satisfy apply_composition_claim preconditions
# ---------------------------------------------------------------------------


def test_enriched_fields_satisfy_apply_composition_claim_preconditions(
    tmp_path: Path,
) -> None:
    """Each enriched composition_category is in SAFE_COMPOSITION_CATEGORIES."""
    for missing_operator, refusal_reason in [
        ("quantity_extraction", "incomplete_operation"),
        ("multi_quantity_composition", "incomplete_operation"),
    ]:
        sub = tmp_path / missing_operator
        sub.mkdir()
        audit = _write_audit(
            sub,
            [
                _case(
                    case_id=f"{missing_operator}-p-001",
                    refusal_reason=refusal_reason,
                    missing_operator=missing_operator,
                ),
                _case(
                    case_id=f"{missing_operator}-p-002",
                    refusal_reason=refusal_reason,
                    missing_operator=missing_operator,
                ),
            ],
        )
        proposals = decompose_audit(audit)
        assert len(proposals) == 1
        payload = proposals[0].proposed_change_payload
        assert isinstance(payload, dict)
        assert payload["composition_category"] in SAFE_COMPOSITION_CATEGORIES
        assert payload["polarity"] in {"affirms", "falsifies"}
        assert payload["surface_pattern"].strip()


# ---------------------------------------------------------------------------
# 6. Round-trip: real audit composition proposal → apply_composition_claim
# ---------------------------------------------------------------------------


def test_round_trip_composition_proposal_into_apply_composition_claim(
    pack_copy: Path,
) -> None:
    """First composition_reclassification proposal from real audit → apply_composition_claim
    without operator-side field synthesis."""
    assert REAL_AUDIT_PATH.exists(), REAL_AUDIT_PATH

    proposals = decompose_audit(REAL_AUDIT_PATH)
    comp_proposals = [
        p
        for p in proposals
        if p.proposed_change_kind == "composition_reclassification"
    ]
    assert comp_proposals, "real audit must produce at least one composition_reclassification proposal"

    proposal = comp_proposals[0]
    payload = proposal.proposed_change_payload
    assert isinstance(payload, dict)

    # All fields needed by apply_composition_claim come straight from the payload
    composition_category: str = payload["composition_category"]
    surface_pattern: str = payload["surface_pattern"]
    polarity: str = payload["polarity"]

    # Use the first evidence pointer's backing record
    evidence_record = proposal.evidence_pointers[0]

    # apply_composition_claim must succeed without exception
    receipt = apply_composition_claim(
        claim=evidence_record,
        composition_category=composition_category,
        polarity=polarity,
        reviewer="test_round_trip",
        surface_pattern=surface_pattern,
        pack_root=pack_copy,
    )
    assert receipt.composition_category == composition_category
    assert receipt.polarity == polarity


# ---------------------------------------------------------------------------
# 7. polarity is always "affirms" in enriched payload
# ---------------------------------------------------------------------------


def test_composition_payload_polarity_is_always_affirms(tmp_path: Path) -> None:
    """polarity must be 'affirms' in all auto-generated composition payloads."""
    for missing_operator in ("quantity_extraction", "multi_quantity_composition"):
        sub = tmp_path / missing_operator
        sub.mkdir(exist_ok=True)
        audit = _write_audit(
            sub,
            [
                _case(
                    case_id=f"pol-{missing_operator}-001",
                    refusal_reason="incomplete_operation",
                    missing_operator=missing_operator,
                ),
                _case(
                    case_id=f"pol-{missing_operator}-002",
                    refusal_reason="incomplete_operation",
                    missing_operator=missing_operator,
                ),
            ],
        )
        proposals = decompose_audit(audit)
        assert len(proposals) == 1
        assert proposals[0].proposed_change_payload["polarity"] == "affirms"


# ---------------------------------------------------------------------------
# 8. Determinism: payload is identical across reruns
# ---------------------------------------------------------------------------


def test_enriched_payload_deterministic_across_reruns(tmp_path: Path) -> None:
    """Same audit → byte-identical payload across 5 reruns."""
    audit = _write_audit(
        tmp_path,
        [
            _case(
                case_id="det-001",
                refusal_reason="incomplete_operation",
                missing_operator="quantity_extraction",
            ),
            _case(
                case_id="det-002",
                refusal_reason="incomplete_operation",
                missing_operator="quantity_extraction",
            ),
        ],
    )
    first = decompose_audit(audit)
    first_payload = json.dumps(
        first[0].proposed_change_payload, sort_keys=True, separators=(",", ":")
    )
    for _ in range(4):
        rerun = decompose_audit(audit)
        rerun_payload = json.dumps(
            rerun[0].proposed_change_payload, sort_keys=True, separators=(",", ":")
        )
        assert rerun_payload == first_payload
