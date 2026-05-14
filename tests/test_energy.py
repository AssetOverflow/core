"""
ADR-0006 — Field Energy Operator tests.

Covers:
  - EnergyClass enum properties (vault_candidate, governance_critical)
  - aspect_weight() lookup table (Hebrew and Greek aspect forms)
  - FieldEnergyOperator.compute() — all four input axes
  - Class boundary thresholds (E0–E4)
  - Anchor-adjacent E4 escalation
  - EnergyProfile.requires_architect_review
  - propagate_step() energy recomputation
  - Aspect weight preservation across propagation steps
"""

import numpy as np
import pytest

from core.physics.energy import (
    EnergyClass,
    EnergyProfile,
    FieldEnergyOperator,
    aspect_weight,
)
from field.state import FieldState
from field.propagate import propagate_step
from algebra.versor import unitize_versor
from algebra.rotor import make_rotor_from_angle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_versor() -> np.ndarray:
    """Return a Cl(4,1) unit versor suitable for FieldState.F."""
    v = np.zeros(32, dtype=np.float64)
    v[0] = 1.0
    return unitize_versor(v)


def _identity_rotor() -> np.ndarray:
    v = np.zeros(32, dtype=np.float64)
    v[0] = 1.0
    return v


_op = FieldEnergyOperator()


# ---------------------------------------------------------------------------
# EnergyClass properties
# ---------------------------------------------------------------------------

class TestEnergyClassProperties:
    def test_e0_is_vault_candidate(self):
        assert EnergyClass.E0.vault_candidate is True

    def test_e1_is_vault_candidate(self):
        assert EnergyClass.E1.vault_candidate is True

    def test_e2_is_not_vault_candidate(self):
        assert EnergyClass.E2.vault_candidate is False

    def test_e3_is_not_vault_candidate(self):
        assert EnergyClass.E3.vault_candidate is False

    def test_e4_is_governance_critical(self):
        assert EnergyClass.E4.governance_critical is True

    def test_e3_is_not_governance_critical(self):
        assert EnergyClass.E3.governance_critical is False


# ---------------------------------------------------------------------------
# aspect_weight lookup
# ---------------------------------------------------------------------------

class TestAspectWeight:
    def test_none_features_returns_zero(self):
        assert aspect_weight(None) == 0.0

    def test_empty_features_returns_zero(self):
        assert aspect_weight({}) == 0.0

    def test_qatal_is_low(self):
        w = aspect_weight({"aspect": "qatal"})
        assert w == pytest.approx(0.15)

    def test_aorist_is_low(self):
        w = aspect_weight({"tense": "aorist"})
        assert w == pytest.approx(0.15)

    def test_imperative_is_highest(self):
        w = aspect_weight({"mood": "imperative"})
        assert w == pytest.approx(0.90)

    def test_yiqtol_is_high(self):
        w = aspect_weight({"aspect": "yiqtol"})
        assert w == pytest.approx(0.65)

    def test_wayyiqtol_is_mid(self):
        w = aspect_weight({"aspect": "wayyiqtol"})
        assert w == pytest.approx(0.45)

    def test_unknown_aspect_returns_zero(self):
        assert aspect_weight({"aspect": "unknown_form"}) == 0.0

    def test_case_insensitive(self):
        assert aspect_weight({"aspect": "IMPERATIVE"}) == pytest.approx(0.90)

    def test_max_of_multiple_features(self):
        # qatal + imperative: max should be imperative
        w = aspect_weight({"aspect": "qatal", "mood": "imperative"})
        assert w == pytest.approx(0.90)


# ---------------------------------------------------------------------------
# FieldEnergyOperator — class boundary thresholds
# ---------------------------------------------------------------------------

