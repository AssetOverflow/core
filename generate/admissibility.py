"""
Forward Semantic Control — admissibility regions on the manifold.

Per ADR-0022: the proposition graph computes an *admissibility region*
that bounds the manifold subset in which the field is allowed to
propagate during a given turn.  The region is a pure-function
constraint object; it neither selects tokens nor authors text.  The
realizer/walk consults the region to reject transitions that exit it;
within the region, selection is exact CGA inner product unchanged.

Design decisions resolving the ADR's TBDs:

* **TBD-2 (region intersection algebra)** — composition over two
  regions is defined as:

  - ``allowed_indices``: set intersection of the candidate index
    arrays (the same shape the existing
    `_intersect_candidates` operator in ``generate/stream.py`` already
    uses for the language/salience composition).  Set-intersection on
    finite candidate sets has a closure proof by inspection.
  - ``relation_blade``: outer-product composition.  An empty / zero
    blade on either side is treated as the identity (no constraint
    from that side), so an unconstrained region composes neutrally.
    The resulting blade is *not* unitized here — admissibility is a
    boundary on propagation, not a closure operator, so we do not
    introduce a normalization site (CLAUDE.md §Normalization Rules).
  - ``rotor_constraint``: conjugation under the frame versor.  When
    both sides specify a frame versor we sandwich the inner rotor
    through the outer frame; when only one side specifies a frame
    versor that frame survives.  The closure check on the conjugated
    rotor is *not* asserted in this module; the propagate site asserts
    ``versor_condition(F) < 1e-6`` after application as always.

* **TBD-4 (identity manifold as constraint source)** — admissibility
  exposes an ``IDENTITY`` source slot but v1 leaves population to the
  caller (currently no identity manifold is wired through the
  pipeline).  Composition operates the same regardless of source.

The module has no I/O, no learned state, no dynamic imports — the
trust boundary review in ADR-0022 §Trust Boundary applies (no new
surface introduced).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Iterable

import numpy as np

from algebra.cga import cga_inner, outer_product


_BLADE_DIM = 32
_NULL_TOLERANCE = 1e-8


@unique
class RegionSource(Enum):
    """Where the constraint originated.

    Sources are recorded for telemetry / trace evidence so the failure
    surface can name *which* constraint blocked propagation
    (ADR-0022 §Failure surface).  They do not affect the algebra.
    """

    FRAME = "frame"
    RELATION = "relation"
    IDENTITY = "identity"
    INTENT = "intent"
    COMPOSED = "composed"


@dataclass(frozen=True, slots=True)
class AdmissibilityRegion:
    """A typed bound on admissible manifold transitions for one turn.

    Attributes
    ----------
    allowed_indices:
        Sorted ``np.int64`` array of vocabulary indices allowed as
        destinations.  ``None`` means *no token-set constraint from
        this region*.
    relation_blade:
        Blade specifying which relational shape is admissible.  Zero
        blade means *no relation constraint*.  Selection within the
        region remains exact CGA inner product against this blade.
    frame_versor:
        Versor anchoring the rotor family allowed under this region.
        ``None`` means *no rotor constraint*.
    source:
        Provenance of the constraint, for trace/failure reporting.
    label:
        Human-readable label used in the failure surface so the user
        sees *which* constraint blocked the walk (e.g.
        ``"frame[copular]"``).
    """

    allowed_indices: np.ndarray | None = None
    relation_blade: np.ndarray = field(
        default_factory=lambda: np.zeros(_BLADE_DIM, dtype=np.float32)
    )
    frame_versor: np.ndarray | None = None
    source: RegionSource = RegionSource.INTENT
    label: str = ""

    def __post_init__(self) -> None:
        if self.allowed_indices is not None:
            arr = np.asarray(self.allowed_indices, dtype=np.int64)
            arr = np.unique(arr)
            object.__setattr__(self, "allowed_indices", arr)
        blade = np.asarray(self.relation_blade, dtype=np.float32).copy()
        if blade.shape != (_BLADE_DIM,):
            raise ValueError(
                f"relation_blade must have shape ({_BLADE_DIM},); got {blade.shape}"
            )
        object.__setattr__(self, "relation_blade", blade)
        if self.frame_versor is not None:
            versor = np.asarray(self.frame_versor, dtype=np.float32).copy()
            object.__setattr__(self, "frame_versor", versor)

    # ------------------------------------------------------------------
    # Predicates
    # ------------------------------------------------------------------

    def is_unconstrained(self) -> bool:
        """True when this region imposes no bound at all.

        An unconstrained region is a no-op for admissibility checks
        and a neutral element for composition.
        """
        return (
            self.allowed_indices is None
            and float(np.linalg.norm(self.relation_blade)) < _NULL_TOLERANCE
            and self.frame_versor is None
        )

    def admits_index(self, index: int) -> bool:
        """Token-set admissibility check (pure)."""
        if self.allowed_indices is None:
            return True
        return bool(np.any(self.allowed_indices == int(index)))

    def admits_versor(self, versor: np.ndarray, threshold: float = 0.0) -> bool:
        """Blade-direction admissibility check.

        A candidate versor is admitted iff its CGA inner product with
        the region's relation blade is at least ``threshold``.  An
        empty (zero) blade admits any direction.
        """
        if float(np.linalg.norm(self.relation_blade)) < _NULL_TOLERANCE:
            return True
        score = cga_inner(np.asarray(versor, dtype=np.float32), self.relation_blade)
        return score >= threshold


# ----------------------------------------------------------------------
# Constructors
# ----------------------------------------------------------------------


def unconstrained() -> AdmissibilityRegion:
    """The neutral region — admits any transition.

    Used as the default during the ADR-0022 transition window so
    legacy call sites preserve their existing behavior until they
    pass a real region.
    """
    return AdmissibilityRegion(source=RegionSource.INTENT, label="unconstrained")


def region_from_frame_relation(
    relation_blade: np.ndarray,
    *,
    allowed_indices: np.ndarray | None = None,
    frame_versor: np.ndarray | None = None,
    label: str = "",
) -> AdmissibilityRegion:
    """Build a region from a frame-derived relation blade.

    This is the natural construction site after ``FrameRegistry.select``
    yields a frame: its ``relation`` blade plus (optionally) the
    candidate index set for the active output language compose into
    a region the propagation operator can consult.
    """
    return AdmissibilityRegion(
        allowed_indices=allowed_indices,
        relation_blade=relation_blade,
        frame_versor=frame_versor,
        source=RegionSource.FRAME,
        label=label or "frame",
    )


def region_from_relation_chain(
    relation_versors: Iterable[np.ndarray],
    *,
    label: str = "",
) -> AdmissibilityRegion:
    """Build a region whose blade is the outer product of a relation chain.

    Useful for typed transitive walks (ADR-0018) where the admissible
    shape is the chain of relations the walk has already crossed.
    """
    blade = np.zeros(_BLADE_DIM, dtype=np.float32)
    iterator = iter(relation_versors)
    try:
        first = np.asarray(next(iterator), dtype=np.float32)
    except StopIteration:
        return AdmissibilityRegion(
            relation_blade=blade,
            source=RegionSource.RELATION,
            label=label or "relation-chain[empty]",
        )
    blade = first
    for nxt in iterator:
        blade = outer_product(blade, np.asarray(nxt, dtype=np.float32))
    return AdmissibilityRegion(
        relation_blade=blade,
        source=RegionSource.RELATION,
        label=label or "relation-chain",
    )


# ----------------------------------------------------------------------
# Composition (TBD-2)
# ----------------------------------------------------------------------


def _intersect_indices(
    a: np.ndarray | None, b: np.ndarray | None
) -> np.ndarray | None:
    """Set-intersect two candidate-index arrays (sorted, unique).

    ``None`` is treated as the universal set (no constraint).  When
    both sides specify a set, the result is their sorted intersection;
    an empty intersection is returned as a 0-length int64 array, *not*
    relaxed to ``None`` — an empty admissibility set is a meaningful
    state that the propagation operator must observe (it triggers
    honest refusal per ADR-0022 §2).
    """
    if a is None:
        return b
    if b is None:
        return a
    a_arr = np.asarray(a, dtype=np.int64)
    b_arr = np.asarray(b, dtype=np.int64)
    return np.intersect1d(a_arr, b_arr, assume_unique=False)


def _compose_blades(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compose two relation blades via outer product.

    A zero blade on either side is the neutral element (the other
    side passes through unchanged) — this keeps an unconstrained
    region from collapsing a constrained one.
    """
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a < _NULL_TOLERANCE:
        return np.asarray(b, dtype=np.float32).copy()
    if norm_b < _NULL_TOLERANCE:
        return np.asarray(a, dtype=np.float32).copy()
    return outer_product(a, b)


