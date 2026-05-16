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

# Contractions relevant to identity-override surface forms.  Expanded before
# marker matching and tokenisation so "you're now a pirate" is treated
# identically to "you are now a pirate".
_CONTRACTIONS: dict[str, str] = {
    "you're": "you are",
    "you've": "you have",
    "you'd": "you would",
    "you'll": "you will",
    "you'r": "you are",          # tolerate the common typo
    "it's": "it is",
    "let's": "let us",
    "i'm": "i am",
    "i've": "i have",
    "i'd": "i would",
    "we're": "we are",
    "we've": "we have",
    "they're": "they are",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "won't": "will not",
    "wouldn't": "would not",
    "shouldn't": "should not",
    "couldn't": "could not",
    "can't": "cannot",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "haven't": "have not",
    "hasn't": "has not",
    "hadn't": "had not",
}

_CONTRACTION_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _CONTRACTIONS) + r")\b"
)


def _normalize(text: str) -> str:
    """Fold contractions and Unicode punctuation to a canonical ASCII form.

    Pre-step for both rule (a) substring matching and rule (b/c/d) tokenisation
    so contractions, curly quotes, and em-dashes do not create override
    bypasses.
    """
    # Curly single / double quotes -> ASCII
    text = (
        text.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
    )
    # Em / en dashes -> space (so dashes do not glue tokens together)
    text = text.replace("—", " ").replace("–", " ")
    lower = text.lower()
    return _CONTRACTION_RE.sub(lambda m: _CONTRACTIONS[m.group(1)], lower)


def _stem_verb(tok: str) -> str:
    """Lightweight deterministic English verb-form folding for redirect-verb
    lookup.  Handles bare form, -s, -es, -ed, -ing with the standard
    consonant-doubling and silent-e patterns.  Returns the bare form if a
    match is found, otherwise the original token.
    """
    if tok in _REDIRECT_VERBS:
        return tok
    for suffix in ("ing", "ed", "es", "s"):
        if not tok.endswith(suffix) or len(tok) <= len(suffix) + 1:
            continue
        candidate = tok[: -len(suffix)]
        if candidate in _REDIRECT_VERBS:
            return candidate
        # Silent-e drop: "becoming" -> "becom" -> "become"
        if (candidate + "e") in _REDIRECT_VERBS:
            return candidate + "e"
        # Doubled consonant: "dropping" -> "dropp" -> "drop"
        if (
            len(candidate) >= 2
            and candidate[-1] == candidate[-2]
            and candidate[:-1] in _REDIRECT_VERBS
        ):
            return candidate[:-1]
    return tok


def _is_identity_override(text: str) -> bool:
    normalized = _normalize(text).strip()
    # Rule (a): legacy substring markers (v1/v2 coverage), now contraction-aware.
    if any(marker in normalized for marker in _IDENTITY_MARKERS):
        return True

    tokens = _TOKEN_RE.findall(normalized)
    stems = [_stem_verb(t) for t in tokens]
    has_verb = any(s in _REDIRECT_VERBS for s in stems)
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
        start = max(0, i - 3)
        end = i + 4
        window_tokens = tokens[start:end]
        window_stems = stems[start:end]
        if any(w in _ROLE_FRAMES for w in window_tokens):
            return True
        if any(w in _REDIRECT_VERBS for w in window_stems):
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
