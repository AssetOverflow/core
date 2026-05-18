"""Lab evaluation environment for AssetOverflow/core.

This package contains deep-trace evals, identity configuration explorers,
and teaching layer probes.  Nothing here mutates packs, manifolds, or any
durable geometry.  Every eval runs in an isolated in-process VaultStore
that evaporates at end of process.

Run individually:
    python -m evals.lab.teaching_trace
    python -m evals.lab.identity_config_explorer
    python -m evals.lab.teaching_contradiction_probe
    python -m evals.lab.vault_epistemic_trace
"""
