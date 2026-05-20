"""ADR-0075 (C1) — realizer slot-type guard.

Pure verifier that runs on every candidate surface produced by the
truth path, before the surface is assigned to ``ChatResponse.surface``.
Rejects illegal articulations; the runtime routes a rejected
candidate to a deterministic bounded disclosure string.

Doctrine
--------

This module is **admission control with a deterministic fallback**,
not normalization.  The guard never edits a surface; it only emits
a verdict (``status`` + ``rule_id`` + ``detail``).  That keeps it
firmly outside CLAUDE.md's forbidden normalization sites — it does
not repair a candidate, it refuses it.

Rules
-----

C1 active rules (see ADR-0075):

* **R2_aux_neg_requires_verb** — after a do-support negation
  (``do not`` / ``does not`` / ``did not``), the immediately
  following non-adverb content token must have POS ``VERB``.
* **R3_be_neg_requires_predicate** — after a be-negation
  (``is not`` / ``are not`` / ``was not`` / ``were not``), the
  immediately following non-adverb content token must have POS in
  ``{NOUN, ADJ, DET, ADV, PRON}``.

R1 (``no_finite_verb``) was scoped into C1 originally but **deferred**
during ratification: the active language-pack POS coverage does not
list every English finite verb used by the teaching-chain realizer
(notably ``requires`` / ``makes``), so R1 would falsely reject
currently-passing cognition cases — a regression the ADR's
byte-identity canary explicitly forbids.  R1's intent is preserved
for a follow-up phase that either broadens pack POS coverage or
adds a closed English-vocabulary POS table to the guard.

Empty surfaces are exempt — those route through a separate
disclosure path.

Determinism
-----------

The guard is a pure function of ``(surface, pos_lookup)``.  No I/O,
no mutation, no globals beyond the closed sets defined in this
module.  Pack lexicons that back the ``pos_lookup`` callable are
themselves deterministic from manifest checksums, so guard verdicts
are replay-equivalent across runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Literal


DISCLOSURE_SURFACE = "I do not have a reviewed articulation for that yet."
"""Bounded fallback surface used when the guard rejects a candidate.