def _compose_frame_versors(
    outer: np.ndarray | None, inner: np.ndarray | None
) -> np.ndarray | None:
    """Compose two frame versors.

    When both sides specify a frame versor, the *inner* rotor is
    conjugated by the *outer* frame via the sandwich product
    ``outer * inner * reverse(outer)``.  This is exactly the
    ``versor_apply`` shape (CLAUDE.md §Core Primitives), so we route
    through the existing operator rather than reimplementing the
    sandwich here.  When only one side is populated, that side
    survives unchanged.

    The closure check on the resulting rotor is *not* asserted here.
    Admissibility is a boundary on propagation, not a repair
    operator; the call site that applies the rotor will surface a
    ``versor_condition`` failure if and only if the rotor itself is
    ill-formed.
    """
    if outer is None:
        return None if inner is None else np.asarray(inner, dtype=np.float32).copy()
    if inner is None:
        return np.asarray(outer, dtype=np.float32).copy()
    from algebra.backend import versor_apply

    return np.asarray(versor_apply(outer, inner), dtype=np.float32)


def intersect(
    a: AdmissibilityRegion, b: AdmissibilityRegion
) -> AdmissibilityRegion:
    """Compose two admissibility regions (TBD-2).

    Properties (verified in tests):

      * ``intersect(unconstrained(), r) == r`` semantically.
      * ``intersect(r, unconstrained()) == r`` semantically.
      * Token sets compose via sorted set intersection; an empty
        intersection is preserved (it must trigger honest refusal,
        not silent relaxation).
      * Relation blades compose via outer product, with a zero blade
        as the neutral element on either side.
      * Frame versors compose via sandwich conjugation; either side
        absent passes the other side through.

    The composed region is tagged ``RegionSource.COMPOSED`` and
    carries a label that names *both* sources, so the failure surface
    can name precisely which constraint blocked the walk.
    """
    indices = _intersect_indices(a.allowed_indices, b.allowed_indices)
    blade = _compose_blades(a.relation_blade, b.relation_blade)
    frame = _compose_frame_versors(a.frame_versor, b.frame_versor)
    label_parts = [p for p in (a.label, b.label) if p]
    composed_label = "∩".join(label_parts) if label_parts else "composed"
    return AdmissibilityRegion(
        allowed_indices=indices,
        relation_blade=blade,
        frame_versor=frame,
        source=RegionSource.COMPOSED,
        label=composed_label,
    )


