"""ASK serving gate — default-dark invariant.

This is deliberately narrower than serving integration. It proves the post-scoping
kill-switch predicate is dark unless an operator/config object explicitly opts in.
No chat/runtime wiring, no pass-manager emission, no carve-out retirement.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config import DEFAULT_CONFIG, RuntimeConfig
from core.epistemic_questions.serving_gate import ask_serving_enabled


@dataclass(frozen=True, slots=True)
class _LegacyConfig:
    """A pre-field config shape: absence of the flag must mean dark."""

    unrelated: bool = True


@dataclass(frozen=True, slots=True)
class _OptInConfig:
    ask_serving_enabled: bool


def test_default_runtime_config_keeps_ask_serving_dark() -> None:
    assert hasattr(RuntimeConfig(), "ask_serving_enabled")
    assert RuntimeConfig().ask_serving_enabled is False
    assert DEFAULT_CONFIG.ask_serving_enabled is False
    assert ask_serving_enabled(DEFAULT_CONFIG) is False
    assert ask_serving_enabled(RuntimeConfig()) is False



def test_missing_flag_is_dark_for_legacy_config_shape() -> None:
    assert ask_serving_enabled(_LegacyConfig()) is False


def test_gate_only_lights_on_explicit_truthy_opt_in() -> None:
    assert ask_serving_enabled(_OptInConfig(False)) is False
    assert ask_serving_enabled(_OptInConfig(True)) is True


def test_none_uses_default_config_and_stays_dark() -> None:
    assert ask_serving_enabled() is False
