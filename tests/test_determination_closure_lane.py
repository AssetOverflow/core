"""Step D falsification lane — ``evals.determination_closure``.

The lane is the deterministic, falsifiable proof that idle consolidation makes the
engine learn from its determined facts: the directly-answerable set climbs monotonically
across idle ticks to the deductive-closure fixed point, with wrong=0 (the member ∘
member fallacy is never derived), honesty (derived facts stay SPECULATIVE), and a
provenance replay obligation (every derived record re-verifies ENTAILED).
"""

from __future__ import annotations

from evals.determination_closure import run


def test_falsification_met() -> None:
    report = run(depth=9)
    assert report["falsification_met"] is True, report["verdicts"]


def test_each_verdict_holds() -> None:
    v = run(depth=9)["verdicts"]
    assert v["monotone"]
    assert v["strict_increase_on_consolidating_tick"]
    assert v["converged_to_fixed_point"]
    assert v["closure_complete"]
    assert v["canary_member_member_never_derived"]
    assert v["no_fabricated_membership"]
    assert v["provenance_replay_ok"]
    assert v["all_derived_speculative"]


def test_closure_climbs_strictly_then_plateaus() -> None:
    sizes = run(depth=9)["member_closure_sizes"]
    # Non-decreasing throughout.
    assert all(b >= a for a, b in zip(sizes, sizes[1:]))
    # Starts at 1 (the single told membership) and ends at the full chain (10 classes).
    assert sizes[0] == 1
    assert sizes[-1] == 10
    # The final transition is a no-op (the converged fixed point repeats the size).
    assert sizes[-1] == sizes[-2]


def test_run_is_deterministic() -> None:
    a = run(depth=7)
    b = run(depth=7)
    assert a["member_closure_sizes"] == b["member_closure_sizes"]
    assert a["final_member_closure"] == b["final_member_closure"]
    assert a["derived_record_count"] == b["derived_record_count"]


def test_depth_is_clamped_to_chain_length() -> None:
    # Asking for more depth than the chain provides clamps, never errors.
    report = run(depth=999)
    assert report["depth"] == 9
    assert report["falsification_met"] is True
