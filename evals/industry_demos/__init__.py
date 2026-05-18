"""Industry-facing demos for CORE — ADR-0046.

Each demo is a standalone script that makes exactly one falsifiable claim
no transformer-LLM wrapper can reproduce.  Run individually:

    python -m evals.industry_demos.demo_01_forward_constraint
    python -m evals.industry_demos.demo_02_geometry_drives_identity
    python -m evals.industry_demos.demo_03_deterministic_audit

Each exits 0 on pass, 1 on fail, and prints structured JSON evidence
to stdout.

The exact-recall-at-scale claim (CGA vault recall at N up to 100k) is
covered by ADR-0045 — measured on the actual vault path, with properly
constructed versors — and is not duplicated here under a weaker
construction.  See ADR-0046, "Industry Demo Suite", for the rationale.
"""
