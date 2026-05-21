"""Explicit user-facing surface resolution for cognitive turns.

The pipeline produces several candidate surfaces in one turn:

* runtime/canonical surface from ChatRuntime
* semantic realizer surface from the proposition graph
* deterministic operator folds from walk / compose inference

Historically these mutated one string in evaluation order.  This module
centralizes the policy so fold behavior is declared and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SurfaceResolution:
    """Resolved user-facing and articulation surfaces.

    ``authority`` records the prefix authority before deterministic folds
    are appended.  ``fold_sources`` records which inference suffixes were
    appended, in deterministic order.
    """

    surface: str
    articulation_surface: str
    authority: str
    fold_sources: tuple[str, ...] = ()


def _base_runtime_surface(
    *,
    canonical_surface: str,
    pre_decoration_surface: str,
    response_surface: str,
    response_articulation_surface: str,
) -> tuple[str, str, str]:
    """Select the runtime-owned base surface by declared precedence."""

    if canonical_surface:
        return canonical_surface, response_articulation_surface, "runtime_canonical"
    if pre_decoration_surface:
        return pre_decoration_surface, response_articulation_surface, "runtime_pre_decoration"
    return response_surface, response_articulation_surface, "runtime"


def resolve_surface(
    *,
    canonical_surface: str = "",
    pre_decoration_surface: str = "",
    response_surface: str = "",
    response_articulation_surface: str = "",
    realized_surface: str = "",
    realizer_useful: bool = False,
    gate_fired: bool = False,
    walk_surface: str = "",
    compose_surface: str = "",
) -> SurfaceResolution:
    """Resolve the final turn surface under one explicit policy.

    Policy:
      1. Runtime/canonical/pre-decoration selects the base authority.
      2. A useful realizer surface may replace the prefix only when the
         unknown-domain gate did not fire.
      3. Walk and compose suffixes are deterministic inference folds.  They
         append after prefix authority is selected and are never allowed to
         re-run or reinterpret the prefix decision.
    """

    surface, articulation_surface, authority = _base_runtime_surface(
        canonical_surface=canonical_surface or "",
        pre_decoration_surface=pre_decoration_surface or "",
        response_surface=response_surface or "",
        response_articulation_surface=response_articulation_surface or "",
    )

    if realized_surface and realizer_useful and not gate_fired:
        surface = realized_surface
        articulation_surface = realized_surface
        authority = "realizer"

    fold_sources: list[str] = []
    if walk_surface:
        surface = f"{surface} — {walk_surface}" if surface else walk_surface
        articulation_surface = (
            f"{articulation_surface} — {walk_surface}"
            if articulation_surface
            else walk_surface
        )
        fold_sources.append("walk")

    if compose_surface:
        surface = f"{surface} — {compose_surface}" if surface else compose_surface
        articulation_surface = (
            f"{articulation_surface} — {compose_surface}"
            if articulation_surface
            else compose_surface
        )
        fold_sources.append("compose")

    return SurfaceResolution(
        surface=surface,
        articulation_surface=articulation_surface,
        authority=authority,
        fold_sources=tuple(fold_sources),
    )
