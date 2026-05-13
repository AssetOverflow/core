"""
Tests for core_ingest/ governance layer.

Covers:
  - CandidateGeometricPressure construction and invariants
  - content-addressing (pressure_id, semantic_key)
  - IngestCompiler three-gate pipeline
  - structural deduplication and convergent-evidence detection
  - ReviewDecision override path
  - StructuralSegmenter (prose, scripture, code, math)
  - SegmentManifold registration and lookup
"""

from __future__ import annotations

import hashlib
import json
import pytest

from core_ingest.types import (
    CandidateGeometricPressure,
    DeterminismClass,
    FrontendTrace,
    GateDisposition,
    LearningArtifact,
    Modality,
    ReviewDecision,
    ReviewLevel,
    SourceSpan,
)
from core_ingest.compiler import IngestCompiler
from core_ingest.segmenter import SegmentKind, StructuralSegmenter
from core_ingest.manifold import SegmentManifold


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


SOURCE_BYTES = b"In the beginning God created the heavens and the earth."
SOURCE_SHA   = _sha256(SOURCE_BYTES)


def make_span(
    start: int = 0,
    end: int   = 10,
    sha: str   = SOURCE_SHA,
    region: str | None = "body",
) -> SourceSpan:
    return SourceSpan(
        byte_start=start,
        byte_end=end,
        source_sha256=sha,
        region=region,
    )


def make_frontend(
    det: DeterminismClass = DeterminismClass.D0,
    iid: str = "StructuralSegmenter/prose/v1",
) -> FrontendTrace:
    return FrontendTrace(
        instrument_id=iid,
        determinism=det,
        version="1.0.0",
    )


def make_packet(
    review_level: ReviewLevel = ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
    det: DeterminismClass = DeterminismClass.D0,
    lemma: str = "beginning",
    payload: dict | None = None,
    kind: str = "assertion",
    modality: Modality = Modality.TEXT,
    span_start: int = 0,
    span_end: int = 10,
) -> CandidateGeometricPressure:
    return CandidateGeometricPressure(
        kind=kind,
        modality=modality,
        provenance=(make_span(span_start, span_end),),
        frontend=make_frontend(det),
        review_level=review_level,
        confidence=0.95,
        uncertainty=0.05,
        lemma=lemma,
        payload_json=json.dumps(payload or {"text": "In the beginning"}),
    )


# ---------------------------------------------------------------------------
# CandidateGeometricPressure
# ---------------------------------------------------------------------------

