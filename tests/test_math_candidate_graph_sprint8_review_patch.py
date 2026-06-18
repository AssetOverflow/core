"""Review-hardening tests for Sprint 8 A2k/A2l gates."""

from __future__ import annotations

from generate.derivation.fraction_decrease import resolve_promotable_fraction_decrease
from generate.derivation.percent_partition import resolve_promotable_percent_partition
from generate.math_candidate_graph import parse_and_solve


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def test_fraction_decrease_refuses_spaced_extra_fraction_hazard():
    text = (
        "In one hour, Addison mountain's temperature will decrease to 3/4 of its "
        "temperature. Last week it decreased to 1 / 2 of its temperature. If the "
        "current temperature of the mountain is 84 degrees, what will the temperature "
        "decrease by?"
    )
    assert resolve_promotable_fraction_decrease(text) is None
    assert _run(text).answer is None


def test_fraction_decrease_does_not_use_forecast_duration_as_base():
    text = (
        "In one hour, Addison mountain's temperature will decrease to 3/4 of its "
        "temperature. What will the temperature decrease by?"
    )
    assert resolve_promotable_fraction_decrease(text) is None
    assert _run(text).answer is None


def test_percent_partition_refuses_spaced_fraction_surface():
    text = (
        "A school has 100 students. Half of the students are girls, the other half are boys. "
        "20% of the girls have dogs, 10% of the boys have dogs, and 1 / 2 of the dogs are black. "
        "How many students own dogs?"
    )
    assert resolve_promotable_percent_partition(text) is None
    assert _run(text).answer is None


def test_percent_partition_does_not_use_subgroup_quantity_as_total():
    text = (
        "Half of the students are girls, the other half are boys. The girls group has 50 students. "
        "20% of the girls have dogs and 10% of the boys have dogs. How many students own dogs?"
    )
    assert resolve_promotable_percent_partition(text) is None
    assert _run(text).answer is None
