"""ADR-0206 §5 — the math-serving reach seam.

`select_self_verified` is now parameterized with a `ReachPolicy`. The load-bearing
properties this proves:

- **STRICT is byte-identical** — the unique-answer and refuse-on-disagreement paths are
  untouched (every current caller passes STRICT, so the sealed serving lanes do not move).
- **The widening is structurally inert** — a disagreement is resolved past gold ONLY via
  the `VERIFIED` canonical-comparison gate (`_canonically_verified`), which is unbuilt and
  returns `None`. So even a wider reach refuses; the absolute `wrong == 0` holds by
  construction, not by convention. A statistical reliability license must NEVER widen math.
- **Live wiring, not dead code** — when the `VERIFIED` gate is (test-)injected to produce a
  winner, a wider reach resolves the disagreement and STRICT still refuses. This is the
  exact, tested integration point a future `VERIFIED` producer plugs into.
"""

from __future__ import annotations

import generate.derivation.verify as verify_mod
from core.response_governance import APPROXIMATE_POLICY, STRICT_POLICY
from generate.derivation import GroundedDerivation, Quantity, Resolution, Step, select_self_verified


def _q(v: float, unit: str, tok: str) -> Quantity:
    return Quantity(value=v, unit=unit, source_token=tok)


_DISAGREE_TEXT = "She has 5 apples and 3 apples."


def _disagreeing() -> list[GroundedDerivation]:
    # Both COMPLETE + grounded over {5,3}; different ops → different answers (8 vs 15).
    d_add = GroundedDerivation(start=_q(5, "apples", "5"), steps=(Step(op="add", operand=_q(3, "apples", "3"), cue="and"),))
    d_mul = GroundedDerivation(start=_q(5, "apples", "5"), steps=(Step(op="multiply", operand=_q(3, "apples", "3"), cue="and"),))
    assert d_add.answer != d_mul.answer
    return [d_add, d_mul]


def _unique() -> list[GroundedDerivation]:
    return [GroundedDerivation(start=_q(5, "apples", "5"), steps=(Step(op="add", operand=_q(3, "apples", "3"), cue="and"),))]


# --------------------------------------------------------------------------- #
# STRICT (default) is byte-identical to the pre-seam gate
# --------------------------------------------------------------------------- #


def test_default_is_strict_refuse_on_disagreement() -> None:
    # No policy arg → STRICT → refuse (the sealed serving behavior).
    assert select_self_verified(_disagreeing(), _DISAGREE_TEXT) is None
    assert select_self_verified(_disagreeing(), _DISAGREE_TEXT, policy=STRICT_POLICY) is None


def test_unique_answer_unchanged_at_every_reach() -> None:
    # The seam touches only the disagreement path; a unique answer resolves identically.
    for policy in (None, STRICT_POLICY, APPROXIMATE_POLICY):
        res = select_self_verified(_unique(), _DISAGREE_TEXT, policy=policy)
        assert isinstance(res, Resolution) and res.answer == 8.0


# --------------------------------------------------------------------------- #
# The widening is STRUCTURALLY inert until a VERIFIED producer lands
# --------------------------------------------------------------------------- #


def test_wider_reach_still_refuses_without_a_verified_producer() -> None:
    # _canonically_verified returns None (unbuilt) → even APPROXIMATE refuses a
    # disagreement. wrong=0 holds by construction, not by caller discipline.
    assert select_self_verified(_disagreeing(), _DISAGREE_TEXT, policy=APPROXIMATE_POLICY) is None


def test_verified_gate_returns_none_today() -> None:
    assert verify_mod._canonically_verified(_disagreeing(), _DISAGREE_TEXT, APPROXIMATE_POLICY) is None


# --------------------------------------------------------------------------- #
# Live wiring — the seam fires the moment the VERIFIED gate produces a winner
# --------------------------------------------------------------------------- #


def test_seam_is_live_wiring(monkeypatch) -> None:
    derivs = _disagreeing()
    winner = derivs[0]  # the (test-)VERIFIED answer, 8
    monkeypatch.setattr(verify_mod, "_canonically_verified", lambda v, t, p: winner)

    # A wider reach now resolves the disagreement to the VERIFIED winner...
    res = select_self_verified(derivs, _DISAGREE_TEXT, policy=APPROXIMATE_POLICY)
    assert isinstance(res, Resolution) and res.answer == 8.0
    # ...but STRICT NEVER widens, even when the gate would produce a winner.
    assert select_self_verified(derivs, _DISAGREE_TEXT, policy=STRICT_POLICY) is None