Module-level constant — never composed from user input.  The runtime
substitutes this string for any rejected candidate before assigning
to ``ChatResponse.surface``.
"""


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'_-]*")


_FINITE_VERB_AUX: frozenset[str] = frozenset({
    "be", "am", "is", "are", "was", "were", "been", "being",
    "do", "does", "did", "doing", "done",
    "have", "has", "had", "having",
    "will", "would", "shall", "should",
    "can", "could", "may", "might", "must",
})
"""Finite verb forms recognized without pack POS lookup."""


_PREDICATE_FUNCTION_WORDS: frozenset[str] = frozenset({
    "a", "an", "the",
    "i", "you", "he", "she", "it",
    "we", "they", "me", "him", "her", "us", "them",
    "this", "that", "these", "those",
    "my", "your", "his", "its", "our", "their",
})
"""Predicate-eligible function words (allowed after be-negation)."""


_ADVERB_FUNCTION_WORDS: frozenset[str] = frozenset({
    "always", "never", "ever", "even", "only", "just",
    "really", "actually", "still", "yet", "also",
    "often", "sometimes", "usually", "rarely",
})
"""Adverbs skipped when looking past a negation to its target slot."""


_DO_AUX: frozenset[str] = frozenset({"do", "does", "did"})
_BE_AUX: frozenset[str] = frozenset({"is", "are", "was", "were"})


@dataclass(frozen=True)
class RealizerGuardVerdict:
    """Outcome of a single guard check.

    ``status``  : ``"ok"`` when all rules pass; ``"rejected"`` when
                  at least one rule fires.
    ``rule_id`` : closed-set identifier of the failing rule
                  (``""`` when status is ``"ok"``).
    ``detail``  : short surface fragment showing the violation
                  (``""`` when status is ``"ok"``).
    """

    status: Literal["ok", "rejected"]
    rule_id: str
    detail: str


_OK_VERDICT = RealizerGuardVerdict(status="ok", rule_id="", detail="")


def _tokens(surface: str) -> list[tuple[int, str]]:
    """Return ordered ``(start_index, token)`` pairs.

    Punctuation, digits, and bracket/quote characters are skipped.
    The regex selects ``A-Za-z`` runs with internal apostrophes,
    underscores, or hyphens.
    """
    return [(m.start(), m.group(0)) for m in _TOKEN_RE.finditer(surface)]


def _skip_adverbs(tokens: list[tuple[int, str]], start_idx: int) -> int:
    """Return the index of the first non-adverb-function-word at or
    after ``start_idx``.  Returns ``len(tokens)`` when the rest is
    exhausted entirely by adverbs.
    """
    j = start_idx
    while j < len(tokens) and tokens[j][1].casefold() in _ADVERB_FUNCTION_WORDS:
        j += 1
    return j


def _explicit_non_verb(
    token: str,
    pos_lookup: Callable[[str], str | None],
) -> bool:
    """True iff the token has an EXPLICIT non-VERB POS tag.

    Unknown tokens (pack returns ``None``) fail open — the rule does
    not fire on them.  This is the principled trigger for R2: only
    reject when the pack has explicitly classified the next-token as
    the wrong POS for a do-support negation slot.
    """
    fold = token.casefold()
    if fold in _FINITE_VERB_AUX:
        return False
    pos = pos_lookup(token)
    if pos is None or pos == "VERB":
        return False
    return True


def _explicit_non_predicate(
    token: str,
    pos_lookup: Callable[[str], str | None],
) -> bool:
    """True iff the token has an EXPLICIT non-predicate POS tag
    (typically ``VERB``).  Unknown tokens fail open.
    """
    fold = token.casefold()
    if fold in _PREDICATE_FUNCTION_WORDS or fold in _ADVERB_FUNCTION_WORDS:
        return False
    pos = pos_lookup(token)
    if pos is None:
        return False
    return pos not in {"NOUN", "ADJ", "DET", "ADV", "PRON"}


def check_surface(
    surface: str,
    *,
    pos_lookup: Callable[[str], str | None],
) -> RealizerGuardVerdict:
    """Apply C1's active rules (R2, R3) to ``surface``.

    ``pos_lookup`` should return one of the pack POS tags
    (``"NOUN"``, ``"VERB"``, ``"ADJ"``, ``"DET"``, ``"ADV"``,
    ``"PRON"``, …) or ``None`` if the token is unknown.

    **Fail-open on unknown POS, fail-closed on explicit wrong POS.**
    R2 fires only when the next-token has an explicit non-VERB POS;
    R3 fires only when the next-token has an explicit non-predicate
    POS (typically ``VERB``).  Unknown tokens — words the pack
    doesn't list — pass through both rules unscathed, because the
    guard cannot prove they violate the slot type.  This honors the
    byte-identity invariant on currently-passing cases where the
    realizer emits valid English that the cognition pack happens
    not to enumerate (e.g., ``ratified`` in PROCEDURE templates).

    Rules are position-anchored: the scan walks the token stream
    once and emits the first violation it finds.
    """
    if not surface.strip():
        return _OK_VERDICT
    tokens = _tokens(surface)
    if not tokens:
        return _OK_VERDICT

    for i in range(len(tokens) - 1):
        cur = tokens[i][1].casefold()
        nxt = tokens[i + 1][1].casefold()
        if cur in _DO_AUX and nxt == "not":
            j = _skip_adverbs(tokens, i + 2)
            if j >= len(tokens):
                return RealizerGuardVerdict(
                    status="rejected",
                    rule_id="R2_aux_neg_requires_verb",
                    detail=f"{tokens[i][1]} not <missing>",
                )
            tok = tokens[j][1]
            if _explicit_non_verb(tok, pos_lookup):
                return RealizerGuardVerdict(
                    status="rejected",
                    rule_id="R2_aux_neg_requires_verb",
                    detail=f"{tokens[i][1]} not {tok}",
                )
        if cur in _BE_AUX and nxt == "not":
            j = _skip_adverbs(tokens, i + 2)
            if j >= len(tokens):
                return RealizerGuardVerdict(
                    status="rejected",
                    rule_id="R3_be_neg_requires_predicate",
                    detail=f"{tokens[i][1]} not <missing>",
                )
            tok = tokens[j][1]
            if _explicit_non_predicate(tok, pos_lookup):
                return RealizerGuardVerdict(
                    status="rejected",
                    rule_id="R3_be_neg_requires_predicate",
                    detail=f"{tokens[i][1]} not {tok}",
                )

    return _OK_VERDICT
