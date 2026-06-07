"""Proposal-only failure-artifact emitter (N5) — deliberately toothless.

When the contemplation pass (N6) meets a **growth-surface** failure family (``proposal_allowed
= True``), it may emit a single content-addressed JSON artifact under
``teaching/proposals/comprehension_failures/<hash>.json``. That artifact can *propose* a next
fixture/rule for human review. It can do nothing else:

```text
status is always "proposal_only"
mounted is always false
requires_review is always true
serving never reads these files
no reader/test is modified
```

This routes into the existing proposal-only teaching flywheel (ADR-0055/0056/0057) — it is NOT a
parallel correction path (CLAUDE.md teaching-safety). The alignment is
``failure -> classification -> proposal -> review -> ratification``, never ``failure -> self-patch``.

Content-addressing: the filename is ``sha256(failure_family : sha256(problem_text))`` — so the
same failure on the same text always writes the same path (idempotent), and the raw problem text
is **hashed, never stored**. Deterministic; no clock, no randomness.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.comprehension_attempt.failure_family import FailureFamily
from core.comprehension_attempt.model import ComprehensionAttempt

_PROPOSAL_STATUS = "proposal_only"


def default_proposal_root() -> Path:
    """``<repo>/teaching/proposals/comprehension_failures`` — the write-only proposal sink."""
    return Path(__file__).resolve().parents[2] / "teaching" / "proposals" / "comprehension_failures"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _attempt_to_dict(attempt: ComprehensionAttempt) -> dict[str, Any]:
    return {
        "organ": attempt.organ,
        "outcome": attempt.outcome,
        "refusal_reason": attempt.refusal_reason,
        "family": attempt.family,
        "setup_signature": attempt.setup_signature,
        "answer": attempt.answer,
    }


@dataclass(frozen=True, slots=True)
class FailureProposal:
    """A proposal-only artifact. The invariant fields (``status``/``requires_review``/``mounted``)
    are enforced in ``__post_init__`` so even a hand-constructed proposal cannot be made
    serving-mountable."""

    failure_family: str
    problem_text_sha256: str
    observed_attempts: tuple[dict[str, Any], ...]
    status: str = _PROPOSAL_STATUS
    suggested_next_fixture: None = None  # v0: always None — a human authors the fixture on review
    requires_review: bool = True
    mounted: bool = False

    def __post_init__(self) -> None:
        if self.status != _PROPOSAL_STATUS:
            raise ValueError(f"proposal status must be {_PROPOSAL_STATUS!r}; got {self.status!r}")
        if self.mounted:
            raise ValueError("a proposal can never be mounted")
        if not self.requires_review:
            raise ValueError("a proposal always requires review")

    def content_hash(self) -> str:
        """Deterministic content address: same failure on same text -> same hash."""
        return hashlib.sha256(
            f"{self.failure_family}:{self.problem_text_sha256}".encode("utf-8")
        ).hexdigest()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "failure_family": self.failure_family,
            "problem_text_sha256": self.problem_text_sha256,
            "observed_attempts": list(self.observed_attempts),
            "suggested_next_fixture": self.suggested_next_fixture,
            "requires_review": self.requires_review,
            "mounted": self.mounted,
        }


def build_proposal(
    text: str, family: FailureFamily, attempts: tuple[ComprehensionAttempt, ...]
) -> FailureProposal | None:
    """Build a proposal for a growth-surface family, or ``None`` for a correct wrong=0 boundary.

    A family with ``proposal_allowed = False`` (every must-remain-refused boundary) yields NO
    proposal — the loop never proposes against a faithful refusal.
    """
    if not family.proposal_allowed:
        return None
    return FailureProposal(
        failure_family=family.name,
        problem_text_sha256=_sha256(text),
        observed_attempts=tuple(_attempt_to_dict(a) for a in attempts),
    )


def proposal_path(proposal: FailureProposal, root: Path | None = None) -> Path:
    base = root if root is not None else default_proposal_root()
    return base / f"{proposal.content_hash()}.json"


def emit_proposal(
    text: str,
    family: FailureFamily,
    attempts: tuple[ComprehensionAttempt, ...],
    *,
    root: Path | None = None,
) -> Path | None:
    """Write a proposal-only artifact for a growth-surface family; return its path, or ``None``.

    Idempotent: the same failure on the same text writes the same content-addressed path with
    byte-identical content (``sort_keys``). Creates the sink directory on demand.
    """
    proposal = build_proposal(text, family, attempts)
    if proposal is None:
        return None
    path = proposal_path(proposal, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal.to_json_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


__all__ = [
    "FailureProposal",
    "build_proposal",
    "default_proposal_root",
    "emit_proposal",
    "proposal_path",
]
