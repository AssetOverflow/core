"""Pure pass/fail predicates over soak evidence — the falsifiable gates.

Each predicate is a pure function of ``SoakResult`` evidence (it runs no turns
and mutates nothing), so it is trivially replayable and each can be
mutation-verified to *bite*. The predicates:

- **P1 closure** — every turn satisfies ``versor_condition < 1e-6``. A hard
  green guard backed by algebra-owned construction (Decision 0).
- **P2a determinism** — two independent, no-reboot runs of equal length produce
  byte-identical ``trace_hash`` sequences. A hard green guard; a failure is a
  real nondeterminism bug.
- **P2b reboot transparency** — a rebooted run vs an uninterrupted baseline. The
  *diagnostic*: today a reboot restores only recognizers / candidates /
  turn_count (Shape B, ADR-0146) and discards the lived field / vault / anchor,
  so the first post-reboot turn is expected to diverge. P2b LOCATES that
  divergence; it does not pretend it is absent. The structural invariant it
  enforces is weaker and always-true: a reboot must never change turns *before*
  the reboot point.
- **P3 bounded resources** — vault growth stays linear-bounded per turn (no
  unbounded cache/store leak). RSS is recorded for the long lane; on a short
  soak it is dominated by startup and only loosely bounded here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from evals.l10_continuity.runner import SoakResult, TurnRecord

VERSOR_CEILING: float = 1e-6


@dataclass(frozen=True, slots=True)
class PredicateOutcome:
    name: str
    passed: bool
    detail: str
    metrics: dict = field(default_factory=dict)


def evaluate_p1_closure(
    result: SoakResult, *, ceiling: float = VERSOR_CEILING
) -> PredicateOutcome:
    """P1 — every turn's field is a valid versor (``versor_condition < ceiling``)."""
    violations = [
        (r.turn_index, r.versor_condition)
        for r in result.records
        if not (r.versor_condition < ceiling)
    ]
    worst = max((r.versor_condition for r in result.records), default=0.0)
    passed = not violations
    detail = (
        f"all {len(result.records)} turns closed (worst={worst:.3e} < {ceiling:.0e})"
        if passed
        else f"{len(violations)} turn(s) breached the versor ceiling: {violations[:5]}"
    )
    return PredicateOutcome(
        name="P1_closure",
        passed=passed,
        detail=detail,
        metrics={"worst_versor_condition": worst, "violations": violations},
    )


def _first_divergence(a: tuple[str, ...], b: tuple[str, ...]) -> int | None:
    """Index of the first position where two trace-hash sequences differ.

    A length mismatch counts as a divergence at the first extra/missing index.
    Returns ``None`` when the sequences are byte-identical.
    """
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def evaluate_p2a_determinism(
    run_a: SoakResult, run_b: SoakResult
) -> PredicateOutcome:
    """P2a — two independent no-reboot runs are byte-identical in trace_hash."""
    if run_a.reboot_at or run_b.reboot_at:
        raise ValueError("P2a compares two NO-reboot runs; pass reboot_at=().")
    ha, hb = run_a.trace_hashes(), run_b.trace_hashes()
    div = _first_divergence(ha, hb)
    passed = div is None and len(ha) == len(hb)
    detail = (
        f"{len(ha)} turns byte-identical across two independent runtimes"
        if passed
        else f"trace_hash diverged at turn {div} "
        f"({ha[div] if div is not None and div < len(ha) else '∅'} != "
        f"{hb[div] if div is not None and div < len(hb) else '∅'})"
    )
    return PredicateOutcome(
        name="P2a_determinism",
        passed=passed,
        detail=detail,
        metrics={"n_turns": len(ha), "first_divergence": div},
    )


@dataclass(frozen=True, slots=True)
class RebootTransparency:
    """The measured outcome of a reboot leg vs an uninterrupted baseline."""

    pre_reboot_identical: bool
    post_reboot_transparent: bool
    first_divergence: int | None
    reboot_turn: int


