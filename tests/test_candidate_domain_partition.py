"""Tests for W2-C — candidate domain partition."""

from __future__ import annotations

from typing import Any

from core.protocol import canonical_bytes
from teaching.discovery import DiscoveryCandidate


def _candidate(*, domain: str | None = None) -> DiscoveryCandidate:
    kwargs: dict[str, Any] = {
        "candidate_id": "cand_1",
        "proposed_chain": {
            "subject": "wisdom",
            "intent": "cause",
            "connective": None,
            "object": None,
        },
        "trigger": "would_have_grounded",
        "source_turn_trace": "t1",
        "pack_consistent": True,
        "boundary_clean": True,
    }
    if domain is not None:
        kwargs["domain"] = domain
    return DiscoveryCandidate(**kwargs)


def test_default_domain_is_cognition():
    """Bare DiscoveryCandidate has domain == 'cognition'."""
    cand = _candidate()
    assert cand.domain == "cognition"



def test_math_domain_can_be_set():
    """Explicit domain='math' constructs successfully."""
    cand = _candidate(domain="math")
    assert cand.domain == "math"



def test_round_trip_preserves_domain():
    """Serialization/deserialization preserves the domain field."""
    # Cognition domain
    cand_cog = _candidate(domain="cognition")
    dict_cog = cand_cog.as_dict()
    assert "domain" not in dict_cog  # Omitted to preserve legacy keys
    roundtrip_cog = DiscoveryCandidate.from_dict(dict_cog)
    assert roundtrip_cog.domain == "cognition"

    # Math domain
    cand_math = _candidate(domain="math")
    dict_math = cand_math.as_dict()
    assert dict_math["domain"] == "math"  # Included for math
    roundtrip_math = DiscoveryCandidate.from_dict(dict_math)
    assert roundtrip_math.domain == "math"



def test_canonical_bytes_includes_domain_deterministically():
    """Same domain value -> same canonical bytes contribution."""
    cand_math_1 = _candidate(domain="math")
    cand_math_2 = _candidate(domain="math")
    bytes_1 = canonical_bytes(cand_math_1)
    bytes_2 = canonical_bytes(cand_math_2)
    assert bytes_1 == bytes_2

    cand_cog = _candidate(domain="cognition")
    bytes_cog = canonical_bytes(cand_cog)
    assert bytes_cog != bytes_1
    assert b'"domain":"math"' in bytes_1
    assert b'"domain":"cognition"' in bytes_cog



def test_domain_partition_is_behavioral_not_git_state():
    """Partition invariants are enforced by serialized behavior, not git diff state."""
    cognition = _candidate(domain="cognition")
    math = _candidate(domain="math")

    cognition_dict = cognition.as_dict()
    math_dict = math.as_dict()

    # Legacy cognition payloads remain structurally unchanged.
    assert "domain" not in cognition_dict

    # Non-cognition candidates must carry explicit discrimination.
    assert math_dict["domain"] == "math"

    # The canonical protocol surface distinguishes the domains.
    assert canonical_bytes(cognition) != canonical_bytes(math)
