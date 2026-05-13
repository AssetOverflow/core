"""
Field propagation — the generation heartbeat.

Each step: F <- versor_apply(V, F)

V is the rotor for the current node's outgoing edge in the vocab manifold.
No correction. No normalization. No conditional branching. The loop is tight.

Hot path routes through algebra.backend, which dispatches to the Rust
extension (core_rs) when available and falls back to pure Python silently.
"""

from algebra.backend import versor_apply
from field.state import FieldState


def propagate_step(state: FieldState, V) -> FieldState:
    """
    Apply one versor transition.
    V is the edge rotor from the current node.
    Returns a new FieldState one step forward on the manifold.
    """
    new_F = versor_apply(V, state.F)
    return FieldState(F=new_F, node=state.node, step=state.step + 1)