def evaluate_p2b_reboot_transparency(
    rebooted: SoakResult, baseline: SoakResult
) -> tuple[PredicateOutcome, RebootTransparency]:
    """P2b — locate where a rebooted run diverges from an uninterrupted one.

    The predicate PASSES on the structural invariant only: a reboot must not
    change any turn *before* the reboot point (those are the same first
    segment, so they must be identical — a failure here is a real determinism
    or state-leak bug). Full post-reboot transparency is the *measured*
    diagnostic, returned alongside; it is expected to be ``False`` until the
    lived field/vault are persisted across reboot (the Shape-B+ work).
    """
    if not rebooted.reboot_at:
        raise ValueError("P2b expects a rebooted run (reboot_at non-empty).")
    if baseline.reboot_at:
        raise ValueError("P2b baseline must be an uninterrupted run (reboot_at=()).")

    reboot_turn = rebooted.reboot_at[0]
    hr, hb = rebooted.trace_hashes(), baseline.trace_hashes()
    div = _first_divergence(hr, hb)

    pre_reboot_identical = div is None or div >= reboot_turn
    post_reboot_transparent = div is None

    transparency = RebootTransparency(
        pre_reboot_identical=pre_reboot_identical,
        post_reboot_transparent=post_reboot_transparent,
        first_divergence=div,
        reboot_turn=reboot_turn,
    )
    if not pre_reboot_identical:
        detail = (
            f"determinism violated BEFORE reboot: diverged at turn {div} "
            f"(reboot was at {reboot_turn}) — a reboot must not change earlier turns"
        )
    elif post_reboot_transparent:
        detail = (
            f"reboot at turn {reboot_turn} is FULLY transparent "
            f"({len(hr)} turns byte-identical to the uninterrupted run)"
        )
    else:
        detail = (
            f"reboot at turn {reboot_turn} is NOT transparent: first divergence "
            f"at turn {div} (lived field/vault not persisted — Shape B). "
            "Pre-reboot turns are identical; the resume gap is post-reboot."
        )
    return (
        PredicateOutcome(
            name="P2b_reboot_transparency",
            passed=pre_reboot_identical,
            detail=detail,
            metrics={
                "reboot_turn": reboot_turn,
                "first_divergence": div,
                "post_reboot_transparent": post_reboot_transparent,
            },
        ),
        transparency,
    )


def evaluate_p3_bounded_resources(
    result: SoakResult, *, vault_per_turn_ceiling: int = 4
) -> PredicateOutcome:
    """P3 — vault growth is linear-bounded per turn (no unbounded store leak).

    The real turn loop stores a small fixed number of vault entries per turn
    (user + assistant + occasional promotion); an unbounded cache or a per-turn
    accumulator that grows super-linearly would breach the ceiling. RSS is
    recorded for the long lane but is dominated by startup on a short soak, so
    it is reported, not gated, here.

    Ceiling basis (measured): the real soak grows ~2–3 vault entries/turn; the
    default ``vault_per_turn_ceiling=4`` is ~130–200% of that, so it tolerates
    the as-designed user+assistant(+promotion) writes while a genuinely
    unbounded store (a per-turn cache) breaches it. A leak slower than the
    ceiling is by design out of scope for this linear-bound check; it is the
    long-horizon RSS lane's job.
    """
    if result.reboot_at:
        raise ValueError("P3 expects a no-reboot run (vault resets on reboot).")
    records: tuple[TurnRecord, ...] = result.records
    sizes = [r.vault_size for r in records]
    monotonic = all(b >= a for a, b in zip(sizes, sizes[1:]))
    breaches = [
        (r.turn_index, r.vault_size)
        for r in records
        if r.vault_size > vault_per_turn_ceiling * (r.turn_index + 1)
    ]
    passed = monotonic and not breaches
    peak_first = records[0].peak_rss_raw if records else 0
    peak_last = records[-1].peak_rss_raw if records else 0
    detail = (
        f"vault grew monotonically within {vault_per_turn_ceiling}/turn "
        f"(final size {sizes[-1] if sizes else 0} over {len(records)} turns)"
        if passed
        else f"resource bound breached: monotonic={monotonic}, breaches={breaches[:5]}"
    )
    return PredicateOutcome(
        name="P3_bounded_resources",
        passed=passed,
        detail=detail,
        metrics={
            "final_vault_size": sizes[-1] if sizes else 0,
            "vault_monotonic": monotonic,
            "vault_breaches": breaches,
            "peak_rss_raw_first": peak_first,
            "peak_rss_raw_last": peak_last,
        },
    )


