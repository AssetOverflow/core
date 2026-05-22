"""Curriculum-sourced teaching proposal construction (ADR-0104).

Translates curriculum-authored ``PACK_MUTATION_CANDIDATE`` records into
:class:`teaching.store.PackMutationProposal` candidates with
``ProposalSource(kind="curriculum")`` provenance.

The result is **never** review-eligible by itself. Every
curriculum-sourced proposal must traverse the same review path used by
operator-authored and miner-sourced proposals
(:func:`teaching.review.review_correction`). This module is
construction-only — it never mutates packs, never promotes proposals to
``coherent``, and never bypasses identity defenses.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol

from core.contemplation.schema import ContemplationFinding, FindingKind
from teaching.epistemic import EpistemicStatus
from teaching.review import _is_identity_override
from teaching.source import ProposalSource
from teaching.store import PackMutationProposal


class CurriculumProposalError(ValueError):
    """Raised when a curriculum-sourced proposal cannot be constructed."""


@dataclass(frozen=True, slots=True)
class CurriculumReplayEquivalenceResult:
    """Outcome of the pre-review replay-equivalence check."""

    equivalent: bool
    checker_id: str
    non_target_turns_changed: tuple[int, ...] = ()
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "equivalent": self.equivalent,
            "checker_id": self.checker_id,
            "non_target_turns_changed": list(self.non_target_turns_changed),
            "notes": self.notes,
        }


class CurriculumReplayEquivalenceChecker(Protocol):
    """Protocol for the ADR-0104 replay-equivalence gate."""

    def check(
        self, *, finding: ContemplationFinding, curriculum_id: str
    ) -> CurriculumReplayEquivalenceResult: ...


@dataclass(frozen=True, slots=True)
class NoOpCurriculumReplayChecker:
    """Default checker that defers replay to a production implementation."""

    checker_id: str = "noop_curriculum_replay_checker_v1"

    def check(
        self, *, finding: ContemplationFinding, curriculum_id: str
    ) -> CurriculumReplayEquivalenceResult:
        return CurriculumReplayEquivalenceResult(
            equivalent=True,
            checker_id=self.checker_id,
            non_target_turns_changed=(),
            notes="deferred to production checker; treat as not-yet-verified",
        )


@dataclass(frozen=True, slots=True)
class CurriculumProposalBatch:
    """Result of translating a curriculum finding batch into proposals."""

    curriculum_id: str
    emitted_at_revision: str
    proposals: tuple[PackMutationProposal, ...]
    rejections: tuple[Mapping[str, Any], ...] = field(default=())

    def as_dict(self) -> dict[str, Any]:
        return {
            "curriculum_id": self.curriculum_id,
            "emitted_at_revision": self.emitted_at_revision,
            "proposals": [p.as_dict() for p in self.proposals],
            "rejections": [dict(r) for r in self.rejections],
        }


def _canonical_finding(finding: ContemplationFinding) -> str:
    return json.dumps(
        finding.as_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _proposal_id(
    *, curriculum_id: str, finding: ContemplationFinding, emitted_at_revision: str
) -> str:
    payload = json.dumps(
        {
            "curriculum_id": curriculum_id,
            "finding_canonical": _canonical_finding(finding),
            "emitted_at_revision": emitted_at_revision,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _identity_override_text(finding: ContemplationFinding) -> str | None:
    if _is_identity_override(finding.subject):
        return finding.subject
    if _is_identity_override(finding.proposed_action):
        return finding.proposed_action
    return None


def _validate_finding(finding: Any) -> ContemplationFinding:
    if not isinstance(finding, ContemplationFinding):
        raise CurriculumProposalError(
            f"curriculum finding must be a ContemplationFinding; got "
            f"{type(finding).__name__}"
        )
    if finding.kind is not FindingKind.PACK_MUTATION_CANDIDATE:
        raise CurriculumProposalError(
            "curriculum finding kind must be PACK_MUTATION_CANDIDATE; got "
            f"{finding.kind.value!r}"
        )
    if finding.epistemic_status is not EpistemicStatus.SPECULATIVE:
        raise CurriculumProposalError(
            "curriculum finding must be SPECULATIVE at construction; got "
            f"{finding.epistemic_status.value!r}"
        )
    return finding


def from_finding(
    finding: ContemplationFinding,
    *,
    curriculum_id: str,
    emitted_at_revision: str,
    replay_checker: CurriculumReplayEquivalenceChecker | None = None,
) -> PackMutationProposal:
    """Construct one curriculum-sourced :class:`PackMutationProposal`."""
    if not curriculum_id.strip():
        raise CurriculumProposalError("curriculum_id must be non-empty")
    if not emitted_at_revision.strip():
        raise CurriculumProposalError("emitted_at_revision must be non-empty")

    validated = _validate_finding(finding)
    blocked_text = _identity_override_text(validated)
    if blocked_text is not None:
        raise CurriculumProposalError(
            "curriculum finding rejected at construction: identity-override "
            f"text detected on subject/proposed_action: {blocked_text!r}"
        )

    checker = replay_checker if replay_checker is not None else NoOpCurriculumReplayChecker()
    replay = checker.check(finding=validated, curriculum_id=curriculum_id)
    if not replay.equivalent:
        raise CurriculumProposalError(
            "curriculum finding rejected at construction: replay-equivalence "
            f"failed (checker={replay.checker_id!r}, "
            f"non_target_turns_changed={replay.non_target_turns_changed})"
        )

    source = ProposalSource(
        kind="curriculum",
        source_id=curriculum_id,
        emitted_at_revision=emitted_at_revision,
    )
    return PackMutationProposal(
        proposal_id=_proposal_id(
            curriculum_id=curriculum_id,
            finding=validated,
            emitted_at_revision=emitted_at_revision,
        ),
        candidate_id=validated.finding_id,
        subject=validated.subject,
        correction_text=validated.proposed_action,
        prior_surface=_evidence_summary(validated),
        source=source,
        triple=None,
        epistemic_status=EpistemicStatus.SPECULATIVE,
    )


def _evidence_summary(finding: ContemplationFinding) -> str:
    parts = sorted(f"{e.source_type}:{e.pointer}" for e in finding.evidence_refs)
    return f"curriculum_evidence[{len(parts)}]: " + " | ".join(parts)


def from_findings(
    findings: Iterable[ContemplationFinding],
    *,
    curriculum_id: str,
    emitted_at_revision: str,
    replay_checker: CurriculumReplayEquivalenceChecker | None = None,
) -> CurriculumProposalBatch:
    """Translate a curriculum finding stream into a deterministic batch."""
    proposals: list[PackMutationProposal] = []
    rejections: list[Mapping[str, Any]] = []

    for finding in findings:
        validated = _validate_finding(finding)
        blocked_text = _identity_override_text(validated)
        if blocked_text is not None:
            rejections.append(
                {
                    "finding_id": validated.finding_id,
                    "reason": "identity_override",
                    "matched_text": blocked_text,
                }
            )
            continue
        checker = replay_checker if replay_checker is not None else NoOpCurriculumReplayChecker()
        replay = checker.check(finding=validated, curriculum_id=curriculum_id)
        if not replay.equivalent:
            rejections.append(
                {
                    "finding_id": validated.finding_id,
                    "reason": "replay_equivalence_failed",
                    "checker_id": replay.checker_id,
                    "non_target_turns_changed": list(replay.non_target_turns_changed),
                }
            )
            continue
        proposals.append(
            from_finding(
                validated,
                curriculum_id=curriculum_id,
                emitted_at_revision=emitted_at_revision,
                replay_checker=_AlwaysEquivalentChecker(replay.checker_id),
            )
        )

    return CurriculumProposalBatch(
        curriculum_id=curriculum_id,
        emitted_at_revision=emitted_at_revision,
        proposals=tuple(proposals),
        rejections=tuple(rejections),
    )


@dataclass(frozen=True, slots=True)
class _AlwaysEquivalentChecker:
    checker_id: str

    def check(
        self, *, finding: ContemplationFinding, curriculum_id: str
    ) -> CurriculumReplayEquivalenceResult:
        return CurriculumReplayEquivalenceResult(
            equivalent=True,
            checker_id=self.checker_id,
            non_target_turns_changed=(),
            notes="batch-level checker already ran",
        )


def serialize_proposal_emitted_event(proposal: PackMutationProposal) -> dict[str, Any]:
    """Emit ADR-0104 ``\"type\": \"proposal_emitted\"`` telemetry payload."""
    return {
        "type": "proposal_emitted",
        "proposal_id": proposal.proposal_id,
        "source": proposal.source.serialize(),
        "epistemic_status": proposal.epistemic_status.value,
    }
