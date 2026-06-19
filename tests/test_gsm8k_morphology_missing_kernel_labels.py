"""Tests for scripts/gsm8k_substrate_morphology.py."""
from __future__ import annotations

import pytest

from scripts.gsm8k_substrate_morphology import classify_missing_substrate


def test_classify_missing_substrate_labels() -> None:
    # 1. missing_scalar_equivalence
    labels = classify_missing_substrate("The remaining amount is .5 of the total.")
    assert "missing_scalar_equivalence" in labels

    labels = classify_missing_substrate("He divided the cake into 1 / 2 parts.")
    assert "missing_scalar_equivalence" in labels

    # 2. missing_unit_dimension
    labels = classify_missing_substrate("John has 5 widgets.")
    assert "missing_unit_dimension" in labels

    labels = classify_missing_substrate("There are 10 bloops in the box.")
    assert "missing_unit_dimension" in labels
    assert "missing_container_frame" in labels  # "box" trigger

    # 3. missing_process_frame
    labels = classify_missing_substrate("John decides to give away his cards.")
    assert "missing_process_frame" in labels

    # 4. missing_part_whole_frame
    labels = classify_missing_substrate("Mary wants to split the money.")
    assert "missing_part_whole_frame" in labels

    # 5. missing_container_frame
    labels = classify_missing_substrate("Pack 10 apples into a bag.")
    assert "missing_container_frame" in labels

    # 6. missing_temporal_frame
    labels = classify_missing_substrate("John worked for 5 hours to earn money.")
    assert "missing_temporal_frame" in labels

    # 7. missing_route_frame
    labels = classify_missing_substrate("They will drive a distance of 50 miles.")
    assert "missing_route_frame" in labels

    # 8. missing_question_target
    labels = classify_missing_substrate("Calculate the total amount.")
    assert "missing_question_target" in labels

    # 9. blocked_ambiguity_hazard
    labels = classify_missing_substrate("He ate half of the pizza.")
    assert "blocked_ambiguity_hazard" in labels

    # 10. blocked_provenance_gap
    labels = classify_missing_substrate("Determine the days in a leap year.")
    assert "blocked_provenance_gap" in labels


def test_deterministic_and_sorted() -> None:
    problem = "John decides to split 5 bloops into boxes during a leap year."
    labels1 = classify_missing_substrate(problem)
    labels2 = classify_missing_substrate(problem)

    assert labels1 == labels2
    assert list(labels1) == sorted(labels1)
    # Check that multiple labels are correctly triggered
    assert "missing_unit_dimension" in labels1      # "bloops"
    assert "missing_part_whole_frame" in labels1    # "split"
    assert "missing_container_frame" in labels1     # "boxes"
    assert "blocked_provenance_gap" in labels1      # "leap year"
