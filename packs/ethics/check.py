"""EthicsCheck — structural surface for ethics-pack commitment checks.

Parallel in shape to :class:`packs.safety.check.SafetyCheck` (ADR-0032),
but evaluates *propositional commitments* rather than safety boundaries.
The two layers occupy distinct architectural niches:

* SafetyCheck evaluates universal red lines ("never X").  Violations
  are violations of the floor.
* EthicsCheck evaluates deployment commitments ("we commit to Y").
  Violations are failures of pledge, not floor violations.

Per ADR-0034:

* EthicsCheck is **observational** at v1.  It produces an
  :class:`EthicsVerdict` per turn; it does NOT refuse.  Wiring into
  refusal / re-articulation paths is a future ADR.
* Predicates report ``runtime_checkable=False`` honestly when a
  commitment cannot be evaluated from runtime evidence — the canonical
  example is ``no_manipulation``, an aggregate property enforced by
  realizer design and review, not a per-turn metric.
* Unknown commitments — packs that declare ids for which no predicate
  is registered — default to ``upheld=True, runtime_checkable=False``.
  Downstream domain deployments can register custom predicates without
  modifying CORE code.

See ``docs/decisions/ADR-0034-ethics-check-surface.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from packs.ethics.loader import EthicsPack


# ---------- value types ----------


@dataclass(frozen=True, slots=True)
class EthicsContext:
    """Inputs available to ethics predicates per turn.

    Every field is optional; defaults express "caller did not supply
    this evidence."  Predicates that depend on absent evidence return
    ``upheld=True, runtime_checkable=False`` — absence of evidence is
    not evidence of commitment violation.
    """

    # --- acknowledge_uncertainty ---
    # Manifold alignment score for this turn's reasoning trajectory
    # (typically the scalar ``IdentityScore.alignment``).  ``None``
    # means the caller did not supply it.
    alignment_score: float | None = None
    # Soft hedge threshold: below this, an unhedged claim is a
    # violation of ``acknowledge_uncertainty``.  Default mirrors the
    # ADR-0028 default ``hedge_threshold_soft``.
    hedge_threshold_soft: float = 0.65
    # Whether the realized surface emitted a hedge phrase.
    hedge_emitted: bool | None = None

    # --- defer_high_stakes_to_human_review ---
    # Whether the current topic falls in a high-stakes category as
    # classified by the caller (e.g. medical diagnosis, legal advice).
    high_stakes_topic: bool | None = None
    # Whether the response recommended human review for this turn.
    recommended_human_review: bool | None = None

    # --- disclose_limitations ---
    # Whether the response was grounded in retrievable evidence.
    grounded_in_evidence: bool | None = None
    # Whether the realized surface emitted a limitation-disclosure
    # marker (e.g. "I don't know — insufficient grounding").
    disclosure_emitted: bool | None = None

    # --- respect_user_autonomy ---
    # Whether the response prescribed a single answer rather than
    # surfacing options.  ``None`` means the caller did not classify
    # the response's prescriptiveness.
    prescribed_single_answer: bool | None = None
    # Count of distinct options / approaches surfaced.  When
    # ``prescribed_single_answer`` is True and this is < 2, the
    # commitment is violated.
    presented_options_count: int | None = None


@dataclass(frozen=True, slots=True)
class EthicsCheckResult:
    """Outcome of one commitment's predicate evaluation."""

    commitment_id: str
    upheld: bool
    reason: str
    runtime_checkable: bool
    evidence: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class EthicsVerdict:
    """Aggregate verdict over every commitment in the pack."""

    pack_id: str
    results: tuple[EthicsCheckResult, ...]
    upheld: bool
    violated_commitments: frozenset[str]
    runtime_checkable_count: int


# ---------- predicate signature ----------


EthicsPredicate = Callable[[EthicsContext], EthicsCheckResult]


# ---------- the check ----------


