"""VERIFIED serving gate helper — default-dark, no served-surface wiring.

This module centralizes the future kill-switch predicate for VERIFIED serving.
It is default-dark / fail-closed: if the config field is missing or malformed,
it must evaluate to False.

This helper only centralizes the future kill-switch predicate so that future serving code
has one audited predicate. It does not wire any served-surface or implement served
VERIFIED behavior. Missing field means False.

Note that eval-gold-backed producers (such as the verification producer in
evals/constraint_oracle/verified_producer.py) are not serving-eligible.
"""

from __future__ import annotations

from typing import Any

from core.config import DEFAULT_CONFIG, RuntimeConfig


def verified_serving_enabled(config: RuntimeConfig | Any | None = None) -> bool:
    """Return whether served VERIFIED delivery is explicitly enabled.

    Missing attribute means False. This is the load-bearing dark-gate invariant:
    the served VERIFIED path cannot light merely because the helper exists or because
    an older RuntimeConfig instance lacks the future field.
    """
    cfg = DEFAULT_CONFIG if config is None else config
    return bool(getattr(cfg, "verified_serving_enabled", False))


__all__ = ["verified_serving_enabled"]
