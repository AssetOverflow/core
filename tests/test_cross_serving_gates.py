"""Cross-gate configuration field tests.

Verifies that RuntimeConfig has both ask_serving_enabled and
verified_serving_enabled, that both are default false, and that setting
one does not implicitly enable the other.
"""

from __future__ import annotations

import dataclasses

from core.config import RuntimeConfig


def test_cross_serving_gates_independence() -> None:
    # 1. Verify both are present on a fresh config and default to False
    config = RuntimeConfig()
    assert hasattr(config, "ask_serving_enabled")
    assert hasattr(config, "verified_serving_enabled")
    assert config.ask_serving_enabled is False
    assert config.verified_serving_enabled is False

    # 2. Verify setting ask_serving_enabled to True does not enable verified_serving_enabled
    config_ask = dataclasses.replace(config, ask_serving_enabled=True)
    assert config_ask.ask_serving_enabled is True
    assert config_ask.verified_serving_enabled is False

    # 3. Verify setting verified_serving_enabled to True does not enable ask_serving_enabled
    config_verified = dataclasses.replace(config, verified_serving_enabled=True)
    assert config_verified.ask_serving_enabled is False
    assert config_verified.verified_serving_enabled is True
