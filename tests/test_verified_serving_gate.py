"""VERIFIED serving gate — default-dark invariant.

This proves the post-scoping kill-switch predicate is dark unless an
operator/config object explicitly opts in.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config import DEFAULT_CONFIG, RuntimeConfig
from core.epistemic_disclosure.serving_gate import verified_serving_enabled


@dataclass(frozen=True, slots=True)
class _LegacyConfig:
    """A pre-field config shape: absence of the flag must mean dark."""

    unrelated: bool = True


@dataclass(frozen=True, slots=True)
class _OptInConfig:
    """Config with the verified_serving_enabled field."""

    verified_serving_enabled: bool | None


def test_default_runtime_config_keeps_verified_serving_dark() -> None:
    assert verified_serving_enabled(DEFAULT_CONFIG) is False
    assert verified_serving_enabled(RuntimeConfig()) is False


def test_missing_flag_is_dark_for_legacy_config_shape() -> None:
    assert verified_serving_enabled(_LegacyConfig()) is False


def test_gate_only_lights_on_explicit_truthy_opt_in() -> None:
    assert verified_serving_enabled(_OptInConfig(False)) is False
    assert verified_serving_enabled(_OptInConfig(True)) is True
    assert verified_serving_enabled(_OptInConfig(None)) is False


def test_none_uses_default_config_and_stays_dark() -> None:
    assert verified_serving_enabled() is False


def test_verified_serving_gate_has_no_eval_or_runtime_imports() -> None:
    path = Path(__file__).parent.parent / "core/epistemic_disclosure/serving_gate.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    forbidden = {
        "evals",
        "evals.constraint_oracle",
        "evals.constraint_oracle.verified_producer",
        "verify",
        "chat.runtime",
        "generate.contemplation.pass_manager",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                for banned in forbidden:
                    assert name.name != banned, f"Forbidden import: {name.name}"
                    assert not name.name.startswith(banned + "."), f"Forbidden import: {name.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for banned in forbidden:
                    assert node.module != banned, f"Forbidden import from: {node.module}"
                    assert not node.module.startswith(banned + "."), f"Forbidden import from: {node.module}"