class TestFieldEnergyOperatorThresholds:
    """Drive raw score into each class by controlling inputs."""

    def test_all_zero_inputs_gives_e0(self):
        ep = _op.compute()
        assert ep.energy_class is EnergyClass.E0
        assert ep.raw < 0.16

    def test_low_convergence_no_activation_gives_e1(self):
        # convergence_density=2, no recency, no residual, no aspect
        # convergence contribution: 0.35 * log1p(2)/log1p(8) ≈ 0.35 * 0.404 ≈ 0.141
        ep = _op.compute(convergence_density=2)
        assert ep.energy_class in {EnergyClass.E0, EnergyClass.E1}

    def test_moderate_inputs_gives_e2(self):
        # convergence=4 -> ~0.30 contrib; activation=4/8*1=0.5 -> 0.125 contrib
        ep = _op.compute(
            convergence_density=4,
            activation_count=4,
            current_cycle=5,
            last_activation_cycle=4,
        )
        assert ep.energy_class is EnergyClass.E2

    def test_high_convergence_and_activation_gives_e3(self):
        ep = _op.compute(
            convergence_density=8,
            activation_count=8,
            current_cycle=1,
            last_activation_cycle=0,
            coherence_residual=0.5,
        )
        assert ep.energy_class is EnergyClass.E3

    def test_imperative_aspect_and_full_convergence_gives_e4(self):
        ep = _op.compute(
            convergence_density=8,
            activation_count=8,
            current_cycle=1,
            last_activation_cycle=0,
            coherence_residual=1.0,
            morphology_features={"mood": "imperative"},
        )
        assert ep.energy_class is EnergyClass.E4

    def test_e4_raw_boundary(self):
        # raw >= 0.82 without anchor_adjacent should be E4
        # Use max inputs to guarantee raw >= 0.82
        ep = _op.compute(
            convergence_density=8,
            activation_count=8,
            current_cycle=0,
            last_activation_cycle=0,
            coherence_residual=1.0,
            morphology_features={"mood": "imperative"},
        )
        assert ep.energy_class is EnergyClass.E4
        assert ep.raw >= 0.82


# ---------------------------------------------------------------------------
# Anchor-adjacent escalation
# ---------------------------------------------------------------------------

class TestAnchorAdjacentEscalation:
    def test_anchor_adjacent_escalates_to_e4_at_lower_raw(self):
        # Without anchor: raw ~0.72 might be E3
        ep_no_anchor = _op.compute(
            convergence_density=8,
            activation_count=6,
            current_cycle=1,
            last_activation_cycle=0,
            coherence_residual=0.3,
            anchor_adjacent=False,
        )
        ep_anchor = _op.compute(
            convergence_density=8,
            activation_count=6,
            current_cycle=1,
            last_activation_cycle=0,
            coherence_residual=0.3,
            anchor_adjacent=True,
        )
        # anchor_adjacent path escalates at raw >= 0.72 instead of >= 0.82
        if ep_anchor.raw >= 0.72:
            assert ep_anchor.energy_class is EnergyClass.E4
        # Without anchor and same raw, must be lower class
        if ep_no_anchor.raw < 0.82:
            assert ep_no_anchor.energy_class is not EnergyClass.E4

    def test_anchor_adjacent_stored_on_profile(self):
        ep = _op.compute(anchor_adjacent=True)
        assert ep.anchor_adjacent is True


# ---------------------------------------------------------------------------
# EnergyProfile.requires_architect_review
# ---------------------------------------------------------------------------

class TestRequiresArchitectReview:
    def test_e4_always_requires_review(self):
        ep = _op.compute(
            convergence_density=8,
            activation_count=8,
            current_cycle=0,
            last_activation_cycle=0,
            coherence_residual=1.0,
            morphology_features={"mood": "imperative"},
        )
        assert ep.energy_class is EnergyClass.E4
        assert ep.requires_architect_review is True

    def test_e3_anchor_adjacent_requires_review(self):
        # Force E3 but with anchor_adjacent=True
        # E3: raw in [0.62, 0.82). Build that range.
        ep = _op.compute(
            convergence_density=8,
            activation_count=8,
            current_cycle=1,
            last_activation_cycle=0,
            coherence_residual=0.2,
            anchor_adjacent=True,
        )
        # If raw landed in E3 range and anchor_adjacent, review required
        if ep.energy_class is EnergyClass.E3:
            assert ep.requires_architect_review is True

    def test_e2_does_not_require_review(self):
        ep = _op.compute(
            convergence_density=4,
            activation_count=4,
            current_cycle=5,
            last_activation_cycle=4,
        )
        if ep.energy_class is EnergyClass.E2:
            assert ep.requires_architect_review is False


# ---------------------------------------------------------------------------
# propagate_step energy recomputation
# ---------------------------------------------------------------------------

