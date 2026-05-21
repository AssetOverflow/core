"""Industry-facing demos for CORE — ADR-0046.

Each demo is a standalone script that makes exactly one falsifiable claim
no transformer-LLM wrapper can reproduce.  Run individually:

    python -m evals.industry_demos.demo_01_forward_constraint
    python -m evals.industry_demos.demo_02_geometry_drives_identity
    python -m evals.industry_demos.demo_03_deterministic_audit

Or run the full suite via the suite runner:

    python -m evals.industry_demos.run_all

Each individual demo exits 0 on pass, 1 on fail, and prints structured
JSON evidence to stdout.  The suite runner exits 0 iff all three pass
and emits a final machine-readable JSON summary for CI consumption.

Demos
-----
demo_01_forward_constraint
    Claim: PropositionGraph constrains the generation walk via CGA
    geometry (not a prompt filter or keyword list) BEFORE any tokens
    are produced.  Evidence: allowed_indices < vocab_size; every index
    scores positive cga_inner against at least one named node versor;
    region label encodes the graph root node ID.

demo_02_geometry_drives_identity
    Claim: Swapping identity pack (precision_first_v1 vs
    generosity_first_v1) changes the manifold's alignment_threshold
    geometrically — not via a system prompt, different model, or
    temperature setting.  Evidence: threshold_p (0.55) ≠ threshold_g
    (0.40); identity_score.alignment ordered precision ≤ generosity
    on the same input.

demo_03_deterministic_audit
    Claim: Three independent ChatRuntime instances on the same input
    produce byte-identical JSONL audit records for the seven
    architecturally-determined fields (versor_condition, vault_hits,
    dialogue_role, stub_path, safety_upheld, ethics_upheld, flagged).
    This is structural determinism, not seeded randomness.

The exact-recall-at-scale claim (CGA vault recall at N up to 100k) is
covered by ADR-0045 — measured on the actual vault path with properly
constructed versors — and is not duplicated here under a weaker
construction.  See ADR-0046, "Industry Demo Suite", for the rationale.
"""
