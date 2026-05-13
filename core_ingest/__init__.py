"""
core_ingest — Universal input-to-pressure boundary.

The sole job of this package is converting external information from any
source into CORE-native pressure: typed, content-addressed, provenance-
anchored candidate packets that can be validated and, if accepted, exported
as LearningArtifact objects for the train/ layer.

Two paths:
  runtime  — transient working pressure for active cognition
             (short-circuit: bypasses governance, feeds ingest/gate.py directly)
  durable  — validated candidate pressure for learning and update paths
             (full three-gate IngestCompiler pipeline)

The gate (ingest/gate.py) is NEVER imported or modified from this package.
This package is upstream of the gate, not a replacement for it.

Typical usage (durable path via IngestPipeline)
-----------------------------------------------
    from core_ingest import IngestPipeline, SegmentManifold

    manifold = SegmentManifold()
    pipeline = IngestPipeline(manifold=manifold)

    report, artifacts = pipeline.run(
        source=b"In the beginning was the Word...",
        modality_hint="prose",
    )

    # Reconstruction: recover provenance spans for any vault recall hit
    spans = manifold.spans_for(artifacts[0].packet.semantic_key)

Direct compiler usage (when you already have candidate packets)
---------------------------------------------------------------
    from core_ingest import IngestCompiler, SegmentManifold

    manifold  = SegmentManifold()
    compiler  = IngestCompiler()
    report, artifacts = compiler.compile(packets, manifold=manifold)
"""

from core_ingest.types import (
    Modality,
    DeterminismClass,
    ReviewLevel,
    SourceSpan,
    FrontendTrace,
    CandidateGeometricPressure,
    GateDisposition,
    ValidationResult,
    ValidationReport,
    LearningArtifact,
    ReviewDecision,
)
from core_ingest.pressure import make_pressure_id, make_semantic_key
from core_ingest.compiler import IngestCompiler
from core_ingest.segmenter import Segment, SegmentKind, StructuralSegmenter
from core_ingest.manifold import ManifoldEntry, SegmentManifold
from core_ingest.pipeline import IngestPipeline, IngestPipelineConfig

__all__ = [
    # types
    "Modality",
    "DeterminismClass",
    "ReviewLevel",
    "SourceSpan",
    "FrontendTrace",
    "CandidateGeometricPressure",
    "GateDisposition",
    "ValidationResult",
    "ValidationReport",
    "LearningArtifact",
    "ReviewDecision",
    # pressure addressing
    "make_pressure_id",
    "make_semantic_key",
    # compiler
    "IngestCompiler",
    # segmenter
    "Segment",
    "SegmentKind",
    "StructuralSegmenter",
    # manifold index
    "ManifoldEntry",
    "SegmentManifold",
    # pipeline
    "IngestPipeline",
    "IngestPipelineConfig",
]
