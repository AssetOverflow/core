"""
Persona as a CGA motor — a rigid screw motion on the generation manifold.

M = T * R where:
  T = translator versor (persona's position in concept space)
  R = rotor          (persona's characteristic rotation)

Applying persona: F_voiced = M * F * reverse(M)
This is a versor product. Persona application is algebraically closed.
No weight overlay. No post-hoc bias. No separate correction pass.

Normalization doctrine:
  All calls here use unitize_versor() — the construction primitive.
  These are all construction-time operations: building motors from raw
  component arrays, composing two existing motors. None of these are
  gate injection operations, so normalize_to_versor() is forbidden here.
"""

import numpy as np
from algebra.versor import versor_apply, unitize_versor
from algebra.cl41 import geometric_product, reverse, basis_vector, N_COMPONENTS


class PersonaMotor:
    def __init__(self, translator: np.ndarray, rotor: np.ndarray):
        """
        translator: a versor encoding translational bias in CGA
        rotor:      a versor encoding rotational character
        Both must satisfy versor_condition < 1e-6.
        """
        self.M = unitize_versor(
            geometric_product(
                np.asarray(translator, dtype=np.float32),
                np.asarray(rotor, dtype=np.float32),
            )
        )

    def apply(self, F: np.ndarray) -> np.ndarray:
        """Apply persona to field F. Returns M * F * reverse(M)."""
        return versor_apply(self.M, F)

    def compose(self, other: "PersonaMotor") -> "PersonaMotor":
        """
        Compose two persona motors: M_combined = self.M * other.M
        Used to blend persona layers (base persona + session persona).
        """
        result = PersonaMotor.__new__(PersonaMotor)
        result.M = unitize_versor(geometric_product(self.M, other.M))
        return result

    @classmethod
    def identity(cls) -> "PersonaMotor":
        """The identity motor — applies no transformation."""
        inst = cls.__new__(cls)
        inst.M = np.zeros(N_COMPONENTS, dtype=np.float32)
        inst.M[0] = 1.0
        return inst

    @classmethod
    def from_concept_vector(cls, concept: np.ndarray) -> "PersonaMotor":
        """
        Build a persona motor from a 3D concept vector in R^3.
        Embeds as a CGA translator: T = 1 + (1/2) * t * e_inf
        where e_inf = e+ + e- (the point at infinity in CGA).
        """
        concept = np.asarray(concept, dtype=np.float32)
        assert len(concept) == 3

        e_inf = basis_vector(3) + basis_vector(4)  # e+ + e-

        t_blade = np.zeros(N_COMPONENTS, dtype=np.float32)
        for i in range(3):
            t_blade += concept[i] * geometric_product(basis_vector(i), e_inf)

        translator = np.zeros(N_COMPONENTS, dtype=np.float32)
        translator[0] = 1.0
        translator += 0.5 * t_blade

        rotor = np.zeros(N_COMPONENTS, dtype=np.float32)
        rotor[0] = 1.0

        return cls(
            unitize_versor(translator),
            unitize_versor(rotor),
        )
