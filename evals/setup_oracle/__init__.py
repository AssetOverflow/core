"""Setup-oracle lane — grade the READING (the semantic setup), not the answer.

The relational_metric lane scores answers: `comprehend → project → oracle_answer →
compare gold integer`. That hides a hazard the held-out measurements exposed — a WRONG
reading can produce a coincidentally-correct number and still pass. The setup-oracle
closes that gap: it compares the reader's comprehended STRUCTURE (the relations it read
+ the BoundUnknown question target it emitted) against the INDEPENDENT gold structure
(the relational_metric cases' own `relations`/`query`, authored separately from the
binding-graph reader). A wrong setup is a first-class failure even when its answer is right.

`setup_wrong` is the load-bearing, wrong=0-critical count: a reading that misrepresents
the problem. The R1 answer lane (PR-6b) runs only after setup is correct; unsupported
fixtures remain refusals and setup-wrong fixtures are never answer-scored.
"""

from evals.setup_oracle.runner import run, run_r1, run_r1_answers
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
    "run_r1",
    "run_r1_answers",
    "symbol_unit_signature",
]
