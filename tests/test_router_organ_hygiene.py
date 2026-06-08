"""Standing router-hygiene invariant.

**No organ may block another organ's legitimate proposal unless it has first POSITIVELY recognized
the input as belonging to its own family.**

Operationally: on every OTHER organ's gold corpus, when an organ refuses, the refusal reason must
map to the non-substantive ``input_shape`` family ("not my domain") — never a substantive boundary
and never a growth surface. (An organ reading foreign text as ``setup_correct`` would be the
ambiguity case, separately guaranteed to be 0 by the router tests.) A substantive boundary on
foreign text is what lets one organ suppress another organ's legitimate proposal (boundary-first),
the exact hazard caught at N6 (``category_pair_not_found``), R3e (``temporal_state``), and R3.1
(``missing_rate``).

This is a MUST-PASS gate before any future organ joins ``route_setup``: add the new organ's gold
to ``_GOLD`` and its classifier to ``_ORGANS``, and this test enforces the rule for free.
"""

from __future__ import annotations

from core.comprehension_attempt import (
    classify_r1,
    classify_r2,
    classify_r3,
    family_for_reason,
)
from evals.constraint_oracle.runner import _load_r2_gold
from evals.rate_oracle.runner import _load_rate_gold
from evals.setup_oracle.runner import _load_r1_gold

_ORGANS = {
    "r1_quantitative": classify_r1,
    "r2_constraints": classify_r2,
    "r3_rate": classify_r3,
}
_GOLD = {
    "r1_quantitative": _load_r1_gold,
    "r2_constraints": _load_r2_gold,
    "r3_rate": _load_rate_gold,
}


def test_no_organ_claims_a_substantive_boundary_on_foreign_text() -> None:
    for owner, load in _GOLD.items():
        for fx in load():
            for organ_name, classify in _ORGANS.items():
                if organ_name == owner:
                    continue
                att = classify(fx["text"])
                if att.outcome != "setup_refused":
                    continue  # setup_correct on foreign text == ambiguity (guarded == 0 elsewhere)
                fam = family_for_reason(att.refusal_reason)
                assert fam is not None and fam.name == "input_shape", (
                    f"{organ_name} refused {owner}'s {fx.get('id')!r} with reason "
                    f"{att.refusal_reason!r} -> family {fam.name if fam else None!r}; an organ must "
                    f"refuse foreign text as input_shape (not-my-domain), never a substantive boundary"
                )