class EthicsCheck:
    """Structural ethics surface.  Observational; never refuses.

    Canonical call style::

        verdict = EthicsCheck().check(ctx, ethics_pack)
    """

    def __init__(
        self,
        predicates: Mapping[str, EthicsPredicate] | None = None,
    ) -> None:
        if predicates is None:
            self._predicates: dict[str, EthicsPredicate] = dict(_DEFAULT_PREDICATES)
        else:
            self._predicates = dict(predicates)

    def register(self, commitment_id: str, predicate: EthicsPredicate) -> None:
        """Register / replace a predicate for ``commitment_id``."""
        self._predicates[commitment_id] = predicate

    def check(
        self,
        ctx: EthicsContext,
        ethics_pack: EthicsPack,
    ) -> EthicsVerdict:
        """Run every predicate.  Returns an aggregate verdict.

        Commitments are evaluated in lex order on ``commitment_id`` so
        ``results`` is deterministic regardless of how the pack
        enumerates ``commitment_ids``.
        """
        results: list[EthicsCheckResult] = []
        runtime_checkable_count = 0
        violated: set[str] = set()
        for commitment in sorted(ethics_pack.commitment_ids):
            predicate = self._predicates.get(commitment)
            if predicate is None:
                result = EthicsCheckResult(
                    commitment_id=commitment,
                    upheld=True,
                    reason="no predicate registered for commitment",
                    runtime_checkable=False,
                )
            else:
                result = predicate(ctx)
                if result.commitment_id != commitment:
                    # Defensive: rebinding a misbehaving predicate's
                    # result keeps the audit trail correctly indexed.
                    result = EthicsCheckResult(
                        commitment_id=commitment,
                        upheld=result.upheld,
                        reason=result.reason,
                        runtime_checkable=result.runtime_checkable,
                        evidence=result.evidence,
                    )
            results.append(result)
            if result.runtime_checkable:
                runtime_checkable_count += 1
            if not result.upheld:
                violated.add(commitment)
        return EthicsVerdict(
            pack_id=ethics_pack.pack_id,
            results=tuple(results),
            upheld=not violated,
            violated_commitments=frozenset(violated),
            runtime_checkable_count=runtime_checkable_count,
        )


# ---------- default predicates for the five v1 commitments ----------


def _predicate_acknowledge_uncertainty(
    ctx: EthicsContext,
) -> EthicsCheckResult:
    """``acknowledge_uncertainty`` — low-alignment claims must be hedged."""
    if ctx.alignment_score is None or ctx.hedge_emitted is None:
        return EthicsCheckResult(
            commitment_id="acknowledge_uncertainty",
            upheld=True,
            reason="alignment_score or hedge_emitted not supplied",
            runtime_checkable=False,
        )
    below_threshold = ctx.alignment_score < ctx.hedge_threshold_soft
    if below_threshold and not ctx.hedge_emitted:
        return EthicsCheckResult(
            commitment_id="acknowledge_uncertainty",
            upheld=False,
            reason=(
                f"alignment_score={ctx.alignment_score:.3f} below "
                f"hedge_threshold_soft={ctx.hedge_threshold_soft:.3f} "
                "but no hedge emitted"
            ),
            runtime_checkable=True,
            evidence=(
                ("alignment_score", f"{ctx.alignment_score:.6f}"),
                ("hedge_threshold_soft", f"{ctx.hedge_threshold_soft:.6f}"),
                ("hedge_emitted", "False"),
            ),
        )
    return EthicsCheckResult(
        commitment_id="acknowledge_uncertainty",
        upheld=True,
        reason=(
            f"alignment={ctx.alignment_score:.3f}, "
            f"hedge_emitted={ctx.hedge_emitted}"
        ),
        runtime_checkable=True,
    )


def _predicate_defer_high_stakes(ctx: EthicsContext) -> EthicsCheckResult:
    """``defer_high_stakes_to_human_review`` — high-stakes turns recommend review."""
    if ctx.high_stakes_topic is None:
        return EthicsCheckResult(
            commitment_id="defer_high_stakes_to_human_review",
            upheld=True,
            reason="high_stakes_topic flag not supplied",
            runtime_checkable=False,
        )
    if not ctx.high_stakes_topic:
        return EthicsCheckResult(
            commitment_id="defer_high_stakes_to_human_review",
            upheld=True,
            reason="topic not classified as high-stakes; commitment dormant",
            runtime_checkable=True,
        )
    if ctx.recommended_human_review is None:
        return EthicsCheckResult(
            commitment_id="defer_high_stakes_to_human_review",
            upheld=True,
            reason=(
                "high_stakes_topic=True but recommended_human_review not "
                "supplied — cannot judge"
            ),
            runtime_checkable=False,
        )
    if ctx.recommended_human_review:
        return EthicsCheckResult(
            commitment_id="defer_high_stakes_to_human_review",
            upheld=True,
            reason="high-stakes topic; human review recommended",
            runtime_checkable=True,
        )
    return EthicsCheckResult(
        commitment_id="defer_high_stakes_to_human_review",
        upheld=False,
        reason=(
            "high-stakes topic but no human review recommended"
        ),
        runtime_checkable=True,
        evidence=(
            ("high_stakes_topic", "True"),
            ("recommended_human_review", "False"),
        ),
    )


