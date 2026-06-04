from __future__ import annotations

import json
import functools
from pathlib import Path
import pytest

from generate.comprehension import lexicon as comprehension_lexicon
from generate.comprehension import lifecycle
from generate.comprehension.audit import audit_problem
from generate.comprehension.state import ReaderRefusal
from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"


def _use_pack_for_reader(monkeypatch: pytest.MonkeyPatch, pack_root: Path) -> None:
    comprehension_lexicon._CACHE.clear()

    @functools.cache
    def _tmp_lexicon():
        return comprehension_lexicon.load_lexicon(pack_root)

    monkeypatch.setattr(lifecycle, "_get_lexicon", _tmp_lexicon)


def test_case_0050_remains_refused_after_ui_ratification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    pack_root = tmp_path / "en_core_math_v1"

    # 1. UI Ratify Lexical Claim
    proposal_lex = make_and_write_proposal(
        api,
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="lexical",
        missing_operator="drain_token",
        refusal_reason="unknown_word",
    )
    body_lex = json.dumps({"category": "drain_token"}).encode("utf-8")
    resp_lex = api.handle("POST", f"/math-proposals/{proposal_lex.proposal_id}/ratify", body_lex)
    assert resp_lex.status == 200

    # 2. UI Ratify Frame Claim
    proposal_frame = make_and_write_proposal(
        api,
        proposed_change_kind="frame_reclassification",
        evidence_surface="gives",
        evidence_sub_type="frame",
        missing_operator="transfer_frame",
        refusal_reason="unexpected_category",
    )
    body_frame = json.dumps({"category": "transfer_frame", "polarity": "affirms"}).encode("utf-8")
    resp_frame = api.handle("POST", f"/math-proposals/{proposal_frame.proposal_id}/ratify", body_frame)
    assert resp_frame.status == 200

    # 3. UI Ratify Composition Claim
    proposal_comp = make_and_write_proposal(
        api,
        proposed_change_kind="composition_reclassification",
        evidence_surface="each",
        evidence_sub_type="composition",
        missing_operator="quantity_extraction",
        refusal_reason="incomplete_operation",
    )
    body_comp = json.dumps({"category": "multiplicative_composition", "polarity": "affirms"}).encode("utf-8")
    resp_comp = api.handle("POST", f"/math-proposals/{proposal_comp.proposal_id}/ratify", body_comp)
    assert resp_comp.status == 200

    # Hook the reader to use the mutated pack copy
    _use_pack_for_reader(monkeypatch, pack_root)

    # Load and check case 0050
    cases = [json.loads(line) for line in CASES_PATH.read_text().splitlines()]
    case = next(c for c in cases if c["case_id"] == "gsm8k-train-sample-v1-0050")

    result, _rows = audit_problem(case["question"], case_id=case["case_id"])

    assert isinstance(result, ReaderRefusal), "case 0050 must remain refused after ratification"
    assert result.sentence_index == 0
