"""Serving-safe acquisition seam for Stage 2 ASK candidates.

This module owns only the narrow boundary between a serving caller and the
already-shipped ASK artifact adapter:

1. honor the default-dark ``ask_serving_enabled`` gate before any provider call;
2. acquire, or accept, a candidate contemplation result;
3. delegate all artifact validation and served-surface decisioning to
   :func:`core.epistemic_disclosure.ask_serving.evaluate_served_ask`.

It does not render question prose, does not import the Q1-C renderer, does not
call ``generate.contemplation.pass_manager`` directly, and does not mutate
runtime/telemetry schemas. A future runtime slice can supply the provider once
the legal turn-boundary is explicit.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.epistemic_disclosure.ask_serving import ServedAskDecision, evaluate_served_ask
from core.epistemic_disclosure.disposition import ServedDisposition
from core.epistemic_questions.serving_gate import ask_serving_enabled

ContemplationProvider = Callable[[], Any | None]


@dataclass(frozen=True, slots=True)
class AskAcquisitionDecision:
    """Result of the serving-safe ASK acquisition seam."""

    acquired: bool
    provider_called: bool
    decision: ServedAskDecision


_NO_PROGRESS_FALLBACK = ServedAskDecision(
    served=False,
    terminal="NO_PROGRESS",
    surface="",
    disposition=ServedDisposition.REFUSE,
)


def _fallback(surface: str) -> ServedAskDecision:
    return ServedAskDecision(
        served=False,
        terminal=_NO_PROGRESS_FALLBACK.terminal,
        surface=surface,
        disposition=_NO_PROGRESS_FALLBACK.disposition,
    )


def acquire_served_ask_candidate(
    config: Any,
    *,
    fallback_surface: str,
    contemplation_result: Any | None = None,
    provider: ContemplationProvider | None = None,
) -> AskAcquisitionDecision:
    """Acquire and evaluate a candidate served-ASK artifact.

    The provider is never called while ``ask_serving_enabled`` is false. That
    gate-first rule keeps this seam side-effect free under default runtime
    configuration and prevents accidental contemplation work from changing
    normal serving behavior.

    If a caller already has a ``ContemplationResult``, pass it via
    ``contemplation_result``. Otherwise, pass a provider that can return one.
    The result is delegated to ``evaluate_served_ask``; this seam duplicates no
    Q1-D artifact validation and constructs no user-facing question text.
    """

    if not ask_serving_enabled(config):
        # Preserve any already-known terminal/disposition without causing a
        # provider side effect. ``evaluate_served_ask`` itself is gate-aware and
        # will fail closed without reading artifacts when the gate is disabled.
        if contemplation_result is not None:
            decision = evaluate_served_ask(config, contemplation_result, fallback_surface)
        else:
            decision = _fallback(fallback_surface)
        return AskAcquisitionDecision(
            acquired=contemplation_result is not None,
            provider_called=False,
            decision=decision,
        )

    provider_called = False
    candidate = contemplation_result
    if candidate is None and provider is not None:
        provider_called = True
        try:
            candidate = provider()
        except Exception:
            return AskAcquisitionDecision(
                acquired=False,
                provider_called=True,
                decision=_fallback(fallback_surface),
            )

    if candidate is None:
        return AskAcquisitionDecision(
            acquired=False,
            provider_called=provider_called,
            decision=_fallback(fallback_surface),
        )

    return AskAcquisitionDecision(
        acquired=True,
        provider_called=provider_called,
        decision=evaluate_served_ask(config, candidate, fallback_surface),
    )


__all__ = [
    "AskAcquisitionDecision",
    "ContemplationProvider",
    "acquire_served_ask_candidate",
]
