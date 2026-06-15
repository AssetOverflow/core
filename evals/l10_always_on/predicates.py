"""Pure pass/fail predicates over heartbeat-soak evidence — the falsifiable gates.

Each predicate is a pure function of ``HeartbeatSoakResult`` evidence (it runs no beats and
mutates nothing), so each can be mutation-verified to *bite*. The idle-path claims today's
always-on work makes, none of which the short daemon unit tests or the turn-loop soak prove
at horizon:

- **H1 closure** — every OBSERVED idle beat satisfies ``versor_condition < 1e-6``. The L10
  riskiest-unknown for the IDLE path: the heartbeat holds closure over long uptime WITHOUT
  any repair (it only reads ``versor_condition``).
- **H2 bounded idle** — a beat that does NO work adds NOTHING to the vault (no idle leak); a
  growing store on an idle beat is a resource leak that only manifests at horizon.
- **H3 convergence** — a saturated idle life SETTLES: once it stops working it stays at rest
  (no re-awakening) and the final beat is at rest — a continuously-IDLING steady state, not
  a churning or thrashing one — and closure still holds across the converged tail.
- **H4 reboot resume** — a reboot mid-soak resumes the SAME life: the reconstruct under the
  strict identity guard succeeds, the pre-reboot DERIVED learning survives, and post-reboot
  closure holds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from evals.l10_always_on.runner import HeartbeatSoakResult

VERSOR_CEILING: float = 1e-6


@dataclass(frozen=True, slots=True)
class PredicateOutcome:
    name: str
    passed: bool
    detail: str
    metrics: dict = field(default_factory=dict)


def evaluate_h1_closure(
    result: HeartbeatSoakResult, *, ceiling: float = VERSOR_CEILING
) -> PredicateOutcome:
    """H1 — every observed idle beat is a valid versor (``versor_condition < ceiling``).

    Requires at least one OBSERVED beat (a real field) so the gate is non-vacuous — a soak
    where the field never existed cannot pass H1 by saying nothing."""
    observed = result.observed()
    violations = [
        (r.beat_index, r.versor_condition)
        for r in observed
        if not (r.versor_condition is not None and r.versor_condition < ceiling)
    ]
    worst = max((r.versor_condition for r in observed if r.versor_condition is not None), default=0.0)
    passed = bool(observed) and not violations
    if not observed:
        detail = "no beat observed a field — closure is vacuous, not held"
    elif passed:
        detail = f"all {len(observed)} observed beats closed (worst={worst:.3e} < {ceiling:.0e})"
    else:
        detail = f"{len(violations)} idle beat(s) breached the versor ceiling: {violations[:5]}"
    return PredicateOutcome(
        name="H1_closure",
        passed=passed,
        detail=detail,
        metrics={"observed_beats": len(observed), "worst_versor_condition": worst, "violations": violations},
    )


def evaluate_h2_bounded_idle(result: HeartbeatSoakResult) -> PredicateOutcome:
    """H2 — a no-work idle beat adds nothing to the vault (no idle resource leak).

    A ``did_work=False`` beat that GROWS the vault over the previous beat is an idle leak —
    the kind that is invisible at 5 beats and fatal at 100k. Work beats (consolidation)
    legitimately grow it and are exempt."""
    records = result.records
    leaks = [
        (r.beat_index, prev.vault_size, r.vault_size)
        for prev, r in zip(records, records[1:])
        if not r.did_work and r.vault_size > prev.vault_size
    ]
    monotonic = all(b.vault_size >= a.vault_size for a, b in zip(records, records[1:]))
    passed = not leaks
    final = records[-1].vault_size if records else 0
    detail = (
        f"no idle beat grew the vault (final size {final} over {len(records)} beats, monotonic={monotonic})"
        if passed
        else f"idle resource leak: {len(leaks)} no-work beat(s) grew the vault: {leaks[:5]}"
    )
    return PredicateOutcome(
        name="H2_bounded_idle",
        passed=passed,
        detail=detail,
        metrics={"idle_leaks": leaks, "final_vault_size": final, "vault_monotonic": monotonic},
    )


def evaluate_h3_convergence(
    result: HeartbeatSoakResult, *, min_converged_tail: int = 2
) -> PredicateOutcome:
    """H3 — a saturated idle life SETTLES and stays settled (no re-awakening), at rest at
    the end, with closure intact across the converged tail.

    Three failure modes: it never settles (the final beat still works — churns forever); it
    re-awakens (a ``did_work=True`` beat after it had gone to rest — a nondeterministic idle
    leak); or closure breaks on the converged tail. The converged tail must be at least
    ``min_converged_tail`` beats so 'settled' is observed, not assumed."""
    records = result.records
    if not records:
        return PredicateOutcome("H3_convergence", False, "no beats to evaluate", {})

    rest_indices = [i for i, r in enumerate(records) if not r.did_work]
    if not rest_indices:
        return PredicateOutcome(
            "H3_convergence", False, "the life never went to rest (every beat did work)", {}
        )
    convergence_at = rest_indices[0]
    tail = records[convergence_at:]
    reawakenings = [r.beat_index for r in tail if r.did_work]
    final_at_rest = not records[-1].did_work
    closure_breaks = [r.beat_index for r in tail if not r.field_valid]
    long_enough = len(tail) >= min_converged_tail
    passed = not reawakenings and final_at_rest and not closure_breaks and long_enough

    if passed:
        detail = (
            f"converged at beat {convergence_at}; the {len(tail)}-beat tail stayed at rest "
            f"with closure intact"
        )
    else:
        cause = []
        if reawakenings:
            cause.append(f"RE-AWAKENED at {reawakenings[:5]}")
        if not final_at_rest:
            cause.append("never settled (final beat still working)")
        if closure_breaks:
            cause.append(f"closure broke on the tail at {closure_breaks[:5]}")
        if not long_enough:
            cause.append(f"converged tail too short ({len(tail)} < {min_converged_tail})")
        detail = "; ".join(cause)
    return PredicateOutcome(
        name="H3_convergence",
        passed=passed,
        detail=detail,
        metrics={
            "convergence_beat": convergence_at,
            "converged_tail_len": len(tail),
            "reawakenings": reawakenings,
        },
    )


def evaluate_h4_reboot_resume(result: HeartbeatSoakResult) -> PredicateOutcome:
    """H4 — a reboot mid-soak resumes the SAME life.

    Three obligations: the reconstruct under the strict identity guard succeeded
    (``resumed_cleanly`` — a different-life checkpoint would have raised
    ``IdentityContinuityError``); the pre-reboot DERIVED learning survived
    (``learned_fact_survived`` — recalled post-reboot, not merely re-derivable); and
    post-reboot closure holds (every segment>0 beat is a valid versor)."""
    if not result.reboot_at:
        raise ValueError("H4 expects a soak with a reboot leg (reboot_at non-empty).")
    post = result.post_reboot_records()
    post_closure_breaks = [
        r.beat_index for r in post if r.versor_condition is not None and not r.field_valid
    ]
    passed = (
        result.resumed_cleanly
        and result.learned_fact_survived is True
        and not post_closure_breaks
    )
    if passed:
        detail = (
            f"reboot at {result.reboot_at[0]} resumed the SAME life: identity guard passed, "
            f"learning survived, {len(post)} post-reboot beats closed"
        )
    else:
        cause = []
        if not result.resumed_cleanly:
            cause.append("reconstruct RAISED IdentityContinuityError (not the same life)")
        if result.learned_fact_survived is not True:
            cause.append(f"pre-reboot learning did NOT survive (={result.learned_fact_survived})")
        if post_closure_breaks:
            cause.append(f"post-reboot closure broke at {post_closure_breaks[:5]}")
        detail = "; ".join(cause)
    return PredicateOutcome(
        name="H4_reboot_resume",
        passed=passed,
        detail=detail,
        metrics={
            "resumed_cleanly": result.resumed_cleanly,
            "learned_fact_survived": result.learned_fact_survived,
            "post_reboot_beats": len(post),
        },
    )
