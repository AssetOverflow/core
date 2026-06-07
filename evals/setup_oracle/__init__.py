"""Setup-oracle lane — grade the READING (the semantic setup), not the answer.

The relational_metric lane scores answers: `comprehend → project → oracle_answer →
compare gold integer`. That hides a hazard the held-out measurements exposed — a WRONG
reading can produce a coincidentally-correct number and still pass. The setup-oracle
closes that gap: it compares the reader's comprehended STRUCTURE (the relations it read
+ the BoundUnknown question target it emitted) against the INDEPENDENT gold structure
(the relational_metric cases' own `relations`/`query`, authored separately from the
binding-graph reader). A wrong setup is a first-class failure even when its answer is right.

`setup_wrong` is the load-bearing, wrong=0-critical count: a reading that misrepresents
the problem. v1 grades structure (facts + equations + question target/state/form); unit
modelling stays covered by the admissibility tests (a documented signature extension).
"""

from evals.setup_oracle.runner import run
from evals.setup_oracle.signature import (
    gold_unknown_signature,
    reader_symbol_units,
    reader_unknown_signature,
    relation_signature,
    symbol_unit_signature,
)

__all__ = [
    "gold_unknown_signature",
    "reader_symbol_units",
    "reader_unknown_signature",
    "relation_signature",
    "run",
    "symbol_unit_signature",
]
