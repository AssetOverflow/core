"""Miner-sourced teaching proposal construction (ADR-0095).

Translates :class:`core.contemplation.schema.ContemplationFinding`
records (``kind=PACK_MUTATION_CANDIDATE``) emitted by the Phase-5
miners into :class:`teaching.store.PackMutationProposal` candidates.

The result is **never** review-eligible by itself. Every miner-sourced
proposal must traverse the same review path used by operator-authored
proposals (:func:`teaching.review.review_correction`). This module is
construction-only — it never mutates packs, never promotes proposals
to ``coherent``, and never bypasses identity defenses.

Hard constraints (ADR-0095):

1. **Single review path.** Construction emits ``SPECULATIVE`` proposals.
   No code in this module promotes a proposal.

2. **Default status ``speculative``.** Inherited from
   :class:`PackMutationProposal` schema.

3. **Identity-pack defense at construction.** A finding whose
   ``subject`` or ``proposed_action`` matches the identity-override
   detector is rejected here, before review. This is an upstream
   extension of :func:`teaching.review._is_identity_override` so the
   miner can never even *file* an identity-override candidate.

4. **Replay-equivalence pre-gate.** A pluggable
   :class:`ReplayEquivalenceChecker` runs before the proposal is
   yielded. If the checker reports trace_hash divergence on any
   non-target turn, the proposal is rejected at construction.

5. **Deterministic emission.** ``proposal_id`` is the first 16 hex
   chars of SHA-256(canonical(miner_id, finding, revision)). Same
   inputs → byte-identical proposal stream.
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


class MinerProposalError(ValueError):
    """Raised when a miner-sourced proposal cannot be constructed."""


@dataclass(frozen=True, slots=True)
class ReplayEquivalenceResult:
    """Outcome of the pre-review replay-equivalence check.

    ``equivalent`` is True only when replaying the originating lane
    under the proposed mutation preserves ``trace_hash`` on every
    non-target turn. ``non_target_turns_changed`` enumerates the indices
    whose hash diverged.

    ``checker_id`` identifies the implementation that produced this
    result so audit/telemetry can attribute the verdict.
    """

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


class ReplayEquivalenceChecker(Protocol):
    """Protocol for the ADR-0095 pre-review replay-equivalence gate.

    Implementations replay the originating turn against the proposed
    mutation and report whether non-target turns remain byte-identical.
    The concrete production checker lives outside this ADR; this module
    only requires the seam.

    Implementations must expose a ``checker_id`` attribute on the
    returned :class:`ReplayEquivalenceResult` so audit and telemetry
    can attribute verdicts without depending on instance identity.
    """

    def check(
        self, *, finding: ContemplationFinding, miner_id: str
    ) -> ReplayEquivalenceResult: ...


@dataclass(frozen=True, slots=True)
class NoOpReplayChecker:
    """Default checker that defers replay to a production implementation.

    Returns ``equivalent=True`` with an explicit note so downstream
    audit can recognize a deferred verdict and refuse coherence
    promotion until a real checker has run. This is a seam, not a free
    pass: the lane runner uses an injectable checker for tests and the
    runtime uses the production checker once it lands.
    """

    checker_id: str = "noop_replay_checker_v1"

    def check(
        self, *, finding: ContemplationFinding, miner_id: str
    ) -> ReplayEquivalenceResult:
        return ReplayEquivalenceResult(
            equivalent=True,
            checker_id=self.checker_id,
            non_target_turns_changed=(),
            notes="deferred to production checker; treat as not-yet-verified",
        )


@dataclass(frozen=True, slots=True)
class MinerProposalBatch:
    """Result of translating a finding batch into miner-sourced proposals.

    ``proposals`` contains the survivors; ``rejections`` records why
    each non-yielded finding was filtered. Together they round-trip
    the full input batch deterministically.
    """

    miner_id: str
    emitted_at_revision: str
    proposals: tuple[PackMutationProposal, ...]
    rejections: tuple[Mapping[str, Any], ...] = field(default=())

    def as_dict(self) -> dict[str, Any]:
        return {
            "miner_id": self.miner_id,
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
    *, miner_id: str, finding: ContemplationFinding, emitted_at_revision: str
) -> str:
    payload = json.dumps(
        {
            "miner_id": miner_id,
            "finding_canonical": _canonical_finding(finding),
            "emitted_at_revision": emitted_at_revision,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _identity_override_text(finding: ContemplationFinding) -> str | None:
    """Return the first identity-override text found on the finding, else None.

    Defense is upstream of review: rejects miner-sourced findings that
    *could* parse as identity-override attempts so they never reach the
    proposal log at all.
    """
    if _is_identity_override(finding.subject):
        return finding.subject
    if _is_identity_override(finding.proposed_action):
        return finding.proposed_action
    return None


def _validate_finding(finding: Any) -> ContemplationFinding:
    if not isinstance(finding, ContemplationFinding):
        raise MinerProposalError(
            f"miner finding must be a ContemplationFinding; got "
            f"{type(finding).__name__}"
        )
    if finding.kind is not FindingKind.PACK_MUTATION_CANDIDATE:
        raise MinerProposalError(
            f"miner finding kind must be PACK_MUTATION_CANDIDATE; got "
            f"{finding.kind.value!r}"
        )
    if finding.epistemic_status is not EpistemicStatus.SPECULATIVE:
        raise MinerProposalError(
            "miner finding must be SPECULATIVE at construction; got "
            f"{finding.epistemic_status.value!r}"
        )
    return finding


def from_finding(
    finding: ContemplationFinding,
    *,
    miner_id: str,
    emitted_at_revision: str,
    replay_checker: ReplayEquivalenceChecker | None = None,
) -> PackMutationProposal:
    """Construct one miner-sourced :class:`PackMutationProposal`.

    Raises :class:`MinerProposalError` if the finding violates an
    ADR-0095 hard constraint (identity override, wrong kind, malformed,
    replay-equivalence broken).
    """
    if not miner_id.strip():
        raise MinerProposalError("miner_id must be non-empty")
    if not emitted_at_revision.strip():
        raise MinerProposalError("emitted_at_revision must be non-empty")

    validated = _validate_finding(finding)
    blocked_text = _identity_override_text(validated)
    if blocked_text is not None:
        raise MinerProposalError(
            "miner finding rejected at construction: identity-override "
            f"text detected on subject/proposed_action: {blocked_text!r}"
        )

    checker = replay_checker if replay_checker is not None else NoOpReplayChecker()
    replay = checker.check(finding=validated, miner_id=miner_id)
    if not replay.equivalent:
        raise MinerProposalError(
            "miner finding rejected at construction: replay-equivalence "
            f"failed (checker={replay.checker_id!r}, "
            f"non_target_turns_changed={replay.non_target_turns_changed})"
        )

    pid = _proposal_id(
        miner_id=miner_id,
        finding=validated,
        emitted_at_revision=emitted_at_revision,
    )
    source = ProposalSource(
        kind="miner",
        source_id=miner_id,
        emitted_at_revision=emitted_at_revision,
    )

    return PackMutationProposal(
        proposal_id=pid,
        candidate_id=validated.finding_id,
        subject=validated.subject,
        correction_text=validated.proposed_action,
        prior_surface=_evidence_summary(validated),
        source=source,
        triple=None,
        epistemic_status=EpistemicStatus.SPECULATIVE,
    )


def _evidence_summary(finding: ContemplationFinding) -> str:
    """Deterministic single-line summary of finding evidence_refs.

    Stored in ``prior_surface`` so reviewers see provenance without
    needing to round-trip the original observations.
    """
    parts = sorted(
        f"{e.source_type}:{e.pointer}" for e in finding.evidence_refs
    )
    return f"miner_evidence[{len(parts)}]: " + " | ".join(parts)


def from_findings(
    findings: Iterable[ContemplationFinding],
    *,
    miner_id: str,
    emitted_at_revision: str,
    replay_checker: ReplayEquivalenceChecker | None = None,
) -> MinerProposalBatch:
    """Translate a finding stream into a deterministic proposal batch.

    Identity-override rejections and replay-equivalence failures are
    captured in :attr:`MinerProposalBatch.rejections` rather than
    raised, so a partial batch can proceed without losing audit
    evidence on the rejected items. Other malformed inputs (wrong
    kind, wrong epistemic status, non-finding values) still raise.

    Findings are processed in input order; rejection ordering matches.
    """
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
        checker = replay_checker if replay_checker is not None else NoOpReplayChecker()
        replay = checker.check(finding=validated, miner_id=miner_id)
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
        try:
            proposal = from_finding(
                validated,
                miner_id=miner_id,
                emitted_at_revision=emitted_at_revision,
                replay_checker=_AlwaysEquivalentChecker(replay.checker_id),
            )
        except MinerProposalError as exc:
            rejections.append(
                {"finding_id": validated.finding_id, "reason": str(exc)}
            )
            continue
        proposals.append(proposal)

    return MinerProposalBatch(
        miner_id=miner_id,
        emitted_at_revision=emitted_at_revision,
        proposals=tuple(proposals),
        rejections=tuple(rejections),
    )


@dataclass(frozen=True, slots=True)
class _AlwaysEquivalentChecker:
    """Internal: passes the verdict through after the batch-level gate ran."""

    checker_id: str

    def check(
        self, *, finding: ContemplationFinding, miner_id: str
    ) -> ReplayEquivalenceResult:
        return ReplayEquivalenceResult(
            equivalent=True,
            checker_id=self.checker_id,
            non_target_turns_changed=(),
            notes="batch-level checker already ran",
        )


def serialize_proposal_emitted_event(proposal: PackMutationProposal) -> dict[str, Any]:
    """Emit ADR-0095 ``"type": "proposal_emitted"`` telemetry payload.

    Content (``correction_text``, ``subject``) is **redacted by default**
    in keeping with ADR-0040 telemetry policy. Only the proposal id,
    serialized source string, and proposal epistemic status flow to the
    sink; raw content is intentionally absent.
    """
    return {
        "type": "proposal_emitted",
        "proposal_id": proposal.proposal_id,
        "source": proposal.source.serialize(),
        "epistemic_status": proposal.epistemic_status.value,
    }
