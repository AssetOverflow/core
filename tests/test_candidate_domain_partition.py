"""Tests for W2-C — candidate domain partition."""

from __future__ import annotations

import subprocess
from pathlib import Path
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


def test_existing_cognition_tests_untouched():
    """Assert zero modifications to pre-existing cognition test files."""
    # Find modified or untracked test files in git status
    result = subprocess.run(
        ["git", "status", "--porcelain", "tests/"],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    # Allowlist of new/modified test files contributed by ADR-0167 PRs.
    # Future ADR-0167 PRs append their own file here so this regression net
    # stays meaningful as the wave progresses.
    allowed = {
        "test_candidate_domain_partition.py",  # W2-C
        "test_math_evidence_e2e.py",  # W3-A
        # Fix PR — wrong=0 hazard regression (recognizer skip-only fallback).
        # Modifies test_math_candidate_graph.py and test_teaching_audit.py;
        # adds test_recognizer_skip_wrong_zero.py.  See ADR-0167-FOLLOWUPS §2
        # for the architectural fix that would retire this allowlist.
        "test_math_candidate_graph.py",
        "test_teaching_audit.py",
        "test_recognizer_skip_wrong_zero.py",
    }
    for line in lines:
        path = line.split()[-1]
        assert Path(path).name in allowed, (
            f"unexpected new/modified test file: {path}"
        )
