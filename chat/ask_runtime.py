"""Runtime-facing ASK helper.

This tiny module is separate from chat.runtime so connector edits do not
rewrite the large runtime file. It is the serving-side consumer of the
ASK acquisition seam, but it does not call pass_manager, render question
prose, or change runtime schemas.
"""

from __future__ import annotations

from typing import Any

from core.epistemic_disclosure.ask_acquisition import acquire_served_ask_candidate


def maybe_apply_served_ask(
    config: Any,
    fallback_surface: str,
    *,
    contemplation_result: Any | None = None,
    provider: Any | None = None,
) -> str:
    """Return a valid served ASK surface, or the original fallback surface."""

    acquisition = acquire_served_ask_candidate(
        config,
        fallback_surface=fallback_surface,
        contemplation_result=contemplation_result,
        provider=provider,
    )
    if acquisition.decision.served:
        return acquisition.decision.surface
    return fallback_surface


__all__ = ["maybe_apply_served_ask"]
