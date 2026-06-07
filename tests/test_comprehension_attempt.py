"""Tests for the shared ComprehensionAttempt normalizer (N2).

Pins that `classify_r1` / `classify_r2` faithfully normalize each organ's output against the
existing gold: well-formed fixtures → `setup_correct` with a deterministic signature; refused
fixtures → `setup_refused` carrying the organ's typed reason. No gold comparison, no solving.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.comprehension_attempt import classify_r1, classify_r2
from evals.constraint_oracle.runner import _load_r2_gold
from evals.setup_oracle.runner import _load_r1_gold


def test_classify_r2_matches_gold_expect() -> None:
    for fx in _load_r2_gold():
        att = classify_r2(fx["text"], case_id=fx["id"])
        assert att.organ == "r2_constraints"
        if fx["expect"] in ("solved", "solver_refuses"):
            assert att.outcome == "setup_correct", f"{fx['id']}: {att.refusal_reason}"
            assert att.setup_signature is not None
        else:  # reader_refuses
            assert att.outcome == "setup_refused"
            assert att.refusal_reason == fx["reader_reason"], fx["id"]


def test_classify_r1_admits_seven_refuses_three() -> None:
    attempts = [classify_r1(fx["text"], case_id=fx["id"]) for fx in _load_r1_gold()]
    correct = [a for a in attempts if a.outcome == "setup_correct"]
    refused = [a for a in attempts if a.outcome == "setup_refused"]
    assert len(correct) == 7 and len(refused) == 3
    assert all(a.organ == "r1_quantitative" for a in attempts)
    assert all(a.setup_signature is not None for a in correct)
    assert all(a.refusal_reason for a in refused)


def test_classify_r1_specific_inverse_and_pronoun() -> None:
    inverse = classify_r1("Nia has 9 more beads than Omar. Nia has 15 beads. How many beads does Omar have?")
    assert inverse.outcome == "setup_correct"
    pronoun = classify_r1("Pat has 5 marbles. He has 3 more than her. How many marbles does she have?")
    assert pronoun.outcome == "setup_refused" and pronoun.refusal_reason is not None


def test_signatures_are_deterministic() -> None:
    text = next(f for f in _load_r2_gold() if f["expect"] == "solved")["text"]
    assert classify_r2(text).setup_signature == classify_r2(text).setup_signature


def test_attempt_is_frozen() -> None:
    att = classify_r2("A school rents 6 buses. How many large buses are there?")
    with pytest.raises(dataclasses.FrozenInstanceError):
        att.outcome = "setup_correct"  # type: ignore[misc]


def test_classify_does_not_import_evals() -> None:
    # core/comprehension_attempt must not depend on evals (runtime must not import the harness).
    import inspect

    import core.comprehension_attempt.classify as m

    source = inspect.getsource(m)
    assert "import evals" not in source and "from evals" not in source
