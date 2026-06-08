"""Combined-rate setup oracle (off-serving) — the independent ruler for the combined-rate organ.

Grades a comprehended ``CombinedRateProblem`` against independent gold by a span-free canonical
signature (``signature``), backed by a reviewable gold corpus (``combined_rate_gold.jsonl``) and a
validation runner (``runner``). The CMB twin of ``evals.rate_oracle`` / ``evals.constraint_oracle``.
Imports no ``generate.derivation`` / ``core.reliability_gate`` — disjoint from the GSM8K serving
path. CMB-a ships the ruler only; the reader grading lane lands with the reader (CMB-c).
"""
