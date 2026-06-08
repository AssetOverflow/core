"""R3 rate setup oracle (off-serving) — the independent ruler for the single-rate organ.

Grades a comprehended ``RateProblem`` against independent gold by a span-free canonical signature
(``signature``), backed by a reviewable gold corpus (``rate_gold.jsonl``) and a validation runner
(``runner``). The R3 twin of ``evals.constraint_oracle``. Imports no ``generate.derivation`` /
``core.reliability_gate`` — disjoint from the GSM8K serving path.
"""
