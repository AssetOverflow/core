"""SafetyCheck — structural surface for safety-pack boundary checks.

Parallel in *shape* to :class:`core.physics.identity.IdentityCheck`, but
different in kind: identity boundaries are geometric (projection onto
value axes), while safety boundaries are propositional (each is a
predicate over runtime evidence).  Mechanically therefore SafetyCheck
is a registry of named predicates, one per boundary id, rather than a
manifold projector.

Per ADR-0032:

* SafetyCheck is **observational**.  It produces a :class:`SafetyVerdict`
  per turn; it does NOT refuse.  Wiring violations into refusal paths
  is a future ADR.
* Predicates report ``runtime_checkable=False`` honestly when a boundary
  is a code-path constraint that cannot be evaluated from runtime
  evidence (the canonical example is ``no_hot_path_repair``, whose
  enforcement lives in static analysis and code review).
* Unknown boundaries — packs that declare boundary ids for which no
  predicate is registered — default to ``upheld=True,
  runtime_checkable=False`` so a downstream deployment that adds a
  novel boundary doesn't crash the runtime.

See ``docs/decisions/ADR-0032-safety-check-surface.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from packs.safety.loader import SafetyPack


# ---------- value types ----------


@dataclass(frozen=True, slots=True)
class SafetyContext:
    """Inputs available to safety predicates per turn.

    Every field is optional / has a safe default.  Callers populate
    whatever they have; predicates over fields the caller didn't
    populate default to ``upheld=True`` (no evidence of violation).
    The interpretation is deliberate: SafetyCheck is observational,
    so absence of evidence is not evidence of violation.
    """

    # For ``preserve_versor_closure``.  Any object with a
    # ``versor_condition`` attribute / property qualifies.
    field_state: object | None = None
    versor_halt_threshold: float = 1.0e-6

    # For ``no_fabricated_source``.  Set of SHA-256 hashes the
    # trajectory cited as sources.
    cited_source_shas: frozenset[str] = frozenset()
    # Set of SHA-256 hashes the trust allowlist recognizes.  An empty
    # ``allowed_source_shas`` is treated as "allowlist not in use" —
    # the predicate reports ``runtime_checkable=False`` rather than
    # flagging every citation as fabricated.
    allowed_source_shas: frozenset[str] = frozenset()

    # For ``no_silent_correction``.  ``True`` when the most recent
    # refusal / exhaustion event was raised as a typed exception
    # (e.g. ``InnerLoopExhaustion``).  Default ``True`` means no
    # silent correction observed (absence of evidence of silent
    # correction).
    last_refusal_was_typed: bool = True

    # For ``no_identity_override``.  Hashes of the identity manifold
    # captured at the start and end of the turn.  Empty strings mean
    # the caller did not supply the hashes; predicate reports
    # ``runtime_checkable=False`` in that case.
    identity_manifold_hash_before: str = ""
    identity_manifold_hash_after: str = ""


@dataclass(frozen=True, slots=True)
class SafetyCheckResult:
    """Outcome of one boundary's predicate evaluation."""

    boundary_id: str
    upheld: bool
    reason: str
    runtime_checkable: bool
    evidence: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class SafetyVerdict:
    """Aggregate verdict over every boundary in the pack."""

    pack_id: str
    results: tuple[SafetyCheckResult, ...]
    upheld: bool
    violated_boundaries: frozenset[str]
    runtime_checkable_count: int


# ---------- predicate signature ----------


SafetyPredicate = Callable[[SafetyContext], SafetyCheckResult]


# ---------- the check ----------


class SafetyCheck:
    """Structural safety surface.  Observational; never refuses.

    Canonical call style::

        verdict = SafetyCheck().check(ctx, safety_pack)
    """

    def __init__(
        self,
        predicates: Mapping[str, SafetyPredicate] | None = None,
    ) -> None:
        if predicates is None:
            self._predicates: dict[str, SafetyPredicate] = dict(_DEFAULT_PREDICATES)
        else:
            self._predicates = dict(predicates)

    def register(self, boundary_id: str, predicate: SafetyPredicate) -> None:
        """Register / replace a predicate for ``boundary_id``."""
        self._predicates[boundary_id] = predicate

    def check(
        self,
        ctx: SafetyContext,
        safety_pack: SafetyPack,
    ) -> SafetyVerdict:
        """Run every predicate.  Returns an aggregate verdict.

        Boundaries are evaluated in lex order on ``boundary_id`` so
        ``results`` is deterministic regardless of how the pack
        enumerates ``boundary_ids``.
        """
        results: list[SafetyCheckResult] = []
        runtime_checkable_count = 0
        violated: set[str] = set()
        for boundary in sorted(safety_pack.boundary_ids):
            predicate = self._predicates.get(boundary)
            if predicate is None:
                result = SafetyCheckResult(
                    boundary_id=boundary,
                    upheld=True,
                    reason="no predicate registered for boundary",
                    runtime_checkable=False,
                )
            else:
                result = predicate(ctx)
                if result.boundary_id != boundary:
                    # Defensive: a registered predicate must declare
                    # the same boundary id it was registered under.
                    result = SafetyCheckResult(
                        boundary_id=boundary,
                        upheld=result.upheld,
                        reason=result.reason,
                        runtime_checkable=result.runtime_checkable,
                        evidence=result.evidence,
                    )
            results.append(result)
            if result.runtime_checkable:
                runtime_checkable_count += 1
            if not result.upheld:
                violated.add(boundary)
        return SafetyVerdict(
            pack_id=safety_pack.pack_id,
            results=tuple(results),
            upheld=not violated,
            violated_boundaries=frozenset(violated),
            runtime_checkable_count=runtime_checkable_count,
        )