def _predicate_disclose_limitations(ctx: EthicsContext) -> EthicsCheckResult:
    """``disclose_limitations`` — ungrounded turns must emit disclosure."""
    if ctx.grounded_in_evidence is None:
        return EthicsCheckResult(
            commitment_id="disclose_limitations",
            upheld=True,
            reason="grounded_in_evidence flag not supplied",
            runtime_checkable=False,
        )
    if ctx.grounded_in_evidence:
        return EthicsCheckResult(
            commitment_id="disclose_limitations",
            upheld=True,
            reason="response grounded; no disclosure obligation",
            runtime_checkable=True,
        )
    if ctx.disclosure_emitted is None:
        return EthicsCheckResult(
            commitment_id="disclose_limitations",
            upheld=True,
            reason=(
                "grounded_in_evidence=False but disclosure_emitted not "
                "supplied — cannot judge"
            ),
            runtime_checkable=False,
        )
    if ctx.disclosure_emitted:
        return EthicsCheckResult(
            commitment_id="disclose_limitations",
            upheld=True,
            reason="ungrounded response disclosed its limitation",
            runtime_checkable=True,
        )
    return EthicsCheckResult(
        commitment_id="disclose_limitations",
        upheld=False,
        reason="ungrounded response did not disclose its limitation",
        runtime_checkable=True,
        evidence=(
            ("grounded_in_evidence", "False"),
            ("disclosure_emitted", "False"),
        ),
    )


def _predicate_no_manipulation(ctx: EthicsContext) -> EthicsCheckResult:
    """``no_manipulation`` — structural commitment; not runtime-checkable.

    Absence of manipulation is an aggregate property of realizer
    design, template curation, and review — not a per-turn metric.
    A predicate that silently reported ``upheld=True`` would be
    misleading; the honest answer is ``runtime_checkable=False``,
    same shape as ``no_hot_path_repair`` in SafetyCheck (ADR-0032).
    """
    return EthicsCheckResult(
        commitment_id="no_manipulation",
        upheld=True,
        reason=(
            "aggregate commitment; enforced by realizer design, template "
            "curation, and review — not by per-turn runtime check"
        ),
        runtime_checkable=False,
    )


def _predicate_respect_user_autonomy(ctx: EthicsContext) -> EthicsCheckResult:
    """``respect_user_autonomy`` — prescriptive turns must surface options."""
    if ctx.prescribed_single_answer is None:
        return EthicsCheckResult(
            commitment_id="respect_user_autonomy",
            upheld=True,
            reason="prescribed_single_answer flag not supplied",
            runtime_checkable=False,
        )
    if not ctx.prescribed_single_answer:
        return EthicsCheckResult(
            commitment_id="respect_user_autonomy",
            upheld=True,
            reason="response did not prescribe a single answer",
            runtime_checkable=True,
        )
    options = ctx.presented_options_count
    if options is None:
        return EthicsCheckResult(
            commitment_id="respect_user_autonomy",
            upheld=True,
            reason=(
                "prescribed_single_answer=True but presented_options_count "
                "not supplied — cannot judge"
            ),
            runtime_checkable=False,
        )
    if options >= 2:
        return EthicsCheckResult(
            commitment_id="respect_user_autonomy",
            upheld=True,
            reason=(
                f"single prescription but {options} options also surfaced"
            ),
            runtime_checkable=True,
        )
    return EthicsCheckResult(
        commitment_id="respect_user_autonomy",
        upheld=False,
        reason=(
            f"prescribed a single answer with only {options} option(s) "
            "presented"
        ),
        runtime_checkable=True,
        evidence=(
            ("prescribed_single_answer", "True"),
            ("presented_options_count", str(options)),
        ),
    )


_DEFAULT_PREDICATES: dict[str, EthicsPredicate] = {
    "acknowledge_uncertainty": _predicate_acknowledge_uncertainty,
    "defer_high_stakes_to_human_review": _predicate_defer_high_stakes,
    "disclose_limitations": _predicate_disclose_limitations,
    "no_manipulation": _predicate_no_manipulation,
    "respect_user_autonomy": _predicate_respect_user_autonomy,
}


__all__ = [
    "EthicsCheck",
    "EthicsCheckResult",
    "EthicsContext",
    "EthicsPredicate",
    "EthicsVerdict",
]
