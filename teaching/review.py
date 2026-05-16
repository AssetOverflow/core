"""Review gate — validate corrections before they become teaching examples.

The reviewer enforces two hard constraints:
  1. Identity override rejected — corrections that attempt to redefine
     CORE's identity axes are blocked.
  2. Bounded — the correction must reference a specific prior turn and
     contain non-empty corrective content.

Reviewed examples carry a deterministic trace (SHA-256 over their content)
so that identical corrections on identical prior turns always produce the
same review hash.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum, unique

from core.physics.identity import IdentityCheck, IdentityManifold, IdentityScore
from teaching.correction import CorrectionCandidate


@unique
class ReviewOutcome(Enum):
    ACCEPTED = "accepted"
    REJECTED_IDENTITY = "rejected_identity"
    REJECTED_EMPTY = "rejected_empty"


# Rule (a): legacy literal markers. Retained for backward compatibility with the
# v1/v2 marker-family attacks and existing teaching-loop tests.
_IDENTITY_MARKERS: frozenset[str] = frozenset({
    "you are",
    "your name is",
    "your identity",
    "you must be",
    "you should act as",
    "you are now",
    "forget your",
    "ignore your",
    "override your",
    "your personality",
    "your character",
    "pretend to be",
    "act as if you",
    "from now on you",
})

# Rule (b) component: verbs that redirect, transform, or discard the agent's
# active role/state. Deliberately narrow — only verbs that, in correction
# context, mean "switch what you are / stop being what you were."
_REDIRECT_VERBS: frozenset[str] = frozenset({
    "become", "behave", "transform", "switch", "assume", "adopt",
    "take", "drop", "discard", "abandon", "slip", "set",
    "pretend", "shift", "roleplay", "ignore", "forget",
    "override", "act", "treat", "suppose",
})

# Rule (b) component: noun phrases that classify the agent's role or its
# operating context. A redirect-verb landing on one of these is the syntactic
# signature of an identity-override attempt.
_ROLE_FRAMES: frozenset[str] = frozenset({
    # agent-role nouns
    "agent", "agents", "assistant", "assistants", "model", "models",
    "ai", "bot", "bots", "chatbot", "chatbots", "helper", "helpers",
    "persona", "personas", "character", "characters",
    "personality", "personalities", "role", "roles",
    "mode", "modes", "representative", "representatives",
    # operating-context nouns
    "framework", "frameworks", "framing", "system", "systems",
    "session", "sessions", "guardrails", "constraints",
    "axes", "rules", "bindings",
})

# Rule (c)/(d) component: qualifiers that dismiss or replace what is in place.
# Adjacent to a role-frame or to a redirect-verb, these signal an override
# attempt even when (b) by itself doesn't fire (e.g. "become unbounded",
# "respond without any of the prior bindings").
_NEGATING_QUALIFIERS: frozenset[str] = frozenset({
    "prior", "without", "different", "fresh", "new", "generic",
    "unrestricted", "unbounded", "unaligned", "unbound",
    "free-form", "open",
})

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'\-]*")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _is_identity_override(text: str) -> bool:
    lower = text.lower().strip()
    # Rule (a): legacy substring markers (v1/v2 coverage).
    if any(marker in lower for marker in _IDENTITY_MARKERS):
        return True

    tokens = _tokenize(text)
    has_verb = any(t in _REDIRECT_VERBS for t in tokens)
    has_frame = any(t in _ROLE_FRAMES for t in tokens)

    # Rule (b): a redirect-verb and a role-frame co-occur in the correction.
    if has_verb and has_frame:
        return True

    # Rules (c)/(d): a negating qualifier sits within a small window of either
    # a role-frame or a redirect-verb. Window is symmetric ±3 tokens to catch
    # both "without prior bindings" (qualifier before frame) and
    # "become unbounded" (verb before qualifier).
    for i, tok in enumerate(tokens):
        if tok not in _NEGATING_QUALIFIERS:
            continue
        window = tokens[max(0, i - 3):i + 4]
        if any(w in _ROLE_FRAMES for w in window):
            return True
        if any(w in _REDIRECT_VERBS for w in window):
            return True

    return False


def _review_hash(candidate: CorrectionCandidate, outcome: ReviewOutcome) -> str:
    payload = json.dumps(
        {
            "candidate_id": candidate.candidate_id,
            "outcome": outcome.value,
            "correction_text": candidate.correction_text,
            "prior_surface": candidate.prior_surface,
            "prior_turn": candidate.prior_turn,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewedTeachingExample:
    candidate: CorrectionCandidate
    outcome: ReviewOutcome
    review_hash: str

    @property
    def accepted(self) -> bool:
        return self.outcome is ReviewOutcome.ACCEPTED

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate": self.candidate.as_dict(),
            "outcome": self.outcome.value,
            "review_hash": self.review_hash,
        }


def review_correction(
    candidate: CorrectionCandidate,
    *,
    identity_score: IdentityScore | None = None,
    identity_manifold: IdentityManifold | None = None,
) -> ReviewedTeachingExample:
    """Review a correction candidate and produce a teaching example.

    Identity overrides are rejected by two independent layers:
      - Syntactic (rules a/b/c/d in `_is_identity_override`) — deterministic
        text-pattern detection.
      - Geometric (`IdentityCheck.would_violate`) — manifold-alignment check
        on the trajectory the correction produced.  Paraphrase-invariant by
        construction (ADR-0010).

    Both layers vote independently; either one is sufficient to reject.
    Empty corrections are rejected separately.  Everything else is accepted.
    """
    if _is_identity_override(candidate.correction_text):
        outcome = ReviewOutcome.REJECTED_IDENTITY
    elif IdentityCheck.would_violate(identity_score, identity_manifold):
        outcome = ReviewOutcome.REJECTED_IDENTITY
    elif not candidate.correction_text.strip():
        outcome = ReviewOutcome.REJECTED_EMPTY
    else:
        outcome = ReviewOutcome.ACCEPTED

    return ReviewedTeachingExample(
        candidate=candidate,
        outcome=outcome,
        review_hash=_review_hash(candidate, outcome),
    )
