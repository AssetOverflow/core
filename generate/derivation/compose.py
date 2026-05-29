"""ADR-0178 GB-2 — sequential composition: list-structure + comparative-scale.

GB-1 read the problem into clauses; GB-2 begins combining structure the blunt MS-3
shapes could not reach. The first increment adds the **same-unit-list → sum** shape
(like quantities joined by an additive cue sum) and **always applies trailing
comparative scalars** (×N / half / doubled) — the `sum-then-scale` family
(0024-class: `(6+4)×2`). The op for each step comes from the text's structure (list
⇒ add; comparative ⇒ scale), not a single blunt op.

All operands are text quantities (grounded) + comparative steps (cue-grounded), so
no derived-intermediate model is needed — the running value is the intermediate.
A stated comparative is part of the problem, so it is always applied (no
bare-vs-scaled alternative, which would self-disagree). Each licensed base shape
(list-sum, product) is one candidate; routed through the proven gate (grounding ∧
cue ∧ unit ∧ completeness ∧ uniqueness). When two bases self-verify and disagree
(e.g. a same-unit list that also has a multiplicative cue), uniqueness refuses —
cue precision (ADR-0177) is what later breaks such ties. Refuse-preferring; sealed.

Branch/DAG structures (0033's `25−12`) and richer relational ops (per/each, more/
older) are later GB increments.
"""

from __future__ import annotations

from typing import Final

from generate.derivation.comparatives import comparative_step, extract_comparative_scalars
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.multistep import MAX_QUANTITIES
from generate.derivation.search import MULTIPLICATIVE_CUES
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

# Additive cues that license summing a same-unit list (lexeme-level, ADR-0165).
_ADDITIVE_CUES: Final[tuple[str, ...]] = ("and", "plus", "altogether", "total")


def _same_unit(quantities: list[Quantity]) -> bool:
    return len({q.unit for q in quantities}) == 1


def compose_sequential(problem_text: str) -> Resolution | None:
    """GB-2 composer — the same-unit **list-sum-then-scale** structure.

    Scope (deliberately narrow): only same-unit quantity *lists*. The list sums
    (additive cue) and any stated comparative scales the sum (sum-then-scale). A
    product base over the same list is added *without* a comparative tail purely as
    a **disagreement-safety** candidate — so a same-unit list that also carries a
    multiplicative cue (ambiguous: sum vs product) refuses rather than guessing.

    Product-of-all / cross-unit products are **not** this composer's job (that is
    MS-3 ``search_chain``); a non-same-unit problem yields no candidate here and
    refuses. This keeps GB-2 to the one structure it adds and avoids the
    product×comparative blowups a blunt all-bases composer produced.

    Refuse-preferring; deterministic; sealed.
    """
    quantities = list(extract_quantities(problem_text))
    if not 2 <= len(quantities) <= MAX_QUANTITIES or not _same_unit(quantities):
        return None

    tokens = _tokens(problem_text)
    tail = tuple(comparative_step(cs) for cs in extract_comparative_scalars(problem_text))
    start, *rest = quantities

    candidates: list[GroundedDerivation] = []
    add_cue = next((c for c in _ADDITIVE_CUES if c in tokens), None)
    if add_cue is not None:  # list-sum (+ applied comparative scale)
        candidates.append(
            GroundedDerivation(
                start=start,
                steps=tuple(Step(op="add", operand=q, cue=add_cue) for q in rest) + tail,
            )
        )
    mult_cue = next((c for c in MULTIPLICATIVE_CUES if c in tokens), None)
    if mult_cue is not None:  # product (no tail) — disagreement-safety only
        candidates.append(
            GroundedDerivation(
                start=start,
                steps=tuple(Step(op="multiply", operand=q, cue=mult_cue) for q in rest),
            )
        )
    return select_self_verified(candidates, problem_text, target_units=())
