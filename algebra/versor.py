"""
The three versor primitives.

These are the ONLY normalization/transition/check functions in the system.
Do not add correction, monitoring, or grade-guard functions here.
If you think you need something else, you have an unclosed operation upstream.
"""

import numpy as np
from .cl41 import geometric_product, reverse, scalar_part, norm_squared


def versor_apply(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """
    Sandwich product: V * F * reverse(V).

    The ONLY allowed field transition in the system.
    Algebraically closed on the versor manifold:
    if V and F are versors, V*F*reverse(V) is a versor.
    No pre/post normalization. No grade projection. No guards.
    """
    return geometric_product(V, geometric_product(F, reverse(V)))


def normalize_to_versor(F: np.ndarray) -> np.ndarray:
    """
    Project F onto the versor manifold: F / sqrt(|F * reverse(F)|).

    Call this ONCE per input at the injection gate (ingest/gate.py).
    Never call mid-propagation, mid-generation, or in the vault.
    If you feel the urge to call this elsewhere, fix the upstream operation.
    """
    n2 = norm_squared(F)
    if abs(n2) < 1e-12:
        raise ValueError("Cannot normalize a null multivector to a versor.")
    return F / np.sqrt(abs(n2))


def versor_condition(F: np.ndarray) -> float:
    """
    Returns ||F * reverse(F) - 1||_F.

    Zero means F is on the versor manifold.
    Use in tests and at the injection gate only.
    Never call in the generation hot path.
    """
    product = geometric_product(F, reverse(F))
    product = product.copy()
    product[0] -= 1.0
    return float(np.linalg.norm(product))
