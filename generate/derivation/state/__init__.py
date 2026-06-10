"""ADR-0184 — scoped semantic-state helper substrate.

This package is the sealed derivation-lane home for reusable semantic reading
helpers.  S1 exposes behavior-equivalent referent/change-cue helpers extracted from
:mod:`generate.derivation.accumulate`.  S2 adds a minimal semantic-state model
(SET/GAIN/LOSS over one entity/unit key), an accumulation ledger builder, and a
replay bridge back to ``GroundedDerivation``.  No serving path imports this package,
and no new candidate behavior is introduced here: the ledger only re-expresses the
proven accumulation reading, and arithmetic commitment still happens only after
replay through the existing verifier/pool.
"""

from __future__ import annotations

from generate.derivation.state.bind import (
    PRONOUNS,
    continues_anchor_referent,
    leading_subject_token,
)
from generate.derivation.state.change import (
    GAIN_VERBS,
    LOSS_VERBS,
    classify_change_polarity,
    select_change_cue,
)
from generate.derivation.state.ledger import build_accumulation_ledger
from generate.derivation.state.model import (
    VALID_TRANSITION_OPS,
    SemanticLedger,
    SemanticQuantity,
    SemanticStateError,
    StateKey,
    StateTransition,
)
from generate.derivation.state.replay import replay_accumulation_ledger

__all__ = [
    "GAIN_VERBS",
    "LOSS_VERBS",
    "PRONOUNS",
    "VALID_TRANSITION_OPS",
    "SemanticLedger",
    "SemanticQuantity",
    "SemanticStateError",
    "StateKey",
    "StateTransition",
    "build_accumulation_ledger",
    "classify_change_polarity",
    "continues_anchor_referent",
    "leading_subject_token",
    "replay_accumulation_ledger",
    "select_change_cue",
]
