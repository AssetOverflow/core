"""Brief 11B-step-2 — verb-classification analysis tests.

These tests pin the evidence in
``evals/gsm8k_math/train_sample/v1/audit_brief_11b_step_2_verb_classification.md``:

1. The 8 GSM8K train-sample cases that refuse with
   ``missing_operator == 'pre_frame_filler_sentence'`` are exactly
   the enumerated set.
2. With the failing sentence elided, each case still refuses (zero
   admissions available) — i.e. there is no safe lift in scope for
   Brief 11B-step-2.
3. The load-bearing ``wrong == 0`` invariant is preserved (this PR
   makes no runtime/pack changes); the canonical 50-case audit
   produces exactly 0 admissions and 0 wrong admissions.
4. The hazard case ``gsm8k-train-sample-v1-0050`` remains refused at
   pre-frame, never reaching ``assert_graph_complete``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from generate.comprehension.audit import audit_problem
from generate.comprehension.state import ReaderRefusal


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES_PATH = (
    _REPO_ROOT
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "cases.jsonl"
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


EXPECTED_FILLER_CASES = frozenset(
    {
        "gsm8k-train-sample-v1-0002",
        "gsm8k-train-sample-v1-0016",
        "gsm8k-train-sample-v1-0025",
        "gsm8k-train-sample-v1-0028",
        "gsm8k-train-sample-v1-0030",
        "gsm8k-train-sample-v1-0035",
        "gsm8k-train-sample-v1-0036",
        "gsm8k-train-sample-v1-0050",
    }
)


# Post-skip simulation expectations, transcribed from the analysis doc.
EXPECTED_POST_SKIP = {
    "gsm8k-train-sample-v1-0002": (
        "unexpected_category",
        "fraction_percentage_literal",
    ),
    "gsm8k-train-sample-v1-0016": (
        "unresolved_pronoun",
        "pronoun_resolution",
    ),
    "gsm8k-train-sample-v1-0025": (
        "unknown_word",
        "lexicon_entry",
    ),
    "gsm8k-train-sample-v1-0028": (
        "unresolved_pronoun",
        "pronoun_resolution",
    ),
    "gsm8k-train-sample-v1-0030": (
        "unresolved_pronoun",
        "pronoun_resolution",
    ),
    "gsm8k-train-sample-v1-0035": (
        "unattached_quantity",
        "unit_binding",
    ),
    "gsm8k-train-sample-v1-0036": (
        "unresolved_pronoun",
        "pronoun_resolution",
    ),
    "gsm8k-train-sample-v1-0050": (
        "unresolved_pronoun",
        "pronoun_resolution",
    ),
}


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    rows: list[dict] = []
    with _CASES_PATH.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_filler_cases_are_exactly_the_enumerated_set(cases: list[dict]) -> None:
    """The eight pre_frame_filler_sentence cases are the documented set."""
    actual: set[str] = set()
    for c in cases:
        _result, rows = audit_problem(c["question"], case_id=c["case_id"])
        if rows and rows[0].missing_operator == "pre_frame_filler_sentence":
            actual.add(c["case_id"])
    assert actual == EXPECTED_FILLER_CASES


@pytest.mark.parametrize("case_id", sorted(EXPECTED_FILLER_CASES))
def test_post_skip_simulation_still_refuses(
    case_id: str, cases: list[dict]
) -> None:
    """With the offending sentence elided, the problem still refuses.

    This is the load-bearing evidence that no case can be lifted from
    refused -> admitted by handling only the pre-frame filler. Every
    case has an additional downstream blocker.
    """
    case = next(c for c in cases if c["case_id"] == case_id)
    _result, rows = audit_problem(case["question"], case_id=case_id)
    assert rows, f"{case_id}: expected at least one audit row"
    si = rows[0].sentence_index
    assert si is not None, f"{case_id}: sentence_index is None"

    sents = [s for s in _SENTENCE_SPLIT_RE.split(case["question"].strip()) if s.strip()]
    remainder = " ".join(sents[:si] + sents[si + 1:])
    result2, rows2 = audit_problem(remainder, case_id=f"{case_id}-skip")

    # Must still refuse — i.e. not produce a complete graph.
    assert isinstance(result2, ReaderRefusal), (
        f"{case_id}: post-skip lifted to admitted ({type(result2).__name__}); "
        "the documented zero-lift claim would be violated"
    )
    assert rows2, f"{case_id}: post-skip audit produced no rows"

    expected_reason, expected_op = EXPECTED_POST_SKIP[case_id]
    assert rows2[0].refusal_reason == expected_reason, (
        f"{case_id}: post-skip refusal_reason drifted "
        f"{expected_reason!r} -> {rows2[0].refusal_reason!r}"
    )
    assert rows2[0].missing_operator == expected_op, (
        f"{case_id}: post-skip missing_operator drifted "
        f"{expected_op!r} -> {rows2[0].missing_operator!r}"
    )


def test_runtime_wrong_zero_preserved(cases: list[dict]) -> None:
    """50-case audit yields exactly 0 admissions and 0 wrong admissions.

    This is the load-bearing wrong=0 invariant for Brief 11B-step-2.
    Because this PR makes no runtime / pack change, the post-condition
    is identical to the parent PR #345 baseline.
    """
    admitted = 0
    refused = 0
    none_count = 0
    for c in cases:
        result, _rows = audit_problem(c["question"], case_id=c["case_id"])
        if result is None:
            none_count += 1
        elif isinstance(result, ReaderRefusal):
            refused += 1
        else:
            admitted += 1

    assert admitted == 0
    assert refused == 50
    assert none_count == 0


def test_hazard_case_0050_remains_refused_pre_frame(cases: list[dict]) -> None:
    """The hazard case is still refused at pre_frame_filler_sentence.

    Specifically: ``Operation(mark, add, 3, songs)`` never reaches
    ``assert_graph_complete`` because the first sentence refuses first.
    """
    case = next(
        c for c in cases if c["case_id"] == "gsm8k-train-sample-v1-0050"
    )
    result, rows = audit_problem(case["question"], case_id=case["case_id"])
    assert isinstance(result, ReaderRefusal)
    assert rows
    assert rows[0].missing_operator == "pre_frame_filler_sentence"
    assert rows[0].sentence_index == 0
