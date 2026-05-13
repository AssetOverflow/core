"""
The single injection gate.

The ONLY point where raw data enters the versor manifold.
normalize_to_versor() is called here and nowhere else in production code.

Normalization doctrine (three-tier):

  unitize_versor()       algebra/versor.py — construction primitive.
                         Allowed in: algebra/, persona/, vocab/ (pre-add).
                         Purpose: build valid rotors/motors/manifold entries.

  inject()               THIS function — gate operation, once per raw input.
                         Calls normalize_to_versor() internally at the
                         holonomy-to-field boundary.

  FORBIDDEN:             normalization inside propagation, generation,
                         vault recall, or as post-hoc repair after a
                         supposedly closed transition. If normalization is
                         needed there, fix the operator — not the result.

Contract:
  Input:  raw token sequence + VocabManifold
  Output: FieldState with F satisfying versor_condition(F) < 1e-6
"""

from algebra.versor import normalize_to_versor, versor_condition
from algebra.holonomy import holonomy_encode
from field.state import FieldState


def inject(tokens: list, vocab) -> FieldState:
    """
    Encode a token sequence and inject into the versor manifold.

    Steps:
    1. Look up each token's versor in the vocab manifold
    2. Encode via holonomy walk
    3. normalize_to_versor() — the single allowed gate normalization call
    4. Assert versor condition before returning
    """
    word_versors = [vocab.get_versor(t) for t in tokens]
    H = holonomy_encode(word_versors)
    F = normalize_to_versor(H)

    cond = versor_condition(F)
    if cond > 1e-5:
        raise RuntimeError(
            f"Injection produced non-versor field: condition={cond:.2e}. "
            "Check holonomy_encode() and normalize_to_versor()."
        )

    return FieldState(F=F, node=0, step=0, holonomy=H)