def evaluate_p4_recovery_determinism(
    recovery_a: SoakResult, recovery_b: SoakResult
) -> PredicateOutcome:
    """P4 — two independent crash-recoveries from the same checkpoint converge.

    The L10 kill-9 claim: a hard kill (incl. mid-checkpoint-write) always
    next-boots onto a valid prior checkpoint (ADR-0156 atomicity) and resumes
    *deterministically*. Because Shape B discards the lived field/vault, a
    recovered run does NOT match the uninterrupted baseline (that is the P2b
    gap) — so determinism here means: two independent recoveries from the same
    durable checkpoint produce byte-identical continuations. A non-deterministic
    recovery (torn read, partial state, nondeterministic boot) breaks this.
    """
    if not recovery_a.reboot_at or not recovery_b.reboot_at:
        raise ValueError("P4 expects two crash-recovery runs (reboot_at non-empty).")
    tail_a = tuple(r.trace_hash for r in recovery_a.post_reboot_records())
    tail_b = tuple(r.trace_hash for r in recovery_b.post_reboot_records())
    div = _first_divergence(tail_a, tail_b)
    passed = div is None and len(tail_a) == len(tail_b) and len(tail_a) > 0
    detail = (
        f"two crash-recoveries produced byte-identical {len(tail_a)}-turn tails"
        if passed
        else f"recovery diverged at post-reboot index {div} "
        f"(|a|={len(tail_a)}, |b|={len(tail_b)})"
    )
    return PredicateOutcome(
        name="P4_recovery_determinism",
        passed=passed,
        detail=detail,
        metrics={"recovered_tail_len": len(tail_a), "first_divergence": div},
    )


def evaluate_p4_commit_point(
    recovered_turn_count: int | None, expected_turn_count: int
) -> PredicateOutcome:
    """P4 (WAL/ARIES force boundary) — the checkpoint IS the commit boundary.

    The engine-state checkpoint is the last durable act of a turn, so a kill
    next-boots onto a checkpoint whose ``turn_count`` equals the number of
    fully-committed turns — never a partially-applied turn. A recovered count
    that is ``None`` (no checkpoint) or != the committed count means the durable
    record did not gate the turn as a unit.
    """
    passed = recovered_turn_count == expected_turn_count
    detail = (
        f"recovered checkpoint turn_count={recovered_turn_count} "
        f"== {expected_turn_count} committed turns"
        if passed
        else f"recovered turn_count={recovered_turn_count} != "
        f"expected {expected_turn_count} (commit boundary not atomic)"
    )
    return PredicateOutcome(
        name="P4_commit_point",
        passed=passed,
        detail=detail,
        metrics={
            "recovered_turn_count": recovered_turn_count,
            "expected_turn_count": expected_turn_count,
        },
    )


