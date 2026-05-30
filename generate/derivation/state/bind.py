"""ADR-0184 S1 — conservative referent-binding helpers.

These helpers are behavior-equivalent extractions from
:mod:`generate.derivation.accumulate`.  They are deliberately small: loose
surface subject collection plus a refusal-first same-referent guard.  They do
not resolve ambiguous pronouns, do not gender-match, and do not choose the most
recent actor.  A new named subject is treated as a referent hazard by callers.
"""

from __future__ import annotations

import re
from typing import Final

PRONOUNS: Final[frozenset[str]] = frozenset(
    {
        "he",
        "she",
        "they",
        "it",
        "him",
        "her",
        "them",
        "his",
        "hers",
        "its",
        "their",
        "we",
        "i",
        "you",
    }
)

_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]+")


def leading_subject_token(clause: str) -> str | None:
    """Return the clause's leading word token, or ``None`` if wordless.

    This is a loose signal collector, not a grammar parser.  It mirrors the
    prior accumulation helper so S1 is behavior-equivalent.
    """

    match = _WORD_RE.search(clause)
    return match.group(0) if match is not None else None


def continues_anchor_referent(clause: str, anchor_subject: str | None) -> bool:
    """Whether ``clause`` can safely continue ``anchor_subject``.

    Conservative ADR-0184 rule, extracted from accumulation:

    * no leading token: no new actor signal, so allow;
    * leading pronoun: allow as a continuation candidate;
    * same leading subject as the anchor: allow;
    * any other capitalized leading non-pronoun: new named actor, so disallow;
    * lowercase leading token: no named-actor signal, so allow.

    This does **not** prove pronoun resolution.  Callers still gate the resulting
    candidate through grounding/completeness/pooling.  Multi-actor ambiguity must
    be handled by future semantic-world logic, not by choosing a most-recent actor.
    """

    subject = leading_subject_token(clause)
    if subject is None:
        return True
    if subject.lower() in PRONOUNS:
        return True
    if anchor_subject is not None and subject == anchor_subject:
        return True
    return not subject[:1].isupper()
