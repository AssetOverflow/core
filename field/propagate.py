"""
Field propagation — the generation heartbeat.

Each step: F <- versor_apply(V, F)

V is the rotor for the current node's outgoing edge in the vocab manifold.
No correction. No normalization. No conditional branching. The loop is tight.

Energy recomputation: after each versor step the EnergyProfile carried in
FieldState is refreshed. The refresh uses only the structural inputs that
are available without external context (activation_count tracks steps taken;
cycle is the new step index). Convergence density and morphology features
are not available inside propagate_step — they are set at the injection gate
and carried forward unchanged. Coherence residual is zero inside a clean
propagation path (no corrective pass is applied here). This is intentional:
propagation is not correction.

Hot path routes through algebra.backend, which dispatches to the Rust
extension (core_rs) when available and falls back to pure Python silently.
"""

from algebra.backend import versor_apply
from core.physics.energy import FieldEnergyOperator
from field.state import FieldState

_energy_op = FieldEnergyOperator()


def propagate_step(state: FieldState, V) -> FieldState:
    """
    Apply one versor transition and refresh the energy profile.

    V is the edge rotor from the current node.
    Returns a new FieldState one step forward on the manifold.

    Energy recomputation policy:
    - activation_count increments by 1 per step (field is actively propagating).
    - current_cycle = new step index (monotonic proxy for time).
    - last_activation_cycle stays at the value set at injection (the gate
      records when this region was first injected; propagation does not reset
      that anchor).
    - coherence_residual = 0.0 (propagation is not a corrective pass).
    - convergence_density and morphology_features are inherited from the
      existing EnergyProfile when one is present; otherwise defaults apply.
    - anchor_adjacent is inherited unchanged.
    """
    new_F = versor_apply(V, state.F)
    new_step = state.step + 1

    if state.energy is not None:
        ep = state.energy
        new_energy = _energy_op.compute(
            convergence_density=ep.convergence_density,
            activation_count=ep.activation_count + 1,
            current_cycle=new_step,
            last_activation_cycle=ep.last_activation_cycle,
            coherence_residual=0.0,
            morphology_features=None,   # aspect weight baked at injection; not re-read here
            anchor_adjacent=ep.anchor_adjacent,
        )
        # Carry the baked aspect_weight forward: the operator won't re-derive
        # it from morphology_features=None, so we patch the raw score to
        # preserve the aspect contribution that was set at the gate.
        if ep.aspect_weight > 0.0:
            from dataclasses import replace as _replace
            # Recompute with the original aspect weight patched back in:
            # raw already accounts for convergence/recency/residual from above.
            # We rebuild raw adding the aspect component the operator lost.
            patched_raw = new_energy.raw + 0.20 * ep.aspect_weight
            patched_raw = min(patched_raw, 1.0)
            from core.physics.energy import EnergyClass as _EC
            if ep.anchor_adjacent and patched_raw >= 0.72:
                patched_class = _EC.E4
            elif patched_raw >= 0.82:
                patched_class = _EC.E4
            elif patched_raw >= 0.62:
                patched_class = _EC.E3
            elif patched_raw >= 0.38:
                patched_class = _EC.E2
            elif patched_raw >= 0.16:
                patched_class = _EC.E1
            else:
                patched_class = _EC.E0
            new_energy = _replace(
                new_energy,
                raw=patched_raw,
                energy_class=patched_class,
                aspect_weight=ep.aspect_weight,
            )
    else:
        new_energy = None

    return FieldState(
        F=new_F,
        node=state.node,
        step=new_step,
        holonomy=state.holonomy,
        energy=new_energy,
        valence=state.valence,
    )
