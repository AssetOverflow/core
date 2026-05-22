"""ADR-0098 Demo Composition Contract.

This package houses the typed :class:`DemoCommand` protocol plus thin
adapters that wrap the existing in-tree demo entry points. Adapters
exist so the showcase composer (ADR-0099) can read demo results
through one stable type rather than special-casing each tour.

Adapters never change demo behavior. They wrap the underlying
``run_tour()`` / ``run_demo()`` entry points and translate the
returned dict into a typed :class:`DemoResult`.
"""

from .contract import (
    CLAIM_CONTRACT_VERSION,
    Claim,
    DemoCommand,
    DemoContractError,
    DemoResult,
    canonical_json,
    verify_no_global_state_mutation,
)

__all__ = [
    "CLAIM_CONTRACT_VERSION",
    "Claim",
    "DemoCommand",
    "DemoContractError",
    "DemoResult",
    "canonical_json",
    "verify_no_global_state_mutation",
]
