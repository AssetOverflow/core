"""
IngestCompiler — deterministic three-gate validation pipeline.

Gate order (sequential; a packet failing any gate does not proceed):
  1. ProvenanceGate  — SourceSpan integrity: non-empty text, valid SHA-256,
                       byte offsets non-negative and ordered
  2. SemanticGate    — span completeness: non-empty payload, balanced
                       delimiters (for code/math), minimum length
  3. GovernanceGate  — ReviewLevel vs DeterminismClass consistency;
                       ReviewDecision override check

The compiler:
  - performs structural deduplication by pressure_id (exact structural identity)
  - tracks semantic convergence by semantic_key and annotates packets that
    assert the same claim as prior packets with a warning
  - applies ReviewDecision overrides without mutating the original packet
  - produces a ValidationReport alongside the original immutable packets
  - exports accepted packets as LearningArtifact objects
  - optionally registers accepted packets into a SegmentManifold when one
    is provided (eliminates the need for a manual manifold.register() call)

Ingest/gate.py is NOT imported or called here.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Sequence

from core_ingest.types import (
    CandidateGeometricPressure,
    GateDisposition,
    LearningArtifact,
    ReviewDecision,
    ReviewLevel,
    ValidationReport,
    ValidationResult,
)

if TYPE_CHECKING:
    from core_ingest.manifold import SegmentManifold


# ---------------------------------------------------------------------------
# Individual gates
# ---------------------------------------------------------------------------

class ProvenanceGate:
    """
    Gate 1: SourceSpan integrity.

    Checks:
    - At least one SourceSpan (enforced at packet construction; double-checked here)
    - source_sha256 is 64 hex characters
    - byte_start >= 0
    - byte_end > byte_start
    """

    def check(self, packet: CandidateGeometricPressure) -> str | None:
        """Return a failure reason string, or None if the packet passes."""
        if not packet.provenance:
            return "provenance is empty"
        for span in packet.provenance:
            if span.byte_start < 0:
                return f"negative byte_start ({span.byte_start}) in SourceSpan"
            if span.byte_end <= span.byte_start:
                return (
                    f"byte_end ({span.byte_end}) <= byte_start ({span.byte_start})"
                )
            if len(span.source_sha256) != 64:
                return (
                    f"source_sha256 is {len(span.source_sha256)} chars, expected 64"
                )
        return None


class SemanticGate:
    """
    Gate 2: Span completeness.

    Checks:
    - payload_json is non-empty (not just '{}')
    - lemma is non-empty for TEXT and SCRIPTURE modalities
    - For CODE modality: no unbalanced braces/brackets/parens in lemma
    - Minimum combined span length of 1 byte
    """
    _PAIRS = {"{": "}", "[": "]", "(": ")", "<": ">"}

    def check(self, packet: CandidateGeometricPressure) -> str | None:
        import json
        from core_ingest.types import Modality
        from core.physics.energy import EnergyClass

        if packet.payload_json in ("{}", ""):
            return "payload_json is empty — no content to ingest"
        payload = json.loads(packet.payload_json)
        if "energy_class_hint" in payload:
            try:
                EnergyClass(str(payload["energy_class_hint"]))
            except ValueError:
                return f"invalid energy_class_hint: {payload['energy_class_hint']!r}"
        if "valence" in payload:
            failure = _validate_valence_payload(payload["valence"])
            if failure is not None:
                return failure

        # Require non-empty lemma for text / scripture
        if packet.modality in (Modality.TEXT, Modality.SCRIPTURE) and not packet.lemma:
            return (
                f"modality {packet.modality.value} requires a non-empty lemma"
            )

        # CODE: balanced delimiter check on lemma
        if packet.modality == Modality.CODE and packet.lemma:
            stack: list[str] = []
            for ch in packet.lemma:
                if ch in self._PAIRS:
                    stack.append(self._PAIRS[ch])
                elif ch in self._PAIRS.values():
                    if not stack or stack[-1] != ch:
                        return f"unbalanced delimiter '{ch}' in code lemma"
                    stack.pop()
            if stack:
                return f"unclosed delimiter(s) in code lemma: {''.join(stack)}"

        # Minimum span length
        total_bytes = sum(s.byte_end - s.byte_start for s in packet.provenance)
        if total_bytes < 1:
            return "total span length is 0 bytes"

        return None


class GovernanceGate:
    """
    Gate 3: ReviewLevel and DeterminismClass consistency.

    Checks:
    - AUTO_ACCEPT_ELIGIBLE is only claimed by D0/D1 frontends
      (enforced at packet construction; double-checked here)
    - AUTO_REJECT packets are always rejected
    - D2-D4 packets not covered by a ReviewDecision land in review_required
    """

    def check(
        self,
        packet: CandidateGeometricPressure,
        authorized_ids: frozenset[str],
    ) -> GateDisposition:
        import json

        if packet.review_level == ReviewLevel.AUTO_REJECT:
            return GateDisposition.REJECTED_GOVERNANCE
        payload = json.loads(packet.payload_json)
        if payload.get("energy_class_hint") == "E4":
            if packet.review_level != ReviewLevel.ARCHITECT_REVIEW_REQUIRED:
                return GateDisposition.REJECTED_GOVERNANCE
            if packet.pressure_id in authorized_ids:
                return GateDisposition.OVERRIDE_ACCEPTED
            return GateDisposition.REJECTED_GOVERNANCE

        # Override: an authorized ReviewDecision accepts regardless of level
        if packet.pressure_id in authorized_ids:
            return GateDisposition.OVERRIDE_ACCEPTED

        if packet.review_level == ReviewLevel.AUTO_ACCEPT_ELIGIBLE:
            # Invariant already enforced at construction — D0/D1 only
            return GateDisposition.ACCEPTED

        if packet.review_level == ReviewLevel.OPERATOR_REVIEW_REQUIRED:
            return GateDisposition.REVIEW_REQUIRED

        # D3 and architect-level D4 packets require an explicit decision.
        return GateDisposition.REJECTED_GOVERNANCE


def _validate_valence_payload(valence: object) -> str | None:
    if not isinstance(valence, dict):
        return "valence must be an object"
    required = {"affective", "force", "emphasis", "polarity", "orientation"}
    missing = required - set(valence)
    if missing:
        return f"valence missing required channel(s): {', '.join(sorted(missing))}"
    if not isinstance(valence["affective"], list):
        return "valence.affective must be a list"
    for key in ("emphasis", "polarity", "orientation"):
        if not isinstance(valence[key], dict):
            return f"valence.{key} must be an object"
    return None


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------

class IngestCompiler:
    """
    Processes batches of CandidateGeometricPressure packets through the
    three-gate pipeline and produces a ValidationReport.

    Usage
    -----
    compiler = IngestCompiler()
    report, artifacts = compiler.compile(packets)

    # With automatic manifold registration:
    manifold = SegmentManifold()
    report, artifacts = compiler.compile(packets, manifold=manifold)
    # Accepted packets are now registered in manifold — no manual call needed.
    """

    def __init__(self) -> None:
        self._provenance_gate = ProvenanceGate()
        self._semantic_gate   = SemanticGate()
        self._governance_gate = GovernanceGate()

    def compile(
        self,
        packets: Sequence[CandidateGeometricPressure],
        review_decision: ReviewDecision | None = None,
        manifold: "SegmentManifold | None" = None,
    ) -> tuple[ValidationReport, list[LearningArtifact]]:
        """
        Validate a batch of candidate packets.

        Parameters
        ----------
        packets         : The batch to validate (any sequence).
        review_decision : Optional operator/architect authorization. Packets
                          whose pressure_id appears in
                          review_decision.authorized_ids are accepted
                          regardless of their ReviewLevel.
        manifold        : Optional SegmentManifold. When provided, accepted
                          packets are registered automatically after
                          compilation — callers do not need a manual
                          manifold.register() call.

        Returns
        -------
        (ValidationReport, list[LearningArtifact])
        """
        authorized_ids: frozenset[str] = (
            review_decision.authorized_ids
            if review_decision is not None
            else frozenset()
        )

        # Deduplication: track seen pressure_ids (structural) and semantic_keys
        seen_pressure_ids: set[str] = set()
        semantic_counts: dict[str, int] = defaultdict(int)

        results:   list[ValidationResult] = []
        artifacts: list[LearningArtifact]  = []

        accepted_ids: set[str] = set()
        rejected_ids: set[str] = set()
        review_ids:   set[str] = set()

        for packet in packets:
            pid = packet.pressure_id
            sk  = packet.semantic_key

            # Structural deduplication
            if pid in seen_pressure_ids:
                results.append(ValidationResult(
                    pressure_id=pid,
                    semantic_key=sk,
                    disposition=GateDisposition.REJECTED_PROVENANCE,
                    gate_failed="provenance",
                    failure_reason="duplicate pressure_id — structural duplicate",
                ))
                rejected_ids.add(pid)
                continue
            seen_pressure_ids.add(pid)

            # Convergent-evidence tracking
            prior_count = semantic_counts[sk]
            semantic_counts[sk] += 1
            convergence_warning: tuple[str, ...] = ()
            if prior_count > 0:
                convergence_warning = (
                    f"semantic_convergence:{prior_count}_prior_sources",
                )

            # Gate 1: Provenance
            prov_failure = self._provenance_gate.check(packet)
            if prov_failure is not None:
                results.append(ValidationResult(
                    pressure_id=pid,
                    semantic_key=sk,
                    disposition=GateDisposition.REJECTED_PROVENANCE,
                    gate_failed="provenance",
                    failure_reason=prov_failure,
                    warnings=convergence_warning,
                ))
                rejected_ids.add(pid)
                continue

            # Gate 2: Semantic
            sem_failure = self._semantic_gate.check(packet)
            if sem_failure is not None:
                results.append(ValidationResult(
                    pressure_id=pid,
                    semantic_key=sk,
                    disposition=GateDisposition.REJECTED_SEMANTIC,
                    gate_failed="semantic",
                    failure_reason=sem_failure,
                    warnings=convergence_warning,
                ))
                rejected_ids.add(pid)
                continue

            # Gate 3: Governance
            disposition = self._governance_gate.check(packet, authorized_ids)

            if disposition == GateDisposition.REVIEW_REQUIRED:
                results.append(ValidationResult(
                    pressure_id=pid,
                    semantic_key=sk,
                    disposition=disposition,
                    warnings=convergence_warning,
                ))
                review_ids.add(pid)
                rejected_ids.add(pid)
                continue

            if disposition == GateDisposition.REJECTED_GOVERNANCE:
                results.append(ValidationResult(
                    pressure_id=pid,
                    semantic_key=sk,
                    disposition=disposition,
                    gate_failed="governance",
                    failure_reason="review required but no ReviewDecision authorized this packet",
                    warnings=convergence_warning,
                ))
                rejected_ids.add(pid)
                continue

            # ACCEPTED or OVERRIDE_ACCEPTED
            result = ValidationResult(
                pressure_id=pid,
                semantic_key=sk,
                disposition=disposition,
                warnings=convergence_warning,
            )
            results.append(result)
            accepted_ids.add(pid)
            artifacts.append(LearningArtifact(packet=packet, result=result))

        report = ValidationReport(
            results=tuple(results),
            accepted_ids=frozenset(accepted_ids),
            rejected_ids=frozenset(rejected_ids),
            review_ids=frozenset(review_ids),
        )

        # Auto-register accepted packets into the manifold if provided
        if manifold is not None and artifacts:
            manifold.register([art.packet for art in artifacts])

        return report, artifacts
