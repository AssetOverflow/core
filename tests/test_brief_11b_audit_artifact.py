"""Brief 11B — pin the audit artifact and the extended missing-operator
inference labels added in this PR.

Hard invariants:

* ``wrong == 0`` (this PR does not change the reader runtime).
* The audit artifact at ``evals/gsm8k_math/train_sample/v1/audit_brief_11.json``
  is reproducible from ``audit_problem`` over the sealed train-sample.
* Every refused case now carries a non-None ``missing_operator`` label.
* The three new labels introduced in this PR fire on the documented
  detail-string patterns.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from generate.comprehension.audit import (
    _infer_missing_operator,
    audit_problem,
)
from generate.comprehension.state import ReaderRefusal

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
ARTIFACT_PATH = REPO_ROOT / "evals/gsm8k_math/train_sample/v1/audit_brief_11.json"


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    with CASES_PATH.open() as f:
        return [json.loads(line) for line in f]


@pytest.fixture(scope="module")
def artifact() -> dict:
    with ARTIFACT_PATH.open() as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Extended inference rule tests (the three new labels).
# ---------------------------------------------------------------------------


def test_pre_frame_filler_sentence_label():
    detail = (
        "category 'statement_terminator' (word='.') at pre-frame position 7 "
        "not handled; may be Phase-3 scope"
    )
    assert (
        _infer_missing_operator("unexpected_category", detail)
        == "pre_frame_filler_sentence"
    )


def test_descriptive_frame_question_label():
    detail = "category 'question_terminator' (word='?') not drainable in descriptive_frame"
    assert (
        _infer_missing_operator("unexpected_category", detail)
        == "descriptive_frame_question"
    )


def test_question_frame_slot_label():
    detail = "question_frame missing required slot(s): unit_class"
    assert (
        _infer_missing_operator("incomplete_operation", detail)
        == "question_frame_slot"
    )


def test_pre_frame_label_does_not_capture_multi_subject():
    detail = (
        "second entity 'Bob' at pre-frame position 3; multi-subject sentences "
        "are Phase-2.1 scope"
    )
    assert (
        _infer_missing_operator("unexpected_category", detail)
        == "multi_subject_sentence"
    )


# ---------------------------------------------------------------------------
# Artifact reproducibility.
# ---------------------------------------------------------------------------


def test_artifact_exists_and_has_expected_shape(artifact):
    assert artifact["schema_version"] == 1
    assert artifact["case_count"] == 50
    assert artifact["summary"]["admitted"] == 0
    assert artifact["summary"]["refused"] == 50
    assert artifact["invariants"]["wrong_count"] == 0
    assert artifact["invariants"]["reader_runtime_changes_in_this_pr"] is False
    assert len(artifact["per_case"]) == 50


def test_artifact_reproduces_from_audit(cases, artifact):
    """Every per-case row in the artifact must round-trip from audit_problem."""
    by_id = {row["case_id"]: row for row in artifact["per_case"]}
    for case in cases:
        cid = case["case_id"]
        result, rows = audit_problem(case["question"], case_id=cid)
        expected = by_id[cid]
        if isinstance(result, ReaderRefusal):
            assert expected["outcome"] == "refused"
            assert expected["refusal_reason"] == result.reason
            assert expected["sentence_index"] == result.sentence_index
            assert expected["token_index"] == result.token_index
            assert expected["token_text"] == result.token_text
            assert expected["refusal_detail"] == result.detail
            if rows:
                assert expected["missing_operator"] == rows[0].missing_operator
                assert expected["recognized_terms"] == list(rows[0].recognized_terms)
                assert expected["skipped_frame"] == rows[0].skipped_frame
        elif result is None:
            assert expected["outcome"] == "no_sentences"
        else:
            assert expected["outcome"] == "admitted"


def test_every_refused_case_has_labeled_operator(artifact):
    """No more None-operator refusals — Brief 11B closes the inference gap."""
    for row in artifact["per_case"]:
        if row["outcome"] != "refused":
            continue
        assert row["missing_operator"] is not None, (
            f"{row['case_id']}: refused with no labeled missing_operator "
            f"(reason={row['refusal_reason']!r}, detail={row['refusal_detail']!r})"
        )


def test_new_labels_present_in_summary(artifact):
    """The three new labels must be represented in the artifact."""
    ops = artifact["summary"]["missing_operators"]
    assert ops.get("pre_frame_filler_sentence", 0) >= 1
    assert ops.get("descriptive_frame_question", 0) >= 1
    assert ops.get("question_frame_slot", 0) >= 1


def test_invariant_no_wrong_admission(artifact):
    """The load-bearing wrong=0 invariant."""
    assert artifact["invariants"]["wrong_count"] == 0
    assert artifact["summary"]["admitted"] == 0


def test_taxonomy_total_matches_refused_count(artifact):
    refused = artifact["summary"]["refused"]
    reason_total = sum(artifact["summary"]["refusal_reasons"].values())
    op_total = sum(artifact["summary"]["missing_operators"].values())
    assert reason_total == refused
    assert op_total == refused


# ---------------------------------------------------------------------------
# Audit row sample integrity — ensure recognized_terms is well-formed.
# ---------------------------------------------------------------------------


def test_recognized_terms_only_present_on_post_pre_frame_refusals(artifact):
    for row in artifact["per_case"]:
        if row["outcome"] != "refused":
            continue
        if row["sentence_index"] == 0 and row["token_index"] == 0:
            assert row.get("recognized_terms", []) == []


def test_refusal_reason_distribution_is_stable(artifact):
    """Pin the headline refusal counts so any reader runtime change must
    explicitly update this test alongside the artifact."""
    # Counts updated by Brief 11B-step-2 lexicon closure (12 drain_token
    # additions). The unknown_word row strictly decreased; previously-hidden
    # bottlenecks at downstream frames became visible (real new work, not
    # regression). See `audit_brief_11.md` for the before/after table.
    expected = {
        "incomplete_operation": 20,
        "unexpected_category": 17,
        "unknown_word": 5,
        "unattached_quantity": 4,
        "unresolved_pronoun": 3,
        "no_question_target": 1,
    }
    assert Counter(artifact["summary"]["refusal_reasons"]) == Counter(expected)
