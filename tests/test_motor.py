import numpy as np
import pytest

from algebra.versor import unitize_versor, versor_condition
from persona.motor import PersonaMotor


def _random_versor(seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return unitize_versor(rng.standard_normal(32).astype(np.float32))


def test_identity_motor_no_change():
    """Identity motor returns input unchanged."""
    motor = PersonaMotor.identity()
    F = _random_versor(0)
    result = motor.apply(F)
    assert np.allclose(result, F, atol=1e-5)


def test_motor_application_stays_on_manifold():
    """Applying a motor keeps F on the versor manifold."""
    t = unitize_versor(_random_versor(1))
    r = unitize_versor(_random_versor(2))
    motor = PersonaMotor(t, r)
    F = _random_versor(3)
    result = motor.apply(F)
    assert versor_condition(result) < 1e-4


def test_motor_composition_on_manifold():
    """Composing two motors produces a motor on the manifold."""
    t1 = unitize_versor(_random_versor(0))
    r1 = unitize_versor(_random_versor(1))
    t2 = unitize_versor(_random_versor(2))
    r2 = unitize_versor(_random_versor(3))
    m1 = PersonaMotor(t1, r1)
    m2 = PersonaMotor(t2, r2)
    composed = m1.compose(m2)
    assert versor_condition(composed.M) < 1e-4


def test_from_concept_vector():
    """PersonaMotor.from_concept_vector should not raise and produces a valid motor."""
    concept = np.array([0.5, -0.3, 0.8], dtype=np.float32)
    motor = PersonaMotor.from_concept_vector(concept)
    assert versor_condition(motor.M) < 1e-4