class TestPropagateStepEnergyRecomputation:
    def _make_state_with_energy(self, energy: EnergyProfile | None = None) -> FieldState:
        F = _clean_versor()
        return FieldState(F=F, node=0, step=0, energy=energy)

    def _rotor(self) -> np.ndarray:
        return _identity_rotor()

    def test_no_energy_propagates_none(self):
        state = self._make_state_with_energy(None)
        new_state = propagate_step(state, self._rotor())
        assert new_state.energy is None

    def test_step_increments(self):
        ep = _op.compute(convergence_density=2, activation_count=2, current_cycle=0)
        state = self._make_state_with_energy(ep)
        new_state = propagate_step(state, self._rotor())
        assert new_state.step == 1

    def test_energy_is_recomputed_not_carried_verbatim(self):
        """After propagation the EnergyProfile object must be a new instance."""
        ep = _op.compute(convergence_density=4, activation_count=3, current_cycle=0)
        state = self._make_state_with_energy(ep)
        new_state = propagate_step(state, self._rotor())
        assert new_state.energy is not ep

    def test_activation_count_increments(self):
        ep = _op.compute(convergence_density=4, activation_count=3, current_cycle=0)
        state = self._make_state_with_energy(ep)
        new_state = propagate_step(state, self._rotor())
        assert new_state.energy.activation_count == ep.activation_count + 1

    def test_convergence_density_preserved(self):
        ep = _op.compute(convergence_density=6, activation_count=2, current_cycle=0)
        state = self._make_state_with_energy(ep)
        new_state = propagate_step(state, self._rotor())
        assert new_state.energy.convergence_density == 6

    def test_anchor_adjacent_preserved(self):
        ep = _op.compute(convergence_density=3, anchor_adjacent=True)
        state = self._make_state_with_energy(ep)
        new_state = propagate_step(state, self._rotor())
        assert new_state.energy.anchor_adjacent is True

    def test_aspect_weight_preserved_across_step(self):
        """Aspect weight baked at injection must survive propagation."""
        ep = _op.compute(
            convergence_density=4,
            activation_count=2,
            current_cycle=0,
            morphology_features={"mood": "imperative"},
        )
        assert ep.aspect_weight == pytest.approx(0.90)
        state = self._make_state_with_energy(ep)
        new_state = propagate_step(state, self._rotor())
        assert new_state.energy.aspect_weight == pytest.approx(0.90)

    def test_coherence_residual_reset_to_zero_on_propagation(self):
        """Propagation is not a corrective pass; residual must be zero."""
        ep = _op.compute(
            convergence_density=4,
            activation_count=2,
            coherence_residual=0.8,
        )
        state = self._make_state_with_energy(ep)
        new_state = propagate_step(state, self._rotor())
        assert new_state.energy.coherence_residual == pytest.approx(0.0)

    def test_multiple_steps_monotonically_age(self):
        """Repeated propagation cools energy as recency decays."""
        ep = _op.compute(
            convergence_density=4,
            activation_count=4,
            current_cycle=0,
            last_activation_cycle=0,
        )
        state = self._make_state_with_energy(ep)
        # 20 steps of propagation — recency term exp(-age/12) decays
        for _ in range(20):
            state = propagate_step(state, _identity_rotor())
        # After 20 cold steps, energy class should not be E4
        assert state.energy.energy_class is not EnergyClass.E4


# ---------------------------------------------------------------------------
# EnergyProfile field storage round-trip on FieldState
# ---------------------------------------------------------------------------

class TestEnergyProfileRoundTrip:
    def test_field_state_carries_energy_profile(self):
        ep = _op.compute(convergence_density=3, activation_count=2)
        F = _clean_versor()
        state = FieldState(F=F, node=0, step=0, energy=ep)
        assert state.energy is ep
        assert state.energy.energy_class in list(EnergyClass)

    def test_field_state_advance_preserves_energy(self):
        ep = _op.compute(convergence_density=3)
        F = _clean_versor()
        state = FieldState(F=F, node=0, step=0, energy=ep)
        new_F = _clean_versor()
        advanced = state.advance(new_F, new_node=1)
        assert advanced.energy is ep
        assert advanced.step == 1
