from __future__ import annotations

import numpy as np

from algebra.rotor import make_rotor_from_angle
from algebra.versor import versor_apply, versor_condition
from chat.runtime import _drive_bias_operator


def test_drive_bias_operator_is_closed_versor() -> None:
    operator = _drive_bias_operator((0.75, -0.25, 0.5), available=0.8)

    assert operator.shape == (32,)
    assert versor_condition(operator) < 1e-6


def test_drive_bias_application_preserves_field_closure() -> None:
    field = make_rotor_from_angle(0.25, bivector_idx=6)
    operator = _drive_bias_operator((0.75, -0.25, 0.5), available=0.8)

    nudged = versor_apply(operator, field)

    assert versor_condition(nudged) < 1e-6
