"""Industry-facing demos for CORE.

Each demo is a standalone script that makes exactly one falsifiable claim
no transformer-LLM wrapper can reproduce.  Run individually:

    python -m evals.industry_demos.demo_01_forward_constraint
    python -m evals.industry_demos.demo_02_geometry_drives_identity
    python -m evals.industry_demos.demo_03_deterministic_audit
    python -m evals.industry_demos.demo_04_exact_recall_scale

Or via the CLI:

    core demo forward-constraint
    core demo geometry-identity
    core demo deterministic-audit
    core demo exact-recall-scale

Each exits 0 on pass, 1 on fail, and prints structured evidence to stdout.
"""
