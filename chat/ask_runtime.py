from __future__ import annotations

from typing import Any, Callable

from core.epistemic_disclosure.ask_acquisition import acquire_served_ask_candidate

Provider = Callable[[], Any | None]


def maybe_apply_served_ask(
    config: Any,
    fallback_surface: str,
    *,
    contemplation_result: Any | None = None,
    provider: Provider | None = None,
) -> str:
    acquisition