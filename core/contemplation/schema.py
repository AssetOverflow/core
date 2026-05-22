from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from teaching.epistemic import EpistemicStatus


@unique
class FindingKind(Enum):
    """Kinds of read-only contemplation findings.

    These are diagnostic/curricular signals, not learned truths.
    """

    COVERAGE_GAP = "coverage_gap"
    CONTRADICTION = "contradiction"
    WEAK_SURFACE = "weak_surface"
    UNPROVED_RELATION = "unproved_relation"
    DERIVABLE_RELATION = "derivable_relation"
    BENCHMARK_CASE = "benchmark_case"
    OOV_GAP = "oov_gap"
    PLANNER_GAP = "planner_gap"
    PACK_MUTATION_CANDIDATE = "pack_mutation_candidate"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_16(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]


# BOUNDARY (vs teaching/discovery.py:EvidencePointer)
# ---------------------------------------------------------------------------
# ``EvidencePointer`` (teaching/discovery.py) and ``ContemplationEvidenceRef``
# below intentionally remain separate types.  They have *different
# semantics*, not just different shapes:
#
#   - ``EvidencePointer.source`` is constrained to
#     ``{corpus, pack, vault_coherent}`` — pointers into reviewed
#     in-process memory the runtime trusts as grounding.
#   - ``ContemplationEvidenceRef.source_type`` is free-form because
#     it points at external artifacts (benchmark report files,
#     evaluator output, lab measurements) that have not been
#     reviewed by the teaching pipeline.
#
# Converging them would either widen the runtime-grounding source
# enum (a real loss — losing the "this came from reviewed memory"
# guarantee) or force benchmark reports to masquerade as
# ``vault_coherent``.  Both are worse than keeping the two types
# separate and documented.
#
# What IS shared:
#   - ``EpistemicStatus`` (one source of truth at teaching/epistemic.py).
#   - Sink plumbing (DiscoveryCandidateSink protocol) — see
#     ``core/contemplation/sink.py``.
#   - Append-only monthly JSONL file convention.


@dataclass(frozen=True, slots=True)
class ContemplationEvidenceRef:
    """Pointer to evidence supporting a contemplation finding.

    Distinct from :class:`teaching.discovery.EvidencePointer` — see
    the BOUNDARY note above this class for why the two stay separate.
    """

    source_type: str
    source_id: str
    pointer: str
    summary: str = ""

    def __post_init__(self) -> None:
        if not self.source_type.strip():
            raise ValueError("ContemplationEvidenceRef.source_type is required")
        if not self.source_id.strip():
            raise ValueError("ContemplationEvidenceRef.source_id is required")
        if not self.pointer.strip():
            raise ValueError("ContemplationEvidenceRef.pointer is required")

    def as_dict(self) -> dict[str, str]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "pointer": self.pointer,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class ContemplationFinding:
    """One speculative self-contemplation output.

    ADR-0080 invariant: contemplation findings are never COHERENT.  The
    loop may propose reviewable evidence, but it may not ratify itself.
    """

    kind: FindingKind
    subject: str
    predicate: str
    object: str | None
    evidence_refs: tuple[ContemplationEvidenceRef, ...]
    proposed_action: str
    substrate_hash: str
    epistemic_status: EpistemicStatus = EpistemicStatus.SPECULATIVE
    finding_id: str = field(default="")

    def __post_init__(self) -> None:
        if self.epistemic_status is not EpistemicStatus.SPECULATIVE:
            raise ValueError(
                "ContemplationFinding must remain SPECULATIVE; "
                f"got {self.epistemic_status.value}"
            )
        if not self.subject.strip():
            raise ValueError("ContemplationFinding.subject is required")
        if not self.predicate.strip():
            raise ValueError("ContemplationFinding.predicate is required")
        if not self.proposed_action.strip():
            raise ValueError("ContemplationFinding.proposed_action is required")
        if not self.substrate_hash.strip():
            raise ValueError("ContemplationFinding.substrate_hash is required")
        if not self.evidence_refs:
            raise ValueError("ContemplationFinding requires at least one evidence ref")
        if not self.finding_id:
            object.__setattr__(self, "finding_id", _sha256_16(self._identity_dict()))

    def _identity_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "evidence_refs": [e.as_dict() for e in self.evidence_refs],
            "proposed_action": self.proposed_action,
            "substrate_hash": self.substrate_hash,
            "epistemic_status": self.epistemic_status.value,
        }

    def as_dict(self) -> dict[str, Any]:
        payload = self._identity_dict()
        payload["finding_id"] = self.finding_id
        return payload

    @property
    def confidence(self) -> EpistemicStatus:
        """ADR-0080 Phase 1 confidence alias.

        Phase 1 deliberately reuses the repository's epistemic lattice:
        every contemplation confidence is SPECULATIVE by construction.
        """
        return self.epistemic_status

    @property
    def evidence(self) -> tuple[ContemplationEvidenceRef, ...]:
        """ADR-0080 Phase 1 evidence alias for ``evidence_refs``."""
        return self.evidence_refs

    @property
    def provenance(self) -> dict[str, str]:
        """Deterministic provenance for the finding's read-only substrate."""
        return {
            "source": "contemplation",
            "substrate_hash": self.substrate_hash,
        }


@dataclass(frozen=True, slots=True)
class ContemplationRun:
    """Deterministic result of a read-only contemplation pass."""

    substrate_hash: str
    config_hash: str
    findings: tuple[ContemplationFinding, ...]
    run_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.substrate_hash.strip():
            raise ValueError("ContemplationRun.substrate_hash is required")
        if not self.config_hash.strip():
            raise ValueError("ContemplationRun.config_hash is required")
        for finding in self.findings:
            if finding.epistemic_status is not EpistemicStatus.SPECULATIVE:
                raise ValueError("ContemplationRun cannot contain non-SPECULATIVE findings")
        if not self.run_id:
            object.__setattr__(self, "run_id", _sha256_16(self._identity_dict()))

    def _identity_dict(self) -> dict[str, Any]:
        return {
            "substrate_hash": self.substrate_hash,
            "config_hash": self.config_hash,
            "findings": [f.as_dict() for f in self.findings],
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "substrate_hash": self.substrate_hash,
            "config_hash": self.config_hash,
            "finding_count": len(self.findings),
            "findings": [f.as_dict() for f in self.findings],
        }


def format_contemplation_finding_jsonl(finding: ContemplationFinding) -> str:
    """Return a deterministic JSONL line for a contemplation finding.

    Mirrors :func:`teaching.discovery.format_candidate_jsonl` in style
    (canonical JSON, sorted keys, no trailing newline) so both flow
    through the same ``DiscoveryCandidateSink`` plumbing without
    schema-aware special casing.
    """
    return _canonical_json(finding.as_dict())


__all__ = [
    "ContemplationEvidenceRef",
    "ContemplationFinding",
    "ContemplationRun",
    "FindingKind",
    "format_contemplation_finding_jsonl",
]
