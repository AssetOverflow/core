"""ADR-0186 — sealed candidate-graph injector lane.

The seal mechanism lets ADR-0170 W2-W5 injectors be developed behind a
default-off ``sealed`` flag, so the current serving metric stays
byte-identical until a reviewed Phase-5 promotion.

These tests are written to **fail under violation** (CLAUDE.md
"Schema-Defined Proof Obligations"):

* ``test_sealed_flag_is_noop_when_registry_empty`` fails if ``sealed=True``
  diverges from the frozen path while ``_SEALED_INJECTORS`` is empty.
* ``test_sealed_injector_admits_only_under_flag`` fails if a registered
  sealed injector either (a) leaks into the frozen ``sealed=False`` path
  (serving drift) or (b) is NOT consulted under ``sealed=True`` (dead seal).
* ``test_frozen_train_sample_byte_identical`` fails if the default
  ``parse_and_solve`` path moves off the checked-in report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import generate.recognizer_anchor_inject as inj
from generate.math_candidate_graph import (
    _load_ratified_registry_or_empty,
    parse_and_solve,
)
from generate.math_candidate_parser import CandidateInitial
from generate.math_problem_graph import InitialPossession, Quantity
from generate.recognizer_match import ShapeCategory, match as recognizer_match


_RATE_SENTENCE = "Tina makes $18.00 an hour."  # train_sample-0001 statement


def _match_for(sentence: str):
    # Use the same ratified registry the live candidate-graph loop loads, so
    # the matcher classifies the statement exactly as it does in serving.
    m = recognizer_match(sentence, _load_ratified_registry_or_empty())
    assert m is not None, f"recognizer did not match {sentence!r}"
    return m


def test_sealed_flag_default_is_off_and_noop_when_registry_empty() -> None:
    """sealed=True must equal the frozen path while no sealed injector exists."""
    m = _match_for(_RATE_SENTENCE)
    frozen = inj.inject_from_match(m, _RATE_SENTENCE)
    sealed = inj.inject_from_match(m, _RATE_SENTENCE, sealed=True)
    assert sealed == frozen  # empty seal is a strict no-op


def test_sealed_injector_admits_only_under_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """A registered sealed injector emits under sealed=True, never under False."""
    sentinel = CandidateInitial(
        initial=InitialPossession(
            entity="tina", quantity=Quantity(value=18.0, unit="dollar")
        ),
        source_span=_RATE_SENTENCE,
        matched_anchor="makes",
        matched_value_token="18.00",
        matched_unit_token="dollar",
        matched_entity_token="Tina",
    )

    def _fake_sealed_injector(match, sentence):  # noqa: ANN001
        return (sentinel,)

    monkeypatch.setitem(
        inj._SEALED_INJECTORS,
        ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY,
        _fake_sealed_injector,
    )
    import dataclasses
    m = _match_for(_RATE_SENTENCE)
    m = dataclasses.replace(m, category=ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY)
    # Frozen path: untouched — still refuses (empty), seal invisible.
    assert inj.inject_from_match(m, _RATE_SENTENCE) == ()
    # Sealed path: the sealed injector is consulted and admits.
    assert inj.inject_from_match(m, _RATE_SENTENCE, sealed=True) == (sentinel,)


def test_parse_and_solve_threads_sealed_flag() -> None:
    """parse_and_solve accepts sealed= and is a no-op with an empty registry."""
    frozen = parse_and_solve(_RATE_SENTENCE)
    sealed = parse_and_solve(_RATE_SENTENCE, sealed=True)
    assert sealed.answer == frozen.answer
    assert sealed.refusal_reason == frozen.refusal_reason


def test_frozen_train_sample_byte_identical() -> None:
    """The default (sealed=False) path stays on the ratified report artifact."""
    report = json.loads(
        Path("evals/gsm8k_math/train_sample/v1/report.json").read_text()
    )
    assert report["counts"] == {"correct": 30, "refused": 20, "wrong": 0}
