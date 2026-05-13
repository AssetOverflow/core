"""
tests/test_manifold.py

Full coverage for core_ingest.manifold.SegmentManifold.

Covers:
  - register → lookup → spans_for round-trip
  - multi-key isolation
  - append-only semantics (re-registering does not overwrite)
  - __len__ and __contains__
  - empty lookup returns empty list, not an error
"""

import hashlib
import json
import pytest

from core_ingest.manifold import ManifoldEntry, SegmentManifold
from core_ingest.types import (
    CandidateGeometricPressure,
    DeterminismClass,
    FrontendTrace,
    Modality,
    ReviewLevel,
    SourceSpan,
)


def _sha(src: bytes = b"source") -> str:
    return hashlib.sha256(src).hexdigest()


def _span(start=0, end=10) -> SourceSpan:
    return SourceSpan(byte_start=start, byte_end=end, source_sha256=_sha())


def _frontend() -> FrontendTrace:
    return FrontendTrace(
        instrument_id="TestInstrument/v1",
        determinism=DeterminismClass.D0,
        version="1.0.0",
    )


def _packet(text: str = "the word", start: int = 0) -> CandidateGeometricPressure:
    payload = json.dumps({"text": text}, sort_keys=True, separators=(",", ":"))
    return CandidateGeometricPressure(
        kind="assertion",
        modality=Modality.TEXT,
        provenance=(_span(start, start + len(text.encode())),),
        frontend=_frontend(),
        review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
        confidence=1.0,
        uncertainty=0.0,
        lemma=text[:64],
        payload_json=payload,
    )


@pytest.fixture
def manifold() -> SegmentManifold:
    return SegmentManifold()


class TestRegisterLookup:
    def test_register_and_lookup(self, manifold):
        p = _packet("logos")
        manifold.register([p])
        entries = manifold.lookup(p.semantic_key)
        assert len(entries) == 1
        assert isinstance(entries[0], ManifoldEntry)
        assert entries[0].semantic_key == p.semantic_key
        assert entries[0].pressure_id == p.pressure_id

    def test_spans_for_returns_correct_spans(self, manifold):
        p = _packet("ruach")
        manifold.register([p])
        spans = manifold.spans_for(p.semantic_key)
        assert len(spans) == 1
        assert spans[0] == p.provenance[0]

    def test_empty_lookup_returns_empty_list(self, manifold):
        result = manifold.lookup("nonexistent_key")
        assert result == []

    def test_empty_spans_for_returns_empty_list(self, manifold):
        result = manifold.spans_for("nonexistent_key")
        assert result == []


class TestMultiKey:
    def test_two_different_keys_isolated(self, manifold):
        p1 = _packet("logos", start=0)
        p2 = _packet("ruach", start=0)
        manifold.register([p1, p2])
        assert len(manifold) == 2
        assert p1.semantic_key in manifold
        assert p2.semantic_key in manifold
        # Keys should be different
        assert p1.semantic_key != p2.semantic_key
        # Each key returns only its own spans
        assert manifold.spans_for(p1.semantic_key)[0] == p1.provenance[0]
        assert manifold.spans_for(p2.semantic_key)[0] == p2.provenance[0]


class TestAppendOnly:
    def test_re_register_appends_not_overwrites(self, manifold):
        """Registering the same semantic_key twice accumulates entries."""
        src_a = b"document A"
        src_b = b"document B"
        p1 = CandidateGeometricPressure(
            kind="assertion",
            modality=Modality.TEXT,
            provenance=(SourceSpan(0, 5, hashlib.sha256(src_a).hexdigest()),),
            frontend=_frontend(),
            review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
            confidence=1.0,
            uncertainty=0.0,
            lemma="logos",
            payload_json=json.dumps({"text": "logos"}, sort_keys=True, separators=(",", ":")),
        )
        p2 = CandidateGeometricPressure(
            kind="assertion",
            modality=Modality.TEXT,
            provenance=(SourceSpan(0, 5, hashlib.sha256(src_b).hexdigest()),),
            frontend=_frontend(),
            review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
            confidence=1.0,
            uncertainty=0.0,
            lemma="logos",
            payload_json=json.dumps({"text": "logos"}, sort_keys=True, separators=(",", ":")),
        )
        # Same semantic_key (same lemma+payload), different provenance
        assert p1.semantic_key == p2.semantic_key
        manifold.register([p1])
        manifold.register([p2])
        entries = manifold.lookup(p1.semantic_key)
        assert len(entries) == 2
        spans = manifold.spans_for(p1.semantic_key)
        assert len(spans) == 2


class TestContainsLen:
    def test_len_increments(self, manifold):
        assert len(manifold) == 0
        manifold.register([_packet("first")])
        assert len(manifold) == 1
        manifold.register([_packet("second")])
        assert len(manifold) == 2

    def test_contains_registered_key(self, manifold):
        p = _packet("dabar")
        manifold.register([p])
        assert p.semantic_key in manifold

    def test_not_contains_unknown_key(self, manifold):
        assert "not_a_real_key" not in manifold
