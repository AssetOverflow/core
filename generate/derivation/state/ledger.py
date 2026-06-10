"""ADR-0184 S2 — semantic-ledger construction for accumulation.

This module owns only the semantic transition construction.  It deliberately does
not verify or commit answers; callers replay the ledger into ``GroundedDerivation``
and then use the existing verifier/pool.
"""

from __future__ import annotations

from generate.derivation.extract import extract_quantities
from generate.derivation.state.bind import continues_anchor_referent, leading_subject_token
from generate.derivation.state.change import classify_change_polarity, select_change_cue
from generate.derivation.state.model import (
    SemanticLedger,
    SemanticQuantity,
    StateKey,
    StateTransition,
)


def build_accumulation_ledger(
    quantity_clauses: list[str], *, drop_isolated_foreign: bool
) -> SemanticLedger | None:
    """Build the single-referent gain/loss accumulation ledger.

    ``quantity_clauses`` must be the already-filtered sequence of clauses/sub-clauses
    that contain quantities.  The behavior mirrors the pre-S2 accumulation composer:

    * first clause must have exactly one quantity and becomes ``set``;
    * later clauses must continue the anchor referent;
    * each later clause must reduce to exactly one change quantity;
    * polarity must be an unambiguous licensed gain/loss cue;
    * change quantities inherit the anchor unit during replay.
    """

    if len(quantity_clauses) < 2:
        return None

    anchor_clause, *change_clauses = quantity_clauses
    anchor_quantities = extract_quantities(anchor_clause)
    if len(anchor_quantities) != 1:
        return None

    anchor_quantity = anchor_quantities[0]
    anchor_subject = leading_subject_token(anchor_clause)
    key = StateKey(entity=anchor_subject, unit=anchor_quantity.unit)
    transitions: list[StateTransition] = [
        StateTransition(
            key=key,
            op="set",
            quantity=SemanticQuantity.from_quantity(anchor_quantity, clause_index=0),
            cue="set",
            clause_index=0,
        )
    ]

    for idx, clause in enumerate(change_clauses, start=1):
        if not continues_anchor_referent(clause, anchor_subject):
            return None
        change_quantities = list(extract_quantities(clause))
        if drop_isolated_foreign and len(change_quantities) > 1:
            change_quantities = [
                q for q in change_quantities if not (q.unit and q.unit != anchor_quantity.unit)
            ]
        if len(change_quantities) != 1:
            return None
        polarity = classify_change_polarity(clause)
        if polarity is None:
            return None
        change = change_quantities[0]
        transitions.append(
            StateTransition(
                key=key,
                op="gain" if polarity > 0 else "loss",
                quantity=SemanticQuantity.from_quantity(change, clause_index=idx),
                cue=select_change_cue(clause, polarity),
                clause_index=idx,
            )
        )

    if len(transitions) <= 1:
        return None
    return SemanticLedger(transitions=tuple(transitions))