class TestCandidatePacket:

    def test_construction_d0(self):
        p = make_packet()
        assert p.pressure_id != ""
        assert p.semantic_key != ""
        assert len(p.pressure_id) == 64
        assert len(p.semantic_key) == 64

    def test_payload_normalized(self):
        # Unsorted keys should be canonicalized
        p = make_packet(payload={"z": 1, "a": 2})
        parsed = json.loads(p.payload_json)
        assert list(parsed.keys()) == sorted(parsed.keys())

    def test_same_claim_same_semantic_key(self):
        # Two packets with same semantic fields but different provenance
        p1 = make_packet(span_start=0, span_end=10)
        p2 = make_packet(span_start=20, span_end=30)
        assert p1.semantic_key == p2.semantic_key
        assert p1.pressure_id  != p2.pressure_id

    def test_governance_invariant_d3_cannot_claim_auto_accept(self):
        with pytest.raises(ValueError, match="AUTO_ACCEPT_ELIGIBLE"):
            make_packet(
                det=DeterminismClass.D3,
                review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(ValueError, match="confidence"):
            CandidateGeometricPressure(
                kind="assertion",
                modality=Modality.TEXT,
                provenance=(make_span(),),
                frontend=make_frontend(),
                review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
                confidence=1.5,
                uncertainty=0.0,
                lemma="test",
                payload_json='{"text": "test"}',
            )

    def test_empty_provenance_rejected(self):
        with pytest.raises(ValueError, match="provenance"):
            CandidateGeometricPressure(
                kind="assertion",
                modality=Modality.TEXT,
                provenance=(),
                frontend=make_frontend(),
                review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
                confidence=0.9,
                uncertainty=0.1,
                lemma="test",
                payload_json='{"text": "test"}',
            )

    def test_invalid_payload_json_rejected(self):
        with pytest.raises(ValueError, match="payload_json"):
            CandidateGeometricPressure(
                kind="assertion",
                modality=Modality.TEXT,
                provenance=(make_span(),),
                frontend=make_frontend(),
                review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
                confidence=0.9,
                uncertainty=0.1,
                lemma="test",
                payload_json="not valid json{",
            )


# ---------------------------------------------------------------------------
# IngestCompiler
# ---------------------------------------------------------------------------

class TestIngestCompiler:

    def setup_method(self):
        self.compiler = IngestCompiler()

    def test_d0_packet_accepted(self):
        p = make_packet()
        report, artifacts = self.compiler.compile([p])
        assert p.pressure_id in report.accepted_ids
        assert len(artifacts) == 1
        assert isinstance(artifacts[0], LearningArtifact)

    def test_d3_operator_review_required(self):
        p = make_packet(
            det=DeterminismClass.D3,
            review_level=ReviewLevel.OPERATOR_REVIEW_REQUIRED,
        )
        report, artifacts = self.compiler.compile([p])
        assert p.pressure_id in report.review_ids
        assert len(artifacts) == 0

    def test_auto_reject_always_rejected(self):
        p = make_packet(
            det=DeterminismClass.D0,
            review_level=ReviewLevel.AUTO_REJECT,
        )
        report, artifacts = self.compiler.compile([p])
        assert p.pressure_id in report.rejected_ids

    def test_structural_deduplication(self):
        p = make_packet()
        report, artifacts = self.compiler.compile([p, p])
        # First accepted, second rejected as duplicate
        assert len(report.accepted_ids) == 1
        assert len(report.rejected_ids) == 1

    def test_convergent_evidence_warning(self):
        # Two packets same semantic claim, different provenance
        p1 = make_packet(span_start=0,  span_end=10)
        p2 = make_packet(span_start=20, span_end=30)
        assert p1.semantic_key == p2.semantic_key
        report, _ = self.compiler.compile([p1, p2])
        # Second packet should carry a convergence warning
        result_p2 = next(r for r in report.results if r.pressure_id == p2.pressure_id)
        assert any("semantic_convergence" in w for w in result_p2.warnings)

    def test_review_decision_override(self):
        p = make_packet(
            det=DeterminismClass.D4,
            review_level=ReviewLevel.ARCHITECT_REVIEW_REQUIRED,
        )
        decision = ReviewDecision(
            authorized_ids=frozenset({p.pressure_id}),
            authorized_by="joshua.shay",
            reason="Manually reviewed and approved",
        )
        report, artifacts = self.compiler.compile([p], review_decision=decision)
        assert p.pressure_id in report.accepted_ids
        assert len(artifacts) == 1

    def test_acceptance_rate(self):
        p1 = make_packet(span_start=0,  span_end=10)
        p2 = make_packet(
            det=DeterminismClass.D4,
            review_level=ReviewLevel.OPERATOR_REVIEW_REQUIRED,
            span_start=20, span_end=30,
        )
        report, _ = self.compiler.compile([p1, p2])
        assert report.acceptance_rate == 0.5


# ---------------------------------------------------------------------------
# StructuralSegmenter
# ---------------------------------------------------------------------------

class TestStructuralSegmenter:

    def setup_method(self):
        self.seg = StructuralSegmenter()

    def test_prose_segments_non_empty(self):
        source = b"# Heading\n\nFirst paragraph.\n\nSecond paragraph."
        segments = self.seg.segment(source, modality_hint="prose")
        assert len(segments) >= 2

    def test_prose_heading_detected(self):
        source = b"# In the Beginning\n\nGod created the heavens."
        segments = self.seg.segment(source, modality_hint="prose")
        kinds = [s.kind for s in segments]
        assert SegmentKind.HEADING in kinds

    def test_scripture_verse_detected(self):
        source = b"Gen 1:1 In the beginning God created.\nGen 1:2 The earth was formless."
        segments = self.seg.segment(source, modality_hint="scripture")
        assert len(segments) >= 1
        for seg in segments:
            assert seg.kind == SegmentKind.VERSE
            assert "verse:" in seg.span.region

    def test_code_block_extracted(self):
        source = b"Some prose.\n\n```python\nprint('logos')\n```\n\nMore prose."
        segments = self.seg.segment(source, modality_hint="code")
        assert len(segments) == 1
        assert segments[0].kind == SegmentKind.CODE

    def test_math_env_extracted(self):
        source = rb"Let \[E = mc^2\] be the energy equation."
        segments = self.seg.segment(source, modality_hint="math")
        assert len(segments) == 1
        assert segments[0].kind == SegmentKind.MATH

    def test_span_byte_offsets_valid(self):
        source = b"# Title\n\nBody text here."
        for seg in self.seg.segment(source, modality_hint="prose"):
            assert seg.span.byte_start >= 0
            assert seg.span.byte_end > seg.span.byte_start
            assert seg.span.byte_end <= len(source)

    def test_source_sha256_consistent(self):
        source = b"Consistent source."
        expected_sha = _sha256(source)
        for seg in self.seg.segment(source, modality_hint="prose"):
            assert seg.span.source_sha256 == expected_sha


# ---------------------------------------------------------------------------
# SegmentManifold
# ---------------------------------------------------------------------------

class TestSegmentManifold:

    def test_register_and_lookup(self):
        manifold = SegmentManifold()
        p = make_packet()
        manifold.register([p])
        entries = manifold.lookup(p.semantic_key)
        assert len(entries) == 1
        assert entries[0].pressure_id == p.pressure_id

    def test_spans_for_returns_all_spans(self):
        manifold = SegmentManifold()
        p1 = make_packet(span_start=0,  span_end=10)
        p2 = make_packet(span_start=20, span_end=30)
        # Same semantic_key — different structural identity
        assert p1.semantic_key == p2.semantic_key
        manifold.register([p1, p2])
        spans = manifold.spans_for(p1.semantic_key)
        assert len(spans) == 2

    def test_len(self):
        manifold = SegmentManifold()
        p1 = make_packet(span_start=0,  span_end=10)
        p2 = make_packet(span_start=20, span_end=30, lemma="earth")
        manifold.register([p1, p2])
        # p1 and p2 have different semantic keys (different lemma)
        assert len(manifold) == 2

    def test_contains(self):
        manifold = SegmentManifold()
        p = make_packet()
        assert p.semantic_key not in manifold
        manifold.register([p])
        assert p.semantic_key in manifold

    def test_lookup_missing_key(self):
        manifold = SegmentManifold()
        assert manifold.lookup("nonexistent_key") == []
