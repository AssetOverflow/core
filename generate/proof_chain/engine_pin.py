"""Deductive-engine provenance pin (ADR-0218 §D4).

``DEDUCTIVE_ENGINE_PIN`` mirrors ``PINNED_SHAS["deductive_logic_v1"]`` in
``scripts/verify_lane_shas.py`` — the SHA-256 of the deductive lane report
produced by the engine build in force.  It is the value the P3 promoter
stamps into every ``PromotionCertificate`` (``engine_pin``) and the value
``VaultStore.apply_certified_promotion`` demands back via
``verify_certificate(..., expected_engine_pin=...)``.

Why a mirrored constant instead of reading the registry: ``scripts/`` is not
an importable runtime package, and the certificate module is deliberately
filesystem-free (PR B honesty boundary: pure replay cannot *know* the true
pin).  The sync is pinned by
``tests/test_adr_0218_proof_promotion.py::test_engine_pin_matches_lane_registry``,
which AST-parses the registry — drift between the two fails the suite.

When the deductive lane re-pins (an intentional engine change), update this
constant in the same commit.  Certificates built under the old pin then fail
apply-time pin verification — that is the desired alarm: an entailment proved
by a different engine build must be re-certified, not trusted across the
engine change.
"""

from __future__ import annotations

from typing import Final

DEDUCTIVE_ENGINE_PIN: Final[str] = (
    "97a230949016e38d5e3f37a69e4245b320575ee70e5af92ff7607f7b05f74b5f"
)