# ----------------------------------------------------------------------
# Admissibility check (used at the propagate site)
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AdmissibilityVerdict:
    """Pure result of an admissibility check on a candidate transition.

    Carries the verdict, the score that produced it, and the label of
    the region that issued it — so the failure surface in
    ``CognitiveTurnPipeline`` can name *which* constraint blocked the
    walk (ADR-0022 §2).
    """

    admitted: bool
    score: float
    region_label: str
    reason: str = ""


def check_transition(
    region: AdmissibilityRegion,
    *,
    candidate_index: int,
    candidate_versor: np.ndarray,
    threshold: float = 0.0,
) -> AdmissibilityVerdict:
    """Decide whether a candidate transition is admitted by ``region``.

    A transition is admitted iff:

      1. The destination index is in ``allowed_indices`` (or there is
         no index constraint), AND
      2. The candidate versor's CGA inner product against
         ``relation_blade`` meets ``threshold`` (or there is no blade
         constraint).

    The rotor / frame versor side of the region is *not* checked here
    — rotor admissibility is enforced at the rotor-application site by
    composition under the frame versor; this function checks token-
    and direction-side admissibility, which is what
    ``_nearest_next`` / ``_nearest_content_word`` need before
    selecting a destination.
    """
    candidate_versor = np.asarray(candidate_versor, dtype=np.float32)
    if region.allowed_indices is not None and not region.admits_index(candidate_index):
        return AdmissibilityVerdict(
            admitted=False,
            score=float("-inf"),
            region_label=region.label,
            reason=f"index {int(candidate_index)} not in admissible set",
        )
    blade_norm = float(np.linalg.norm(region.relation_blade))
    if blade_norm < _NULL_TOLERANCE:
        return AdmissibilityVerdict(
            admitted=True,
            score=0.0,
            region_label=region.label,
            reason="no blade constraint",
        )
    score = float(cga_inner(candidate_versor, region.relation_blade))
    if score < threshold:
        return AdmissibilityVerdict(
            admitted=False,
            score=score,
            region_label=region.label,
            reason=f"score {score:.6f} below threshold {threshold:.6f}",
        )
    return AdmissibilityVerdict(
        admitted=True,
        score=score,
        region_label=region.label,
        reason="ok",
    )


