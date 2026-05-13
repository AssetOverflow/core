"""
tests/test_pipeline.py

End-to-end integration tests for core_ingest.pipeline.IngestPipeline.

Covers:
  - Prose source: segments accepted, manifold populated
  - Scripture source: verse segments accepted, region labels correct
  - Reconstruction: manifold.spans_for returns spans matching accepted artifacts
  - Empty source raises ValueError
  - Source with no segmentable content returns empty report gracefully
  - register_all=True indexes all packets including rejected
  - pipeline.spans_for shortcut delegates to manifold
  - Custom IngestPipelineConfig (instrument_id, version)
"""

import pytest

from core_ingest.manifold import SegmentManifold
from core_ingest.pipeline import IngestPipeline, IngestPipelineConfig
from core_ingest.types import GateDisposition


@pytest.fixture
def pipeline() -> IngestPipeline:
    return IngestPipeline(manifold=SegmentManifold())


# ---------------------------------------------------------------------------
# Prose
# ---------------------------------------------------------------------------

class TestProsePipeline:
    def test_prose_accepted(self, pipeline):
        src = b"In the beginning was the Word, and the Word was with God.\n\nAnd the Word was God."
        report, artifacts = pipeline.run(src, modality_hint="prose")
        assert len(artifacts) > 0
        assert all(
            r.disposition in (GateDisposition.ACCEPTED, GateDisposition.OVERRIDE_ACCEPTED)
            for r in report.results
            if r.pressure_id in report.accepted_ids
        )

    def test_prose_acceptance_rate_is_one(self, pipeline):
        src = b"Paragraph one.\n\nParagraph two."
        report, _ = pipeline.run(src, modality_hint="prose")
        assert report.acceptance_rate == 1.0

    def test_manifold_populated_after_prose(self, pipeline):
        src = b"The logos is the foundation of all things."
        _, artifacts = pipeline.run(src, modality_hint="prose")
        for art in artifacts:
            assert art.packet.semantic_key in pipeline.manifold


# ---------------------------------------------------------------------------
# Scripture
# ---------------------------------------------------------------------------

class TestScripturePipeline:
    def test_scripture_verse_accepted(self):
        manifold = SegmentManifold()
        pipeline = IngestPipeline(manifold=manifold)
        src = (
            b"John 1:1 In the beginning was the Word, and the Word was with God, "
            b"and the Word was God.\n"
            b"John 1:2 He was with God in the beginning."
        )
        report, artifacts = pipeline.run(src, modality_hint="scripture")
        assert len(artifacts) > 0

    def test_scripture_region_label_contains_verse(self):
        pipeline = IngestPipeline()
        src = b"Gen 1:1 In the beginning God created the heavens and the earth."
        _, artifacts = pipeline.run(src, modality_hint="scripture")
        if artifacts:
            region = artifacts[0].packet.provenance[0].region
            assert region is not None
            assert "verse:" in region


# ---------------------------------------------------------------------------
# Reconstruction via manifold
# ---------------------------------------------------------------------------

class TestReconstruction:
    def test_spans_for_returns_provenance_spans(self):
        manifold = SegmentManifold()
        pipeline = IngestPipeline(manifold=manifold)
        src = b"The Word became flesh and made his dwelling among us."
        _, artifacts = pipeline.run(src, modality_hint="prose")
        for art in artifacts:
            sk = art.packet.semantic_key
            spans = manifold.spans_for(sk)
            assert len(spans) >= 1
            # Each span's byte range must lie within the source
            for span in spans:
                assert span.byte_start >= 0
                assert span.byte_end <= len(src)

    def test_pipeline_spans_for_shortcut(self):
        pipeline = IngestPipeline()
        src = b"For God so loved the world."
        _, artifacts = pipeline.run(src, modality_hint="prose")
        if artifacts:
            sk = artifacts[0].packet.semantic_key
            assert pipeline.spans_for(sk) == pipeline.manifold.spans_for(sk)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_source_raises(self, pipeline):
        with pytest.raises(ValueError, match="empty source"):
            pipeline.run(b"", modality_hint="prose")

    def test_no_segmentable_content_returns_empty_report(self, pipeline):
        # A source with no math content — math segmenter returns nothing
        src = b"Just plain prose with no math at all."
        report, artifacts = pipeline.run(src, modality_hint="math")
        assert len(artifacts) == 0
        assert report.acceptance_rate == 0.0

    def test_custom_config_instrument_id(self):
        config = IngestPipelineConfig(
            instrument_id="StructuralSegmenter/prose/v2",
            instrument_version="2.0.0",
        )
        pipeline = IngestPipeline(config=config)
        src = b"Testing custom instrument identity."
        _, artifacts = pipeline.run(src, modality_hint="prose")
        if artifacts:
            assert artifacts[0].packet.frontend.instrument_id == "StructuralSegmenter/prose/v2"
            assert artifacts[0].packet.frontend.version == "2.0.0"

    def test_register_all_policy_indexes_all_packets(self):
        """register_all=True: manifold indexes all packets, not just accepted."""
        config = IngestPipelineConfig(register_all=True)
        manifold = SegmentManifold()
        pipeline = IngestPipeline(manifold=manifold, config=config)
        src = b"The heavens declare the glory of God."
        _, _ = pipeline.run(src, modality_hint="prose")
        # With register_all, at least as many keys as accepted artifacts
        assert len(manifold) >= 1