# ---------- default predicates for v1 boundaries ----------


def _predicate_versor_closure(ctx: SafetyContext) -> SafetyCheckResult:
    """``preserve_versor_closure`` — field's versor_condition under threshold."""
    fs = ctx.field_state
    if fs is None:
        return SafetyCheckResult(
            boundary_id="preserve_versor_closure",
            upheld=True,
            reason="no field_state supplied",
            runtime_checkable=False,
        )
    vc = getattr(fs, "versor_condition", None)
    if vc is None:
        return SafetyCheckResult(
            boundary_id="preserve_versor_closure",
            upheld=True,
            reason="field_state has no versor_condition attribute",
            runtime_checkable=False,
        )
    vc_value = float(vc)
    upheld = vc_value < ctx.versor_halt_threshold
    return SafetyCheckResult(
        boundary_id="preserve_versor_closure",
        upheld=upheld,
        reason=(
            f"versor_condition={vc_value:.3e} "
            f"{'<' if upheld else '>='} threshold={ctx.versor_halt_threshold:.0e}"
        ),
        runtime_checkable=True,
        evidence=(("versor_condition", f"{vc_value:.6e}"),),
    )


def _predicate_no_fabricated_source(ctx: SafetyContext) -> SafetyCheckResult:
    """``no_fabricated_source`` — every cited SHA is in the allowlist."""
    if not ctx.allowed_source_shas:
        return SafetyCheckResult(
            boundary_id="no_fabricated_source",
            upheld=True,
            reason="allowed_source_shas is empty (allowlist not in use)",
            runtime_checkable=False,
        )
    if not ctx.cited_source_shas:
        return SafetyCheckResult(
            boundary_id="no_fabricated_source",
            upheld=True,
            reason="no citations to check",
            runtime_checkable=True,
        )
    fabricated = ctx.cited_source_shas - ctx.allowed_source_shas
    if fabricated:
        return SafetyCheckResult(
            boundary_id="no_fabricated_source",
            upheld=False,
            reason=(
                f"{len(fabricated)} citation(s) not in allowlist: "
                f"{sorted(s[:12] + '...' for s in fabricated)}"
            ),
            runtime_checkable=True,
            evidence=tuple(
                (f"fabricated_{i}", sha)
                for i, sha in enumerate(sorted(fabricated))
            ),
        )
    return SafetyCheckResult(
        boundary_id="no_fabricated_source",
        upheld=True,
        reason=f"all {len(ctx.cited_source_shas)} citation(s) in allowlist",
        runtime_checkable=True,
    )


def _predicate_no_silent_correction(ctx: SafetyContext) -> SafetyCheckResult:
    """``no_silent_correction`` — refusals raised as typed exceptions."""
    upheld = bool(ctx.last_refusal_was_typed)
    return SafetyCheckResult(
        boundary_id="no_silent_correction",
        upheld=upheld,
        reason=(
            "last refusal was typed"
            if upheld
            else "last refusal was swallowed (no typed exception observed)"
        ),
        runtime_checkable=True,
    )


def _predicate_no_identity_override(ctx: SafetyContext) -> SafetyCheckResult:
    """``no_identity_override`` — identity manifold unchanged across the turn."""
    before = ctx.identity_manifold_hash_before
    after = ctx.identity_manifold_hash_after
    if not before or not after:
        return SafetyCheckResult(
            boundary_id="no_identity_override",
            upheld=True,
            reason="identity manifold hashes not supplied",
            runtime_checkable=False,
        )
    upheld = before == after
    return SafetyCheckResult(
        boundary_id="no_identity_override",
        upheld=upheld,
        reason=(
            "identity manifold unchanged"
            if upheld
            else f"identity manifold mutated: {before[:12]}... -> {after[:12]}..."
        ),
        runtime_checkable=True,
        evidence=(
            ("identity_hash_before", before[:24] + "..."),
            ("identity_hash_after", after[:24] + "..."),
        ),
    )


def _predicate_no_hot_path_repair(ctx: SafetyContext) -> SafetyCheckResult:
    """``no_hot_path_repair`` — code-path boundary, not runtime-checkable.

    This boundary forbids normalization / drift-repair operators in
    ``field/propagate.py``, ``generate/stream.py``, ``vault/store.py``.
    Enforcement is static — by tests and by code review.  Reporting it
    as ``runtime_checkable=False`` is the honest answer.  A reviewer
    looking at a SafetyVerdict can verify the surface acknowledged the
    boundary's nature rather than silently passing it.
    """
    return SafetyCheckResult(
        boundary_id="no_hot_path_repair",
        upheld=True,
        reason=(
            "code-path boundary; enforced by static analysis + code review, "
            "not by runtime check"
        ),
        runtime_checkable=False,
    )


_DEFAULT_PREDICATES: dict[str, SafetyPredicate] = {
    "no_fabricated_source": _predicate_no_fabricated_source,
    "no_hot_path_repair": _predicate_no_hot_path_repair,
    "no_identity_override": _predicate_no_identity_override,
    "no_silent_correction": _predicate_no_silent_correction,
    "preserve_versor_closure": _predicate_versor_closure,
}


__all__ = [
    "SafetyCheck",
    "SafetyCheckResult",
    "SafetyContext",
    "SafetyPredicate",
    "SafetyVerdict",
]
