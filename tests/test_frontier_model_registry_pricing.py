from __future__ import annotations

from evals.frontier_compare.cross_provider import run_prompt_battery
from evals.frontier_compare.model_registry import require_model_card
from evals.frontier_compare.providers import AdapterResponse, ProviderConfig


def test_model_card_estimate_cost_formula() -> None:
    card = require_model_card("openai", "gpt-4o-2024-08-06")
    cost = card.estimate_cost_usd(input_tokens=2000, output_tokens=1000)
    assert cost is not None
    # (2000 / 1e6 * 2.5) + (1000 / 1e6 * 10.0) = 0.015
    assert round(cost, 6) == 0.015


def test_prompt_battery_records_usage_and_cost_when_available() -> None:
    cfg = ProviderConfig(provider="openai", model="gpt-4o-2024-08-06")

    def fake_adapter(_: str) -> AdapterResponse:
        return AdapterResponse(
            surface="ok",
            input_tokens=120,
            output_tokens=80,
            total_tokens=200,
        )

    report = run_prompt_battery(
        fake_adapter,
        cfg=cfg,
        prompts=(("case", "What is truth?"),),
    )
    obs = report.cases[0].details["observation"]
    assert obs["input_tokens"] == 120
    assert obs["output_tokens"] == 80
    assert obs["total_tokens"] == 200
    assert obs["estimated_cost_usd"] is not None
    assert obs["estimated_cost_usd"] > 0
