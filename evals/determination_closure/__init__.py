"""Determination-closure lane (Step D — CLOSE of the refined sequencing).

The falsification for "the loop learns from determined facts": idle consolidation
(``generate.determine.consolidate_once``) makes the engine's directly-answerable set
climb monotonically across idle ticks to the deductive-closure fixed point — with
wrong=0 (the member ∘ member fallacy is never derived), honesty (derived facts stay
SPECULATIVE), and a replayable provenance proof obligation.
"""

from evals.determination_closure.runner import (
    TickRecord,
    reverify_derived,
    run,
    seed_chain,
)

__all__ = ["TickRecord", "reverify_derived", "run", "seed_chain"]
