"""
Rotor / frame admissibility — ADR-0025 (Accepted).

Sibling to ``generate/admissibility.py``.  Where that module checks
the *destination versor's* alignment with a region's
``relation_blade`` (token-side admissibility, ADR-0024), this module
checks the *rotor's effect on the field* against a region's
``frame_versor`` (rotor-side admissibility, ADR-0025).

The check is:

    F'    = versor_apply(V, F_current)            (hypothetical apply)
    score = cga_inner(F', region.frame_versor)
    admit iff score > 0                             (basic positivity)

A rotor is admitted iff applying it to the current field state lands
the post-rotor field within the region's frame-versor admissible
cone — i.e. the rotor preserves the frame.  This is the rotor-side
analogue of "the destination versor aligns with the relation blade."

Architectural placement
-----------------------

Three candidate homes were on the table when ADR-0025 was a draft
design note: ``algebra/versor.py`` (Option B), ``field/propagate.py``
(Option C), and ``generate/`` (Option A — rejected by the design
note as inheriting ADR-0024's shape "by momentum").

ADR-0025 (Accepted) reverses that recommendation and places the
check **here**, in ``generate/rotor_admissibility.py`` — a
sibling-but-separate module to ``generate/admissibility.py``:

  * Not ``algebra/versor.py``: admissibility is a *semantic* test
    (does this rotor's effect land in the pack's admissible region),
    not a *closure* invariant.  Putting it inside algebra couples
    algebra to pack-derived admissibility state and creates the
    structural temptation to "repair" inadmissible rotors via
    grade projection — exactly the hot-path repair CLAUDE.md
    §Normalization Rules forbids.
  * Not ``field/propagate.py``: CLAUDE.md lists this as a
    forbidden normalization / repair site.  Even a "guard" framed
    as precondition sets a precedent that erodes the rule.
  * Same architectural seam as ADR-0024 / Phase 3 / Phase 2 —
    between selection and propagation — but in its own file so
    endpoint admissibility (token-side, blade) and rotor admissibility
    (rotor-side, frame) remain conceptually separable.  The bloat
    objection from Option A is answered by file separation; the
    algebra-shaped-invariant objection is answered by recognising
    that this is not algebra — it is a pack-grounded semantic test.

The check is pure: no I/O, no learned state, no dynamic imports.
It does not mutate the field; it asks "would this rotor preserve
the frame?" and returns a typed verdict.  Honest refusal at the
caller site uses the same ``InnerLoopExhaustion`` mechanism wired
in Phase 2, with ``RefusalReason.ROTOR_REJECTION`` distinguishing
rotor-side refusal from destination-side refusal in the trace.

This module does NOT compute the rotor; it only checks one.
Rotor construction lives in ``algebra.rotor.word_transition_rotor``;
field application lives in ``algebra.backend.versor_apply``; the
``versor_condition(F') < 1e-6`` invariant is enforced by the
algebra layer's closure on the apply, not by this module.  This
module's only contribution is the *semantic* frame-cone check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from algebra.backend import versor_apply
from algebra.cga import cga_inner

from generate.admissibility import AdmissibilityRegion


_NULL_TOLERANCE = 1e-8


@dataclass(frozen=True, slots=True)
class RotorVerdict:
    """Result of rotor-side admissibility on one candidate rotor.

    Attributes
    ----------
    admitted:
        True iff the rotor's effect on the current field lands within
        the region's frame-versor admissible cone, or there is no
        frame constraint.
    score:
        ``cga_inner(F', frame_versor)`` where ``F' = versor_apply(V,
        F_current)``.  ``float('inf')`` is the sentinel for the
        no-frame-constraint case so callers comparing scores never
        treat "no constraint" as a hard rejection.
    region_label:
        The region label, surfaced into the failure surface.
    reason:
        Human-readable explanation — admissible cone / no constraint /
        below positivity bar.
    """

    admitted: bool
    score: float
    region_label: str
    reason: str = ""


def check_rotor_admissibility(
    region: AdmissibilityRegion,
    *,
    field_current: np.ndarray,
    rotor: np.ndarray,
) -> RotorVerdict:
    """Check that applying ``rotor`` to ``field_current`` stays inside
    the region's frame-versor admissible cone.

    Behavior:

    1. If the region carries no ``frame_versor`` (``None`` or
       null-norm), the rotor is admitted trivially with
       ``score = +inf`` and ``reason = "no frame constraint"``.  No
       sandwich application is performed.

    2. Otherwise:
         F' = versor_apply(rotor, field_current)
         score = cga_inner(F', frame_versor)
       admit iff ``score > 0`` (basic positivity in the frame's
       half-space).  Refuse otherwise with the computed score in
       ``RotorVerdict.score`` so margin-style telemetry can rank
       rotors across candidates.

    The function does NOT mutate ``field_current`` and does NOT
    enforce ``versor_condition(F') < 1e-6`` — that invariant is the
    algebra layer's responsibility on the actual ``propagate_step``,
    not a precondition of this semantic check.  If the algebra's
    closure asserts at apply time, the assertion surfaces from
    ``versor_apply`` directly; this module's contract is the frame
    semantic only.
    """
    if region.frame_versor is None:
        return RotorVerdict(
            admitted=True,
            score=float("inf"),
            region_label=region.label,
            reason="no frame constraint",
        )
    frame = np.asarray(region.frame_versor, dtype=np.float32)
    if float(np.linalg.norm(frame)) < _NULL_TOLERANCE:
        return RotorVerdict(
            admitted=True,
            score=float("inf"),
            region_label=region.label,
            reason="no frame constraint (null frame versor)",
        )
    F = np.asarray(field_current, dtype=np.float32)
    V = np.asarray(rotor, dtype=np.float32)
    F_next = versor_apply(V, F)
    # Cast back to float32 for the cga_inner — versor_apply may run
    # at float64 in the closed Rust path; we keep the score in the
    # same dtype as the blade/inner-product algebra elsewhere.
    F_next32 = np.asarray(F_next, dtype=np.float32)
    score = float(cga_inner(F_next32, frame))
    if score <= 0.0:
        return RotorVerdict(
            admitted=False,
            score=score,
            region_label=region.label,
            reason=(
                f"post-rotor field score {score:.6f} not positive in "
                f"frame {region.label!r}"
            ),
        )
    return RotorVerdict(
        admitted=True,
        score=score,
        region_label=region.label,
        reason="ok",
    )
