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

from generate.derivation.clauses import segment_clauses
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
    """GB-2/GB-3 composer — the **clause-local** same-unit list-sum-then-scale.

    Scope (deliberately narrow): only same-unit quantity *lists*. The list sums
    (additive cue) and any stated comparative scales the sum (sum-then-scale). A
    product base over the same list is added *without* a comparative tail purely as
    a **disagreement-safety** candidate — so a same-unit list that also carries a
    multiplicative cue (ambiguous: sum vs product) refuses rather than guessing.

    Product-of-all / cross-unit products are **not** this composer's job (that is
    MS-3 ``search_chain``); a non-same-unit problem yields no candidate here and
    refuses. This keeps the composer to the one structure it adds and avoids the
    product×comparative blowups a blunt all-bases composer produced.

    **GB-3 referent guard (wrong=0-first).** The list-sum structure must be
    licensed *within a single clause*. The earlier whole-problem version summed any
    same-unit quantities anywhere in the text, which silently merged unrelated
    referents/scopes (a later sentence's quantity, a second actor's total, a
    depletion event) into one sum — admitting wrong structures whose value happened
    to ground (audit ADR-0178 hazards H1/H2/H3). This composer cannot model
    referents, so when the licensed structure would span clauses it **refuses**
    (cross-clause, referent-aware chaining is GB-3b):

    * quantities must live in exactly **one** clause (segment_clauses); 0 or >1
      quantity-bearing clauses ⇒ refuse;
    * any comparative scalar **outside** that clause ⇒ refuse (it binds to a
      referent/structure this slice does not model).

    Refuse-preferring; deterministic; sealed.
    """
    # GB-3: the structure must be licensed within a single clause (referent guard).
    quantity_clauses = [c for c in segment_clauses(problem_text) if extract_quantities(c)]
    if len(quantity_clauses) != 1:
        return None
    clause = quantity_clauses[0]
    # A comparative living outside the list clause binds an unmodelled referent.
    if len(extract_comparative_scalars(problem_text)) != len(extract_comparative_scalars(clause)):
        return None

    quantities = list(extract_quantities(clause))
    if not 2 <= len(quantities) <= MAX_QUANTITIES or not _same_unit(quantities):
        return None

    tokens = _tokens(clause)
    tail = tuple(comparative_step(cs) for cs in extract_comparative_scalars(clause))
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
