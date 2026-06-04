from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension.audit import AuditRow
from teaching.math_contemplation_proposal import build_proposal, to_jsonl_record
from teaching.math_evidence import from_audit_row
from teaching.math_reasoning_trace import ReasoningStep, build_trace
from workbench.api import WorkbenchApi
from workbench import readers

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPO_ROOT / "language_packs" / "data" / "en_core_math_v1"

def setup_isolated_workbench(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WorkbenchApi:
    # 1. Copy en_core_math_v1 to tmp_path
    target_pack = tmp_path / "en_core_math_v1"
    shutil.copytree(PACK_ROOT, target_pack)
    (target_pack / "lexicon").mkdir(exist_ok=True)
    (target_pack / "frames").mkdir(exist_ok=True)
    (target_pack / "compositions").mkdir(exist_ok=True)

    # Clear caches
    from generate.comprehension import lexicon as comprehension_lexicon
    from generate.comprehension import lifecycle
    comprehension_lexicon._CACHE.clear()
    lifecycle._get_lexicon.cache_clear()

    # 2. Redirect pack root in ratification handlers
    monkeypatch.setattr("teaching.math_lexical_ratification._default_pack_root", lambda: target_pack)
    monkeypatch.setattr("teaching.math_frame_ratification._default_pack_root", lambda: target_pack)
    monkeypatch.setattr("teaching.math_composition_ratification._default_pack_root", lambda: target_pack)

    # Redirect proposal file
    proposals_jsonl = tmp_path / "proposals.jsonl"
    proposals_jsonl.touch()
    monkeypatch.setattr(readers, "MATH_PROPOSALS_JSONL", proposals_jsonl)

    # Create WorkbenchApi
    api = WorkbenchApi()
    return api

def build_test_claim(surface: str, sub_type: str, case_id: str | None = None, missing_operator: str = "lexicon_entry", refusal_reason: str = "unknown_word") -> Any:
    row = AuditRow(
        case_id=case_id or f"case-{surface}",
        sentence_index=0,
        token_index=2,
        token_text=surface,
        recognized_terms=("Ava", "counts"),
        skipped_frame=None,
        missing_operator=missing_operator,
        refusal_reason=refusal_reason,
        refusal_detail=f"test refusal for '{surface}'",
    )
    return from_audit_row(row, sub_type)

def write_proposal_record(api: WorkbenchApi, proposal_id: str, record: dict[str, Any]) -> None:
    # Append to the mocked proposals.jsonl
    path = readers.MATH_PROPOSALS_JSONL
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

def make_and_write_proposal(
    api: WorkbenchApi,
    *,
    domain: str = "math",
    shape_category: ShapeCategory = ShapeCategory.UNCATEGORIZED,
    proposed_change_kind: str = "vocabulary_addition",
    evidence_surface: str = "widgets",
    evidence_sub_type: str = "lexical",
    missing_operator: str = "lexicon_entry",
    refusal_reason: str = "unknown_word",
    wrong_zero_assertion: str = "Proposal wrong zero assertion must be at least forty chars long.",
) -> Any:
    ev1 = build_test_claim(evidence_surface, evidence_sub_type, case_id="case-1", missing_operator=missing_operator, refusal_reason=refusal_reason)
    ev2 = build_test_claim(evidence_surface, evidence_sub_type, case_id="case-2", missing_operator=missing_operator, refusal_reason=refusal_reason)
    steps = (
        ReasoningStep(
            step_index=0,
            step_kind="observation",
            input_pointers=("case-1", "case-2"),
            claim="refusals share pattern",
            justification="grouped by key",
            output_payload={"evidence_count": 2},
        ),
        ReasoningStep(
            step_index=1,
            step_kind="grouping",
            input_pointers=("case-1", "case-2"),
            claim="group key",
            justification="pair equality",
            output_payload={"k": "v"},
        ),
        ReasoningStep(
            step_index=2,
            step_kind="hypothesis",
            input_pointers=("case-1", "case-2"),
            claim="change fits",
            justification="fits shape",
            output_payload={"proposed_change_kind": proposed_change_kind},
        ),
        ReasoningStep(
            step_index=3,
            step_kind="conclusion",
            input_pointers=("case-1", "case-2"),
            claim=f"propose {proposed_change_kind}",
            justification="evidence-only proposal",
            output_payload={"proposed_change_kind": proposed_change_kind},
        ),
    )
    trace = build_trace(steps)
    proposal = build_proposal(
        domain=domain,  # type: ignore[arg-type]
        shape_category=shape_category,
        structural_commonality="test commonality",
        evidence_pointers=(ev1, ev2),
        proposed_change_kind=proposed_change_kind,
        proposed_change_payload={"k": "v"},
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash="0" * 64,
        reasoning_trace=trace,
    )
    record = to_jsonl_record(proposal)
    write_proposal_record(api, proposal.proposal_id, record)
    return proposal
