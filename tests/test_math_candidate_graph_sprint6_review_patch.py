"""Review-hardening tests for Sprint 6 A2g/A2h organs."""

from __future__ import annotations

from generate.derivation.duration_segment_total import (
    resolve_promotable_duration_segment_total,
)
from generate.derivation.survey_rate_earnings import compose_survey_rate_earnings
from generate.math_candidate_graph import parse_and_solve


def test_duration_segment_total_refuses_mixed_duration_units():
    text = (
        "Crossing the city, Maria rides the bus for 5 hours, then the ferry for "
        "twice as much time as the bus ride, then walks the remaining distance "
        "for 3 minutes. What's the total time for her journey?"
    )
    assert resolve_promotable_duration_segment_total(text) is None
    assert parse_and_solve(text).answer is None


def test_survey_rate_earnings_rejects_duplicate_unused_quantity():
    text = (
        "Lisa completes surveys for cash. She gets $0.10 per question. Every "
        "survey has 10 questions. On Wednesday she finished 2 surveys, and on "
        "Thursday 5 surveys. She also completed 10 training modules. How much "
        "money did she earn?"
    )
    assert compose_survey_rate_earnings(text) is None
    assert parse_and_solve(text).answer is None
