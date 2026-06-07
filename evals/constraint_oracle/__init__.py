"""R2 constraint setup oracle (off-serving) — the independent ruler for the R2 organ.

Grades a comprehended :class:`ConstraintProblem` against independent gold by a span-free
canonical signature (``signature``), backed by a reviewable gold corpus (``r2_gold.jsonl``)
and a validation runner (``runner``). The R2 twin of ``evals.setup_oracle``. Imports no
``generate.derivation`` / ``core.reliability_gate`` — disjoint from the GSM8K serving path.
"""
