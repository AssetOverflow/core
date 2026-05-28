"""WAVE-A — multiplicative_aggregation injector with value extraction.

Verifies the matcher extension + injector that turns
``<Subject> <verb> <M> <outer-noun>, each <weigh-verb>ing <N> <unit>``
shape into a pre-composed ``CandidateInitial(value=M*N, unit=unit,
entity=Subject)`` admission. Closes the largest gap from the post-RAT-1
audit (5 of 47 train_sample refusals were ``recognizer_empty_injection
(multiplicative_aggregation)``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from generate.comprehension.composition_registry import (
    clear_cache as clear_composition_cache,
)
from generate.recognizer_registry import clear_registry_cache
from generate.math_candidate_parser import CandidateInitial


_SPEC: Mapping[str, Any] = {
    "anchor_kind": "multiplicative_aggregate",
    "extract_values": True,
    "observed_units": [
        "ounces", "ounce", "strawberries", "strawberry",
        "questions", "question", "apples", "apple",
    ],
}


def setup_function(_):
    clear_composition_cache()
    clear_registry_cache()


def test_each_weighing_shape_admits():
    """John bakes 12 coconut macaroons, each weighing 5 ounces → 60 ounces."""
    from generate.recognizer_match import _match_multiplicative_aggregation

    s = "John bakes 12 coconut macaroons, each weighing 5 ounces."
    r = _match_multiplicative_aggregation(s, _SPEC)
    assert r is not None
    a = r[0][0]
    ci = a["composed_initial"]
    assert isinstance(ci, CandidateInitial)
    assert ci.initial.entity == "John"
    assert ci.initial.quantity.value == 60
    assert ci.initial.quantity.unit == "ounces"


def test_each_basket_holds_shape_admits():
    """Lilibeth fills 6 baskets where each basket holds 50 strawberries → 300."""
    from generate.recognizer_match import _match_multiplicative_aggregation

    s = "Lilibeth fills 6 baskets where each basket holds 50 strawberries."
    r = _match_multiplicative_aggregation(s, _SPEC)
    assert r is not None
    a = r[0][0]
    ci = a["composed_initial"]
    assert ci.initial.entity == "Lilibeth"
    assert ci.initial.quantity.value == 300


def test_detection_only_path_preserved_when_extract_values_absent():
    """Specs WITHOUT extract_values=True get the existing detection-only path."""
    from generate.recognizer_match import _match_multiplicative_aggregation

    spec = dict(_SPEC)
    spec.pop("extract_values")
    r = _match_multiplicative_aggregation(
        "John bakes 12 coconut macaroons, each weighing 5 ounces.", spec
    )
    # Falls through to existing detection-only return.
    assert r is not None
    anchors, intent = r
    assert intent == "aggregate"
    assert anchors == ()


def test_unobserved_unit_refuses():
    from generate.recognizer_match import _match_multiplicative_aggregation

    spec = dict(_SPEC)
    spec["observed_units"] = ["dollars"]
    r = _match_multiplicative_aggregation(
        "John bakes 12 coconut macaroons, each weighing 5 ounces.", spec
    )
    # Falls through to detection-only (no composed admit; unit not observed).
    assert r is not None
    assert r[0] == ()


def test_pronoun_subject_refuses():
    from generate.recognizer_match import _match_multiplicative_aggregation

    r = _match_multiplicative_aggregation(
        "He bakes 12 coconut macaroons, each weighing 5 ounces.", _SPEC
    )
    # Falls through to detection-only (composition path refuses on pronoun).
    assert r is not None
    assert r[0] == ()


def test_zero_count_refuses():
    from generate.recognizer_match import _match_multiplicative_aggregation

    r = _match_multiplicative_aggregation(
        "John bakes 0 coconut macaroons, each weighing 5 ounces.", _SPEC
    )
    assert r is not None
    assert r[0] == ()


def test_inject_from_match_picks_up_composed_initial():
    """The new per-category injector emits the composed CandidateInitial."""
    from evals.refusal_taxonomy.shape_categories import ShapeCategory
    from generate.recognizer_anchor_inject import inject_from_match
    from generate.recognizer_match import (
        RecognizerMatch,
        _match_multiplicative_aggregation,
    )

    s = "John bakes 12 coconut macaroons, each weighing 5 ounces."
    r = _match_multiplicative_aggregation(s, _SPEC)
    assert r is not None

    class _R:
        spec_id = "test_wave_a"

    m = RecognizerMatch(
        recognizer=_R(),  # type: ignore[arg-type]
        category=ShapeCategory.MULTIPLICATIVE_AGGREGATION,
        outcome="admissible",
        graph_intent="aggregate",
        parsed_anchors=r[0],
    )
    emit = inject_from_match(m, s)
    assert len(emit) == 1
    assert isinstance(emit[0], CandidateInitial)
    assert emit[0].initial.quantity.value == 60


def test_lilibeth_canary_solves_end_to_end():
    """The first WAVE-A end-to-end solve on the canonical pack."""
    if not _has_wave_a_seed():
        pytest.skip("WAVE-A recognizer seed not present on canonical pack")
    from generate.math_candidate_graph import parse_and_solve

    p = (
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "How many strawberries does Lilibeth have?"
    )
    r = parse_and_solve(p)
    assert r.refusal_reason is None, f"unexpected refusal: {r.refusal_reason!r}"
    assert r.answer == 300


def _has_wave_a_seed() -> bool:
    from generate.recognizer_registry import load_ratified_registry

    reg = load_ratified_registry()
    return any(
        r.canonical_pattern.get("anchor_kind") == "multiplicative_aggregate"
        and r.canonical_pattern.get("extract_values") is True
        for r in reg
    )


def test_wrong_zero_preserved():
    """The full train_sample eval keeps wrong == 0 after WAVE-A."""
    import subprocess
    import sys

    here = Path(__file__).resolve()
    while here.parent != here and not (here / "pyproject.toml").exists():
        here = here.parent
    subprocess.run(
        [sys.executable, "-m", "evals.gsm8k_math.train_sample.v1.runner"],
        cwd=here,
        capture_output=True,
    )
    report = json.loads(
        (here / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json").read_text()
    )
    assert report["counts"]["wrong"] == 0


def test_case_0050_remains_refused():
    """Hazard pin."""
    import subprocess
    import sys

    here = Path(__file__).resolve()
    while here.parent != here and not (here / "pyproject.toml").exists():
        here = here.parent
    subprocess.run(
        [sys.executable, "-m", "evals.gsm8k_math.train_sample.v1.runner"],
        cwd=here,
        capture_output=True,
    )
    report = json.loads(
        (here / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json").read_text()
    )
    case_0050 = next(
        (c for c in report["per_case"] if c["case_id"].endswith("-0050")),
        None,
    )
    assert case_0050 is not None
    assert case_0050["verdict"] == "refused"
