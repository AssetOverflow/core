"""ADR-0058 — pin the null-lift property of ``forward_graph_constraint``.

ADR-0047 characterised the cognition-lane A/B between
``forward_graph_constraint`` OFF and ON and recorded the finding:

    intent_accuracy / surface_groundedness / term_capture_rate /
    versor_closure_rate are byte-identical with the flag flipped,
    while 6/13 cases produce a non-trivial constraint label.

That finding is what scoped ADR-0048 through ADR-0053 — the surface-
grounding gap lives downstream of propagation, not in the candidate
set the constraint narrows.  ADR-0058 promotes the finding from a
historical observation to a **regression-tested invariant**: if a
future change unexpectedly *does* move a cognition-lane metric on the
flag flip, this test fails and the architectural assumption that the
flag is observably inert on the cognition lane gets re-examined as a
deliberate transition rather than silent drift.

The test runs the full cognition public split twice — flag OFF vs ON —
and asserts the four watched metrics are pair-wise identical.
"""

from __future__ import annotations

from dataclasses import replace

from core.config import RuntimeConfig
from evals.framework import get_lane, run_lane


# The four metrics ADR-0047 reported zero delta on.
_WATCHED: tuple[str, ...] = (
    "intent_accuracy",
    "surface_groundedness",
    "term_capture_rate",
    "versor_closure_rate",
)


def _run(config: RuntimeConfig) -> dict[str, float]:
    lane = get_lane("cognition")
    result = run_lane(lane, version="v1", split="public", config=config)
    return {k: float(result.metrics[k]) for k in _WATCHED}


def test_cognition_lane_metrics_identical_with_flag_flipped() -> None:
    """The ADR-0047 null-lift invariant: every watched metric is
    pair-wise identical between flag OFF and flag ON on the public
    cognition split.  If a future change moves any of these metrics
    on the flag flip, the architectural assumption that the constraint
    is observably inert on this lane no longer holds — surface that
    as a regression rather than silent drift.
    """
    off = _run(RuntimeConfig(forward_graph_constraint=False))
    on = _run(replace(RuntimeConfig(), forward_graph_constraint=True))

    for metric in _WATCHED:
        assert off[metric] == on[metric], (
            f"ADR-0058 null-lift invariant broken on metric {metric!r}: "
            f"flag OFF={off[metric]} vs flag ON={on[metric]}.  Either a "
            f"deliberate downstream wiring change closed the surface-"
            f"grounding gap (in which case update ADR-0058 to mark the "
            f"transition), or a regression slipped in (in which case "
            f"find it before merging)."
        )


def test_default_config_keeps_flag_off() -> None:
    """The default ``RuntimeConfig().forward_graph_constraint`` remains
    ``False``.  This is the contract production callers rely on; any
    flip of the default would change the runtime's default behaviour
    on inputs whose intent-derived graph is non-trivial."""
    assert RuntimeConfig().forward_graph_constraint is False