@dataclass(frozen=True, slots=True)
class AdmissibilityTraceStep:
    """One per-transition record from a constrained walk (ADR-0023 §2).

    ``candidates_before`` and ``candidates_after`` are the candidate
    index arrays observed before and after admissibility filtering at
    this step.  ``selected_index`` / ``selected_word`` are the
    destination chosen by the existing `_nearest_next` selector.  The
    typed ``verdict`` is the result of ``check_transition`` evaluated
    against the selected candidate; an unconstrained region produces
    a verdict with ``reason="unconstrained"`` so the trace shape is
    invariant across constrained / unconstrained walks.

    The trace is observation-only.  It does not influence selection
    and does not introduce any normalization or repair on the field
    path (CLAUDE.md §Normalization Rules).
    """

    step_index: int
    region_label: str
    region_source: str
    candidates_before: tuple[int, ...]
    candidates_after: tuple[int, ...]
    selected_index: int
    selected_word: str
    verdict: AdmissibilityVerdict
    # ADR-0024 §2 — when inner-loop admissibility is on, candidates
    # rejected by ``check_transition`` before final selection are
    # recorded here as (index, word, score) triples in rejection
    # order.  Empty in the ADR-0023 boundary-only path so the trace
    # hash stays byte-identical for legacy turns (the canonical form
    # folds this field only when non-empty).
    rejected_attempts: tuple[tuple[int, str, float], ...] = ()

    def canonical(self) -> dict[str, object]:
        """Deterministic dict representation for trace hashing."""
        out: dict[str, object] = {
            "step_index": int(self.step_index),
            "region_label": str(self.region_label),
            "region_source": str(self.region_source),
            "candidates_before": [int(i) for i in self.candidates_before],
            "candidates_after": [int(i) for i in self.candidates_after],
            "selected_index": int(self.selected_index),
            "selected_word": str(self.selected_word),
            "verdict_admitted": bool(self.verdict.admitted),
            "verdict_reason": str(self.verdict.reason),
        }
        if self.rejected_attempts:
            out["rejected_attempts"] = [
                [int(i), str(w), float(s)] for (i, w, s) in self.rejected_attempts
            ]
        return out


def filter_candidates(
    region: AdmissibilityRegion,
    candidate_indices: np.ndarray | None,
) -> np.ndarray | None:
    """Intersect ``candidate_indices`` with ``region.allowed_indices``.

    This is the bridge function the walk and proposition sites call
    so the existing ``candidate_indices`` plumbing in
    ``generate/stream.py`` and ``generate/proposition.py`` continues
    to flow.  An unconstrained region passes the input through
    unchanged.

    Returns ``None`` when both inputs are unconstrained (preserving
    the legacy "no restriction" sentinel); returns the sorted
    intersection otherwise.  An empty intersection is returned as a
    0-length array so the caller can detect and surface honest
    refusal rather than silently relaxing.
    """
    if region.allowed_indices is None:
        return candidate_indices
    if candidate_indices is None:
        return region.allowed_indices
    return _intersect_indices(region.allowed_indices, candidate_indices)
