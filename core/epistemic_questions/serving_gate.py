"""ASK serving gate helper — default-dark, no served-surface wiring.

This module is the first code slice after the ASK serving-integration scoping brief.
It intentionally does **not** call ``deliver_ask``/``emit_question``, does not import
``chat.runtime``, and does not expose any user-facing surface. It only centralizes the
kill-switch read so future serving code has one audited predicate.

The planned config field is ``RuntimeConfig.ask_serving_enabled``. During this dark-gate
slice the predicate is conservative: absent field == ``False``. That lets the helper land
without widening behavior and preserves the current default for every existing
``RuntimeConfig`` instance.
"""

from __future__ import annotations

from typing import Any

from core.config import DEFAULT_CONFIG, RuntimeConfig


def ask_serving_enabled(config: RuntimeConfig | Any | None = None) -> bool:
    """Return whether served ASK delivery is explicitly enabled.

    Missing attribute means ``False``. That is the load-bearing dark-gate invariant:
    the served ASK path cannot light merely because the helper exists or because an
    older ``RuntimeConfig`` instance lacks the future field.
    """
    cfg = DEFAULT_CONFIG if config is None else config
    return bool(getattr(cfg, "ask_serving_enabled", False))


__all__ = ["ask_serving_enabled"]