def evaluate_p5b_anchor_stability(
    result: SoakResult,
    *,
    warmup: int = 2,
    collapse_floor: float = 1.0,
    freeze_floor: float = 0.05,
) -> PredicateOutcome:
    """P5b — the field anchors without collapsing onto the attractor or freezing.

    The crux of the T-experience gate and the direct long-horizon test of the
    sanctioned ``_session_anchor_pull`` (α=0.05). Two failure modes, both fatal
    to "continuous experiencing life":

    - **collapse** — ``dist_to_anchor`` trends to 0 (the field is swallowed by
      the anchor; every turn becomes the same concept). Guard: the minimum
      steady-state distance stays above ``collapse_floor``.
    - **freeze** — ``turn_movement`` trends to 0 (the field stops moving with
      content). Guard: the median steady-state movement stays above
      ``freeze_floor``.

    Evaluated over the steady state (after ``warmup`` turns) because turn 0 is
    the anchor itself (distance 0) and turn 1 is a large transient.

    Threshold basis (measured, not arbitrary): on the real soak the steady-state
    ``dist_to_anchor`` sits in a ~4.0–6.2 band and the median ``turn_movement``
    is ~1.5. The defaults are set deliberately BELOW that band —
    ``collapse_floor=1.0`` (a ~75%+ drop toward the anchor) and
    ``freeze_floor=0.05`` (movement ~1/30th of healthy) — so P5b is a *binary
    catastrophe* gate (the T-experience question is "does the field collapse or
    freeze?", a yes/no), NOT an early-warning trend detector. A gradual-drift
    detector would need a long-horizon trend test and is a deliberate follow-up;
    tightening these floors toward the healthy band risks false positives on a
    different corpus or a longer horizon.
    """
    if result.reboot_at:
        raise ValueError("P5b expects a no-reboot run (anchor resets on reboot).")
    tail = result.records[warmup:]
    dists = [r.dist_to_anchor for r in tail if not math.isnan(r.dist_to_anchor)]
    moves = [r.turn_movement for r in tail if not math.isnan(r.turn_movement)]
    if len(dists) < 2 or len(moves) < 2:
        return PredicateOutcome(
            name="P5b_anchor_stability",
            passed=False,
            detail=f"insufficient steady-state turns to evaluate (warmup={warmup})",
            metrics={"n_steady": len(dists)},
        )
    min_dist = min(dists)
    sorted_moves = sorted(moves)
    median_move = sorted_moves[len(sorted_moves) // 2]
    no_collapse = min_dist > collapse_floor
    no_freeze = median_move > freeze_floor
    passed = no_collapse and no_freeze
    if passed:
        detail = (
            f"anchored without collapse (min dist {min_dist:.3f} > {collapse_floor}) "
            f"or freeze (median move {median_move:.3f} > {freeze_floor})"
        )
    else:
        cause = []
        if not no_collapse:
            cause.append(f"COLLAPSE (min dist {min_dist:.3f} ≤ {collapse_floor})")
        if not no_freeze:
            cause.append(f"FREEZE (median move {median_move:.3f} ≤ {freeze_floor})")
        detail = "; ".join(cause)
    return PredicateOutcome(
        name="P5b_anchor_stability",
        passed=passed,
        detail=detail,
        metrics={
            "min_steady_dist_to_anchor": min_dist,
            "median_steady_movement": median_move,
            "n_steady": len(dists),
        },
    )


def evaluate_p5c_coherence(
    result: SoakResult, *, min_surface_len: int = 1, min_distinct_surfaces: int = 2
) -> PredicateOutcome:
    """P5c — the field does not wander into noise or collapse to one output.

    Two degeneracies: empty/trivial surfaces (the field drifted into noise) and
    a single repeated surface across the whole horizon (the field froze onto one
    output). Both are caught by surface non-emptiness + a distinct-surface floor.
    """
    surfaces = [r.surface for r in result.records]
    empties = [r.turn_index for r in result.records if len(r.surface) < min_surface_len]
    distinct = len(set(surfaces))
    passed = not empties and distinct >= min_distinct_surfaces
    detail = (
        f"surfaces stayed coherent ({distinct} distinct, none empty) "
        f"over {len(surfaces)} turns"
        if passed
        else f"incoherent: empties={empties[:5]}, distinct_surfaces={distinct}"
    )
    return PredicateOutcome(
        name="P5c_coherence",
        passed=passed,
        detail=detail,
        metrics={"distinct_surfaces": distinct, "empty_turns": empties},
    )
