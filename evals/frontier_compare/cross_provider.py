"""Cross-provider benchmark suite for frontier_compare.

The existing suites (``determinism``, ``truth_lock``,
``axis_orthogonality``) pull CORE-only telemetry (``trace_hash``,
``versor_condition``, ``register_id``, ``anchor_lens_id``) — they
cannot run cross-provider as-is.

This module is the cross-provider lane:

  - Pure ``(prompt) -> str`` over any provider adapter.
  - No CORE-internal telemetry expected.
  - Per-case ``passed`` is loose by design — non-empty surface within
    the elapsed-ms budget — because we are not in a position to
    semantically judge GPT-4o vs Claude vs CORE here.  The point of
    the suite is **operator-visible, side-by-side surface evidence**
    across providers on a fixed prompt battery, not automatic
    quality scoring.

The prompt battery (``_PROMPT_BATTERY``) is the load-bearing data —
edit it to expand cross-provider coverage.  Each entry pairs a
``case_id`` (stable across runs, used by reviewers to diff results)
with the prompt itself.

Trust boundary
--------------
- Read-only.  Never writes packs, vault, or runtime state.
- Provider adapters are constructed via
  ``evals.frontier_compare.providers.build_adapter`` and made of a
  single ``(prompt) -> str`` callable each.
- Per-call exceptions are recorded as case failures, never propagated.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .model_registry import resolve_model_card
from .providers import ProviderConfig
from .runner import CaseResult, SuiteReport


# ---------------------------------------------------------------------------
# Prompt battery
# ---------------------------------------------------------------------------
# Stable case_ids so a future re-run on the same provider produces
# diffable JSON.  Prompts span definitional / causal / verification /
# comparison / procedural / unknown shapes — enough to surface obvious
# provider behavior differences without ballooning credit cost.

_PROMPT_BATTERY: tuple[tuple[str, str], ...] = (
    ("definition_truth", "What is truth?"),
    ("definition_knowledge", "What is knowledge?"),
    ("cause_understanding", "What causes understanding?"),
    ("verification_evidence", "Does evidence ground knowledge?"),
    ("comparison_knowledge_wisdom", "Compare knowledge and wisdom."),
    ("procedure_recall", "Walk me through recall."),
    ("unknown_term", "What is xylomorphic?"),
)


# ---------------------------------------------------------------------------
# Observation shape — provider-agnostic
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    """One ``(prompt, provider) -> surface`` observation.

    Cross-provider sibling of :class:`runner.RuntimeObservation`.
    Carries only fields any provider can supply; CORE-only telemetry
    deliberately omitted.
    """

    prompt: str
    surface: str
    provider: str
    model: str
    elapsed_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    error_type: str = ""
    error_message: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.error_type and bool(self.surface.strip())

    def as_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "surface": self.surface,
            "provider": self.provider,
            "model": self.model,
            "elapsed_ms": self.elapsed_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


# ---------------------------------------------------------------------------
# Suite runner
# ---------------------------------------------------------------------------


def _observe_one(
    adapter: Callable[[str], object],
    cfg: ProviderConfig,
    prompt: str,
) -> ProviderObservation:
    card = resolve_model_card(cfg.provider, cfg.model)
    start = time.perf_counter()
    try:
        raw = adapter(prompt)
    except Exception as exc:  # noqa: BLE001 - record failure, never abort the suite
        return ProviderObservation(
            prompt=prompt,
            surface="",
            provider=cfg.provider,
            model=cfg.model,
            elapsed_ms=(time.perf_counter() - start) * 1000.0,
            error_type=exc.__class__.__name__,
            error_message=str(exc),
        )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    surface = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    if isinstance(raw, str):
        surface = raw
    else:
        surface = str(getattr(raw, "surface", "") or "")
        in_val = getattr(raw, "input_tokens", None)
        out_val = getattr(raw, "output_tokens", None)
        total_val = getattr(raw, "total_tokens", None)
        input_tokens = int(in_val) if in_val is not None else None
        output_tokens = int(out_val) if out_val is not None else None
        total_tokens = int(total_val) if total_val is not None else None
    estimated_cost_usd: float | None = None
    if (
        card is not None
        and input_tokens is not None
        and output_tokens is not None
    ):
        estimated_cost_usd = card.estimate_cost_usd(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    return ProviderObservation(
        prompt=prompt,
        surface=surface,
        provider=cfg.provider,
        model=cfg.model,
        elapsed_ms=elapsed_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )


def run_prompt_battery(
    adapter: Callable[[str], object],
    *,
    cfg: ProviderConfig,
    prompts: tuple[tuple[str, str], ...] = _PROMPT_BATTERY,
) -> SuiteReport:
    """Run the cross-provider prompt battery against one adapter.

    Per-case ``passed`` is loose by design (non-empty surface, no
    exception).  Reviewers should diff ``details.observation.surface``
    side-by-side rather than rely on the boolean.
    """
    cases: list[CaseResult] = []
    for case_id, prompt in prompts:
        obs = _observe_one(adapter, cfg, prompt)
        passed = obs.succeeded
        score = 1.0 if passed else 0.0
        failures: tuple[str, ...] = ()
        if not passed:
            failures = (
                ("adapter_error",) if obs.error_type else ("empty_surface",)
            )
        cases.append(
            CaseResult(
                suite="prompt_battery",
                case_id=case_id,
                prompt=prompt,
                passed=passed,
                score=score,
                elapsed_ms=obs.elapsed_ms,
                details={"observation": obs.as_dict()},
                failures=failures,
            )
        )
    primary = (
        sum(c.score for c in cases) / len(cases) if cases else 0.0
    )
    return SuiteReport(
        suite="prompt_battery",
        cases=tuple(cases),
        primary_score=primary,
        passed=all(c.passed for c in cases),
    )


def run_replay_variability(
    adapter: Callable[[str], object],
    *,
    cfg: ProviderConfig,
    repeats: int = 3,
    prompts: tuple[tuple[str, str], ...] = _PROMPT_BATTERY,
) -> SuiteReport:
    """Run repeated calls per prompt and score surface stability.

    Score formula per case:
        stability_score = 1 / unique_surface_count
    where unique_surface_count >= 1 over `repeats` runs.
    """
    runs = max(1, int(repeats))
    cases: list[CaseResult] = []
    for case_id, prompt in prompts:
        observations = [_observe_one(adapter, cfg, prompt) for _ in range(runs)]
        successful = [o for o in observations if not o.error_type]
        failures: list[str] = []
        if not successful:
            failures.append("adapter_error")
            unique_count = 0
            score = 0.0
            elapsed_ms = sum(o.elapsed_ms for o in observations)
            details = {
                "repeats": runs,
                "observations": [o.as_dict() for o in observations],
            }
        else:
            surfaces = {
                o.surface.strip()
                for o in successful
                if o.surface.strip()
            }
            if not surfaces:
                failures.append("empty_surface")
            unique_count = len(surfaces) if surfaces else 0
            score = 0.0 if unique_count == 0 else (1.0 / float(unique_count))
            if any(o.error_type for o in observations):
                failures.append("partial_adapter_error")
            elapsed_ms = sum(o.elapsed_ms for o in observations)
            costs = [
                float(o.estimated_cost_usd)
                for o in successful
                if o.estimated_cost_usd is not None
            ]
            details = {
                "repeats": runs,
                "successful_runs": len(successful),
                "unique_surface_count": unique_count,
                "mean_elapsed_ms": (elapsed_ms / runs) if runs else 0.0,
                "mean_estimated_cost_usd": (
                    (sum(costs) / len(costs))
                    if costs else None
                ),
                "observations": [o.as_dict() for o in observations],
            }
        passed = not failures and unique_count == 1
        cases.append(
            CaseResult(
                suite="replay_variability",
                case_id=case_id,
                prompt=prompt,
                passed=passed,
                score=score,
                elapsed_ms=elapsed_ms,
                details=details,
                failures=tuple(failures),
            )
        )
    primary = (
        sum(c.score for c in cases) / len(cases) if cases else 0.0
    )
    return SuiteReport(
        suite="replay_variability",
        cases=tuple(cases),
        primary_score=primary,
        passed=all(c.passed for c in cases),
    )


__all__ = [
    "ProviderObservation",
    "run_prompt_battery",
    "run_replay_variability",
]
