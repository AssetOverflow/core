"""
IngestPipeline — end-to-end input-to-pressure pipeline.

Wires the three CORE-ingest subsystems into a single deterministic call:

  StructuralSegmenter  (D0 form-boundary carving)
        ↓
  CandidateGeometricPressure construction  (typed evidence envelope)
        ↓
  IngestCompiler  (three-gate validation: Provenance → Semantic → Governance)
        ↓
  SegmentManifold  (append-only reconstruction index)

The pipeline operates on raw source bytes and a modality hint.  It never
interprets meaning — that stays inside the versor field.  It only carves,
wraps, validates, and indexes.

Design constraints
------------------
- All instruments are D0: fully deterministic given the same source bytes.
- No LLM, no external API, no nondeterministic component is in this path.
- The SegmentManifold is updated atomically after compilation; a failed
  compile() call leaves the manifold unchanged for that batch.
- ingest/gate.py is never imported or called here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from core_ingest.compiler import IngestCompiler
from core_ingest.manifold import SegmentManifold
from core_ingest.segmenter import Segment, SegmentKind, StructuralSegmenter
from core_ingest.types import (
    CandidateGeometricPressure,
    DeterminismClass,
    FrontendTrace,
    LearningArtifact,
    Modality,
    ReviewDecision,
    ReviewLevel,
    SourceSpan,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Modality hint → Modality enum + segmenter hint
# ---------------------------------------------------------------------------

_HINT_TO_MODALITY: dict[str, Modality] = {
    "prose":     Modality.TEXT,
    "scripture": Modality.SCRIPTURE,
    "code":      Modality.CODE,
    "math":      Modality.MATH,
}

_HINT_TO_KIND: dict[str, str] = {
    "prose":     "assertion",
    "scripture": "verse",
    "code":      "definition",
    "math":      "theorem",
}


# ---------------------------------------------------------------------------
# Segment → CandidateGeometricPressure
# ---------------------------------------------------------------------------

def _segment_to_candidate(
    segment:    Segment,
    modality:   Modality,
    kind:       str,
    instrument: FrontendTrace,
) -> CandidateGeometricPressure:
    """
    Lift a Segment into a CandidateGeometricPressure envelope.

    The lemma is set to the first 256 characters of the segment text
    (sufficient for semantic key computation; not an interpretation).
    The payload carries the structural metadata: kind, region, text.
    SVO fields are left empty — structural segmentation does not assert
    subject/verb/object triples.  That is the field's job.
    """
    lemma = segment.text[:256].strip()
    payload = json.dumps(
        {
            "kind":   kind,
            "region": segment.span.region or "",
            "text":   segment.text,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return CandidateGeometricPressure(
        kind=kind,
        modality=modality,
        provenance=(segment.span,),
        frontend=instrument,
        review_level=ReviewLevel.AUTO_ACCEPT_ELIGIBLE,
        confidence=1.0,
        uncertainty=0.0,
        lemma=lemma,
        subject="",
        verb="",
        object_="",
        payload_json=payload,
    )


# ---------------------------------------------------------------------------
# IngestPipeline
# ---------------------------------------------------------------------------

@dataclass
class IngestPipelineConfig:
    """
    Configuration for IngestPipeline.

    instrument_id   — stable identifier for the segmenter instrument;
                      should include modality and version, e.g.
                      'StructuralSegmenter/prose/v1'
    instrument_version — semantic version string
    register_all    — if True, register ALL packets (including rejected)
                      into the manifold; default is accepted-only
    """
    instrument_id:      str = "StructuralSegmenter/v1"
    instrument_version: str = "1.0.0"
    register_all:       bool = False


class IngestPipeline:
    """
    End-to-end StructuralSegmenter → IngestCompiler → SegmentManifold pipeline.

    Usage
    -----
    manifold = SegmentManifold()
    pipeline = IngestPipeline(manifold=manifold)

    report, artifacts = pipeline.run(
        source=source_bytes,
        modality_hint="prose",          # 'prose' | 'scripture' | 'code' | 'math'
    )

    # Reconstruction: given a vault recall hit on a semantic_key,
    # recover all provenance spans in the original source documents.
    spans = manifold.spans_for(semantic_key)

    Parameters
    ----------
    manifold : SegmentManifold
        The shared reconstruction index.  Updated atomically after each
        successful compile() call.
    config   : IngestPipelineConfig (optional)
        Instrument identity and registration policy.
    """

    def __init__(
        self,
        manifold: SegmentManifold | None = None,
        config:   IngestPipelineConfig | None = None,
    ) -> None:
        self._manifold  = manifold or SegmentManifold()
        self._config    = config or IngestPipelineConfig()
        self._segmenter = StructuralSegmenter()
        self._compiler  = IngestCompiler()

        # D0 instrument: fully deterministic given same source bytes
        self._instrument = FrontendTrace(
            instrument_id=self._config.instrument_id,
            determinism=DeterminismClass.D0,
            version=self._config.instrument_version,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        source:         bytes,
        modality_hint:  str = "prose",
        review_decision: ReviewDecision | None = None,
    ) -> tuple[ValidationReport, list[LearningArtifact]]:
        """
        Run the full ingest pipeline on `source`.

        Parameters
        ----------
        source          : Raw source bytes (UTF-8 expected).
        modality_hint   : Structural mode — 'prose' | 'scripture' | 'code' | 'math'.
        review_decision : Optional operator/architect authorization for
                          packets requiring review.

        Returns
        -------
        (ValidationReport, list[LearningArtifact])

        The SegmentManifold is updated atomically after compilation.
        """
        if not source:
            raise ValueError(
                "IngestPipeline.run() received empty source bytes. "
                "Nothing to segment."
            )

        modality = _HINT_TO_MODALITY.get(modality_hint, Modality.TEXT)
        kind     = _HINT_TO_KIND.get(modality_hint, "assertion")

        # Stage 1: Structural segmentation (D0 — deterministic, form-only)
        segments: list[Segment] = self._segmenter.segment(
            source, modality_hint=modality_hint
        )

        # Stage 2: Lift segments into typed evidence envelopes
        candidates: list[CandidateGeometricPressure] = [
            _segment_to_candidate(seg, modality, kind, self._instrument)
            for seg in segments
            if seg.text.strip()  # skip whitespace-only segments
        ]

        if not candidates:
            # Source had no segmentable content for this modality.
            # Return an empty report rather than raising.
            from core_ingest.types import ValidationReport
            report = ValidationReport(
                results=(),
                accepted_ids=frozenset(),
                rejected_ids=frozenset(),
                review_ids=frozenset(),
            )
            return report, []

        # Stage 3: Three-gate validation
        report, artifacts = self._compiler.compile(
            candidates,
            review_decision=review_decision,
        )

        # Stage 4: Register into the reconstruction manifold
        if self._config.register_all:
            self._manifold.register(candidates)
        else:
            # Register only accepted packets — policy: reconstruction is
            # only meaningful for evidence that cleared governance.
            accepted_packets = [
                art.packet for art in artifacts
            ]
            if accepted_packets:
                self._manifold.register(accepted_packets)

        return report, artifacts

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def manifold(self) -> SegmentManifold:
        """The shared reconstruction index."""
        return self._manifold

    def spans_for(self, semantic_key: str):
        """Shortcut: manifold.spans_for(semantic_key)."""
        return self._manifold.spans_for(semantic_key)
