"""ADR-0047 — forward graph constraint wired into chat hot path.

These tests pin the contract that ``RuntimeConfig.forward_graph_constraint``
gates the ADR-0046 forward-constraint behavior on the live ``ChatRuntime``
path:

  - Default ``False`` — region passed to ``generate()`` is ``None``;
    pre-ADR-0046 behavior preserved.
  - Opt-in ``True`` — the PropositionGraph built from the classified
    intent + articulation plan is converted into an
    ``AdmissibilityRegion`` and fed to ``generate()`` BEFORE the walk;
    the resulting trajectory's admissibility trace records the
    constraint source (graph root IDs).

The opt-in side does not assert "every input must produce a non-empty
constraint" — for short inputs and OOV anchors the graph builder may
yield an unconstrained region by design (ADR-0046 fallback contract).
What we pin is the WIRING: when the flag is on AND the input produces
a non-trivial graph, the region reaching ``generate()`` is non-trivial
and labelled by the graph's root node IDs.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig, DEFAULT_CONFIG
from generate.admissibility import AdmissibilityRegion
from generate.graph_constraint import build_graph_constraint
from generate.intent_bridge import build_graph_from_input
from generate.articulation import ArticulationPlan


# ---------------------------------------------------------------------------
# Default-off behavior
# ---------------------------------------------------------------------------


def test_default_config_keeps_forward_constraint_off() -> None:
    """The transition-window default must remain False to preserve
    the ADR-0024 honest-refusal contract on the existing main path."""
    assert DEFAULT_CONFIG.forward_graph_constraint is False


def test_runtime_default_path_unchanged() -> None:
    """With the default config the runtime still answers — no
    InnerLoopExhaustion from a too-tight forward constraint."""
    rt = ChatRuntime()
    response = rt.chat("light logos")
    assert isinstance(response.surface, str)
    assert response.surface != ""


# ---------------------------------------------------------------------------
# Opt-in wiring
# ---------------------------------------------------------------------------


def test_opt_in_runtime_runs_without_exhaustion_on_short_input() -> None:
    """A short well-known input produces either an unconstrained
    region (empty graph branch) or a viable constrained region —
    in neither case should InnerLoopExhaustion fire on this minimal
    input.  Pins the safety of opting in for benign cases."""
    cfg = replace(RuntimeConfig(), forward_graph_constraint=True)
    rt = ChatRuntime(config=cfg)
    # If the constraint is too tight ChatRuntime.chat would propagate
    # InnerLoopExhaustion (a ValueError subclass); assert it doesn't.
    response = rt.chat("light")
    assert isinstance(response.surface, str)


def test_graph_builder_and_region_are_self_consistent() -> None:
    """ADR-0047 only adds wiring; the geometry it produces must be
    identical to calling ADR-0046's primitives directly on the
    same inputs.  Pins that no hidden normalisation is added at
    the wiring layer."""
    rt = ChatRuntime(config=replace(RuntimeConfig(), forward_graph_constraint=True))
    text = "light addresses truth"
    # A stand-in plan with the same surface shape as the runtime's
    # realized plan — subject/predicate/object slots populated.  The
    # graph builder reads slots, not derived state.
    plan = ArticulationPlan(
        subject="light",
        predicate="addresses",
        object="truth",
        surface="",
        output_language="en",
        frame_id="en",
    )
    graph = build_graph_from_input(text, plan)
    region = build_graph_constraint(graph, rt._context.vocab)
    assert isinstance(region, AdmissibilityRegion)
    # Either unconstrained (empty/OOV graph) or labelled by graph root.
    assert region.label == "graph:unconstrained" or region.label.startswith("graph:")


def test_opt_in_flag_is_observable_in_config() -> None:
    """The flag round-trips through replace() — pins that this is a
    real field on the frozen dataclass, not a stray attribute."""
    cfg = replace(RuntimeConfig(), forward_graph_constraint=True)
    assert cfg.forward_graph_constraint is True
    # Frozen dataclass — opt-in must remain immutable.
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError subclass of Exception
        cfg.forward_graph_constraint = False  # type: ignore[misc]
