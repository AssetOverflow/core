"""ADR-0057 Phase C2 — TeachingChainProposal + append-only proposal log.

A ``TeachingChainProposal`` is the **only** path by which the
system extends its active teaching corpus.  Trust boundary:

  - Proposals are derived from contemplated DiscoveryCandidates
    (ADR-0056 Phase C1 output).
  - Eligibility (Call 2 in ADR-0057) is a mechanical predicate.
    Ineligible candidates raise; eligible ones become a pending
    proposal.
  - The replay-equivalence gate (``teaching/replay.py``) is a
    *precondition*, not a permission.  A passing gate moves the
    proposal to ``replay_equivalent=True``; only an explicit
    operator ``accept`` writes to the active corpus.
  - The proposal log is append-only.  All four review states
    (pending / accepted / rejected / withdrawn) are terminal in
    the log; "delete" doesn't exist.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from teaching.provenance import Provenance
from teaching.source import ProposalSource

if TYPE_CHECKING:
    # Deferred to break a circular import: teaching.discovery →
    # chat.pack_grounding → chat.__init__ → chat.runtime →
    # teaching.discovery.  These names are used only as type
    # annotations here, so the TYPE_CHECKING guard is safe.
    from teaching.discovery import (
        ClaimDomain,
        DiscoveryCandidate,
        EvidencePointer,
    )


# Default proposal log location.  Tests inject a tmp path; callers
# in production use this constant.
DEFAULT_PROPOSAL_LOG_PATH: Path = (
    Path(__file__).resolve().parent / "proposals" / "proposals.jsonl"
)


ReviewState = Literal["pending", "accepted", "rejected", "withdrawn"]


@dataclass(frozen=True, slots=True)
class ReplayEvidence:
    """Cognition-lane metrics before/after the proposed append.

    A regressed metric is one whose candidate value is strictly
    less than the baseline value.  The cognition lane is
    deterministic; no float tolerance is applied (ADR-0057 Call 1
    note: any regression is real).
    """

    baseline: dict[str, float]
    candidate: dict[str, float]
    regressed_metrics: tuple[str, ...]
    replay_equivalent: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline": dict(self.baseline),
            "candidate": dict(self.candidate),
            "regressed_metrics": list(self.regressed_metrics),
            "replay_equivalent": bool(self.replay_equivalent),
        }


@dataclass(frozen=True, slots=True)
class TeachingChainProposal:
    """One proposed extension of the active teaching corpus.

    The ``source`` field (ADR-0094) carries typed provenance: operator
    versus miner versus curriculum. Operator is the default and is
    populated on every existing proposal by the migration utility in
    :mod:`teaching.proposals.migrate_source_field`.
    """

    proposal_id: str
    source_candidate_id: str
    proposed_chain: dict[str, Any]
    polarity: Literal["affirms", "falsifies"]
    claim_domain: ClaimDomain
    evidence: tuple[EvidencePointer, ...]
    source: ProposalSource
    review_state: ReviewState = "pending"
    operator_note: str = ""
    replay_evidence: ReplayEvidence | None = None
    provenance: Provenance | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "source_candidate_id": self.source_candidate_id,
            "proposed_chain": dict(self.proposed_chain),
            "polarity": self.polarity,
            "claim_domain": self.claim_domain,
            "evidence": [e.as_dict() for e in self.evidence],
            "source": self.source.as_dict(),
            "review_state": self.review_state,
            "operator_note": self.operator_note,
            "replay_evidence": (
                self.replay_evidence.as_dict()
                if self.replay_evidence is not None
                else None
            ),
            "provenance": (asdict(self.provenance) if self.provenance else None),
        }


class ProposalError(ValueError):
    """Raised when a candidate fails an eligibility gate or when a
    review action is attempted in a state that does not allow it."""


# ---------------------------------------------------------------------------
# Eligibility (ADR-0057 Call 2)
# ---------------------------------------------------------------------------


def _is_chain_complete(chain: dict[str, Any]) -> bool:
    return all(
        chain.get(k) and isinstance(chain.get(k), str)
        for k in ("subject", "intent", "connective", "object")
    )


def check_eligibility(
    candidate: DiscoveryCandidate, *, allow_evaluative: bool = False
) -> None:
    """Raise ``ProposalError`` if ``candidate`` cannot become a proposal.

    Five mechanical gates (ADR-0057 Call 2):
      1. polarity ∈ {affirms, falsifies}
      2. evidence contains at least one corpus pointer
      3. claim_domain != evaluative unless ``allow_evaluative``
      4. boundary_clean=True
      5. proposed_chain is complete (all four fields populated)
    """
    if candidate.polarity not in ("affirms", "falsifies"):
        raise ProposalError(
            f"polarity must be 'affirms' or 'falsifies'; got "
            f"{candidate.polarity!r} — undetermined candidates cannot propose"
        )
    if not any(e.source == "corpus" for e in candidate.evidence):
        raise ProposalError(
            "evidence floor: at least one source='corpus' pointer is required"
        )
    if candidate.claim_domain == "evaluative" and not allow_evaluative:
        raise ProposalError(
            "claim_domain='evaluative' requires explicit --allow-evaluative"
        )
    if not candidate.boundary_clean:
        raise ProposalError("source turn was not boundary_clean")
    if not _is_chain_complete(candidate.proposed_chain):
        raise ProposalError(
            "proposed_chain must have subject/intent/connective/object populated"
        )


# ---------------------------------------------------------------------------
# Proposal id derivation
# ---------------------------------------------------------------------------


def _proposal_id(source_candidate_id: str, chain: dict[str, Any]) -> str:
    payload = {
        "source_candidate_id": source_candidate_id,
        "proposed_chain": chain,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def build_proposal(
    candidate: DiscoveryCandidate,
    *,
    allow_evaluative: bool = False,
    source: ProposalSource | None = None,
) -> TeachingChainProposal:
    """Build a ``pending`` proposal from an eligible candidate.

    Raises ``ProposalError`` for any failing gate.  Idempotent on
    (source_candidate_id, proposed_chain): same inputs produce the
    same ``proposal_id``.

    The ``source`` parameter (ADR-0094) defaults to an operator-authored
    source pinned at the current git HEAD. Miner-sourced and
    curriculum-sourced callers pass an explicit :class:`ProposalSource`.
    """
    check_eligibility(candidate, allow_evaluative=allow_evaluative)
    assert candidate.polarity in ("affirms", "falsifies")
    resolved_source = source if source is not None else _default_operator_source()
    return TeachingChainProposal(
        proposal_id=_proposal_id(candidate.candidate_id, candidate.proposed_chain),
        source_candidate_id=candidate.candidate_id,
        proposed_chain=dict(candidate.proposed_chain),
        polarity=candidate.polarity,
        claim_domain=candidate.claim_domain,
        evidence=tuple(candidate.evidence),
        source=resolved_source,
    )


def _default_operator_source() -> ProposalSource:
    """Return an operator-authored source pinned at the current HEAD.

    Used by :func:`build_proposal` when no explicit source is given.
    Reads ``git rev-parse HEAD``; falls back to ``"unknown"`` when git
    is unavailable so the schema invariant
    ``emitted_at_revision`` non-empty still holds.
    """
    return ProposalSource.operator(emitted_at_revision=_current_revision())


def _current_revision() -> str:
    """Return the current git HEAD SHA, or ``"unknown"`` if unavailable.

    Pure helper; no side effects. Cached at module load so a long
    session sees a stable value even if HEAD moves.
    """
    global _CACHED_REVISION
    if _CACHED_REVISION is not None:
        return _CACHED_REVISION
    import subprocess
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        _CACHED_REVISION = sha or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        _CACHED_REVISION = "unknown"
    return _CACHED_REVISION


_CACHED_REVISION: str | None = None


# ---------------------------------------------------------------------------
# Append-only proposal log
# ---------------------------------------------------------------------------


class ProposalLog:
    """Append-only JSONL store of proposals + state transitions.

    Each line is one *event*:

      - ``{"event": "created", "proposal": {...}}``
      - ``{"event": "replay", "proposal_id": "...", "replay_evidence": {...}}``
      - ``{"event": "transition", "proposal_id": "...",
            "to": "accepted|rejected|withdrawn", "note": "..."}``
      - ``{"event": "accepted_corpus_append", "proposal_id": "...",
            "chain_id": "...", "provenance": {...}}``

    The active view (``current_state``) is derived by replaying the
    log from the top; the file is never rewritten.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_PROPOSAL_LOG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # -- write side ---------------------------------------------------

    def _append(self, event: dict[str, Any]) -> None:
        line = json.dumps(event, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def record_created(self, proposal: TeachingChainProposal) -> None:
        self._append({"event": "created", "proposal": proposal.as_dict()})

    def record_replay(self, proposal_id: str, evidence: ReplayEvidence) -> None:
        self._append({
            "event": "replay",
            "proposal_id": proposal_id,
            "replay_evidence": evidence.as_dict(),
        })

    def record_transition(
        self, proposal_id: str, to_state: ReviewState, note: str
    ) -> None:
        self._append({
            "event": "transition",
            "proposal_id": proposal_id,
            "to": to_state,
            "note": note,
        })

    def record_corpus_append(
        self, proposal_id: str, chain_id: str, provenance: Provenance
    ) -> None:
        self._append({
            "event": "accepted_corpus_append",
            "proposal_id": proposal_id,
            "chain_id": chain_id,
            "provenance": asdict(provenance),
        })

    # -- read side ----------------------------------------------------

    def _events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def current_state(self) -> dict[str, dict[str, Any]]:
        """Replay the log → ``{proposal_id: {state, proposal, replay,
        note, accepted_chain_id, source}}``.

        The active view is derived deterministically from the log.

        ADR-0094: every ``created`` event must carry a ``source`` field
        on its proposal payload. Missing ``source`` raises
        :class:`ProposalError`; the live log is migrated via
        :mod:`teaching.migrate_proposals_source_field` exactly once at
        ADR-0094 landing.
        """
        view: dict[str, dict[str, Any]] = {}
        for ev in self._events():
            kind = ev.get("event")
            if kind == "created":
                p = ev.get("proposal") or {}
                pid = p.get("proposal_id")
                if not pid:
                    continue
                if "source" not in p:
                    raise ProposalError(
                        f"proposal {pid!r} missing required 'source' field; "
                        "run teaching/migrate_proposals_source_field.py "
                        "(ADR-0094)"
                    )
                # Validate that source parses as a v1 ProposalSource;
                # we keep the raw dict in the view for backward
                # compatibility but reject malformed payloads here.
                ProposalSource.from_dict(p["source"])
                view.setdefault(pid, {
                    "proposal": p,
                    "state": p.get("review_state", "pending"),
                    "replay_evidence": p.get("replay_evidence"),
                    "operator_note": p.get("operator_note", ""),
                    "source": p["source"],
                    "accepted_chain_id": None,
                    "accepted_provenance": None,
                })
            elif kind == "replay":
                pid = ev.get("proposal_id")
                if pid in view:
                    view[pid]["replay_evidence"] = ev.get("replay_evidence")
            elif kind == "transition":
                pid = ev.get("proposal_id")
                if pid in view:
                    view[pid]["state"] = ev.get("to")
                    view[pid]["operator_note"] = ev.get("note", "")
            elif kind == "accepted_corpus_append":
                pid = ev.get("proposal_id")
                if pid in view:
                    view[pid]["accepted_chain_id"] = ev.get("chain_id")
                    view[pid]["accepted_provenance"] = ev.get("provenance")
        return view

    def find(self, proposal_id: str) -> dict[str, Any] | None:
        return self.current_state().get(proposal_id)


# ---------------------------------------------------------------------------
# Corpus append (operator-accept side-effect)
# ---------------------------------------------------------------------------


def append_chain_to_corpus(
    chain: dict[str, Any],
    *,
    corpus_path: Path,
    provenance: Provenance,
    chain_id: str | None = None,
    superseded_by: str | None = None,
) -> str:
    """Append one reviewed chain JSON line to the active corpus.

    Returns the ``chain_id`` written.  Trust boundary: this is the
    ONLY function in the codebase that writes to the active teaching
    corpus, and it is reachable only from ``accept_proposal`` (after
    the replay-equivalence gate + operator review) or from
    ``teaching.supersede.supersede_chain`` (operator-driven retire
    of an existing chain — see ADR-0057).

    ``superseded_by`` records the ``chain_id`` of an earlier active
    entry that this new entry retires.  The earlier entry stays on
    disk; ``teaching.audit`` and ``chat.teaching_grounding`` both
    honour the supersession at load time.
    """
    subject = str(chain["subject"]).strip().lower()
    intent = str(chain["intent"]).strip().lower()
    connective = str(chain["connective"]).strip()
    obj = str(chain["object"]).strip().lower()
    if not chain_id:
        chain_id = f"{intent}_{subject}_{connective}_{obj}"
    entry: dict[str, Any] = {
        "chain_id": chain_id,
        "subject": subject,
        "intent": intent,
        "connective": connective,
        "object": obj,
        "domains_subject_k": 2,
        "domains_object_k": 1,
        "provenance": provenance.raw or (
            f"{provenance.adr_id or 'adr-0057'}:{provenance.source}:"
            f"{provenance.review_date or ''}"
        ),
    }
    if superseded_by:
        entry["superseded_by"] = str(superseded_by).strip()
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    with corpus_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return chain_id


# ---------------------------------------------------------------------------
# Orchestration helpers — propose / replay / accept / reject / withdraw
# ---------------------------------------------------------------------------


def propose_from_candidate(
    candidate: DiscoveryCandidate,
    *,
    log: ProposalLog,
    run_replay: Any = None,
    allow_evaluative: bool = False,
) -> TeachingChainProposal:
    """End-to-end: build proposal, run replay-equivalence gate,
    auto-reject on regression, otherwise leave pending.

    ``run_replay`` is the replay function (``teaching.replay.
    run_replay_equivalence`` by default); accepting it as a kwarg
    keeps tests fast — they can pass a fake that returns a stub
    ``ReplayEvidence`` without booting the cognition lane.

    Idempotent on (candidate_id, chain): re-proposing returns the
    existing proposal record if any.
    """
    proposal = build_proposal(candidate, allow_evaluative=allow_evaluative)
    existing = log.find(proposal.proposal_id)
    if existing is not None:
        return proposal
    log.record_created(proposal)

    if run_replay is None:
        from teaching.replay import run_replay_equivalence as run_replay
    evidence = run_replay(proposal.proposed_chain)
    log.record_replay(proposal.proposal_id, evidence)

    if not evidence.replay_equivalent:
        note = "auto_rollback_regression: " + ",".join(evidence.regressed_metrics)
        log.record_transition(proposal.proposal_id, "rejected", note)

    return proposal


def accept_proposal(
    proposal_id: str,
    *,
    log: ProposalLog,
    corpus_path: Path,
    review_date: str,
    operator_note: str = "",
) -> str:
    """Operator accept — append proposed chain to the active corpus.

    Pre-conditions (each raises ``ProposalError`` on failure):
      - proposal exists in the log
      - current state is ``pending``
      - replay evidence is present and replay_equivalent=True
    Returns the ``chain_id`` written to the corpus.
    """
    record = log.find(proposal_id)
    if record is None:
        raise ProposalError(f"proposal not found: {proposal_id}")
    if record["state"] != "pending":
        raise ProposalError(
            f"proposal {proposal_id} is {record['state']!r}, not pending"
        )
    replay = record.get("replay_evidence")
    if not replay or not replay.get("replay_equivalent"):
        raise ProposalError(
            f"proposal {proposal_id} is not replay-equivalent; cannot accept"
        )
    chain = record["proposal"]["proposed_chain"]
    provenance = Provenance(
        adr_id="adr-0057",
        source="discovery_promoted",
        review_date=review_date,
        raw=f"adr-0057:discovery_promoted:{review_date}",
    )
    chain_id = append_chain_to_corpus(
        chain, corpus_path=corpus_path, provenance=provenance
    )
    log.record_transition(proposal_id, "accepted", operator_note)
    log.record_corpus_append(proposal_id, chain_id, provenance)
    return chain_id


def reject_proposal(
    proposal_id: str, *, log: ProposalLog, operator_note: str = ""
) -> None:
    record = log.find(proposal_id)
    if record is None:
        raise ProposalError(f"proposal not found: {proposal_id}")
    if record["state"] != "pending":
        raise ProposalError(
            f"proposal {proposal_id} is {record['state']!r}, not pending"
        )
    log.record_transition(proposal_id, "rejected", operator_note)


def withdraw_proposal(
    proposal_id: str, *, log: ProposalLog, operator_note: str = ""
) -> None:
    record = log.find(proposal_id)
    if record is None:
        raise ProposalError(f"proposal not found: {proposal_id}")
    if record["state"] != "pending":
        raise ProposalError(
            f"proposal {proposal_id} is {record['state']!r}, not pending"
        )
    log.record_transition(proposal_id, "withdrawn", operator_note)


__all__ = [
    "DEFAULT_PROPOSAL_LOG_PATH",
    "ProposalError",
    "ProposalLog",
    "ReplayEvidence",
    "ReviewState",
    "TeachingChainProposal",
    "accept_proposal",
    "append_chain_to_corpus",
    "build_proposal",
    "check_eligibility",
    "propose_from_candidate",
    "reject_proposal",
    "withdraw_proposal",
]
