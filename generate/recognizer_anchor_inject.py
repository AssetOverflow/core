"""ADR-0163.D.2 — per-category recognizer anchor injection.

When the candidate-graph pipeline's existing parser yields no candidates
for a statement AND the ratified recognizer registry recognizes the
statement, this module is consulted to build typed solver primitives
(``CandidateInitial`` / future ``CandidateOperation`` values) from the
recognizer's ``parsed_anchors``.  The output extends ``per_sentence_choices``
the same way the existing parser's output does, so the downstream
solver runs unchanged.

Doctrine
--------
- Pure, deterministic injectors.  Same ``(match, sentence)`` → same
  ``SentenceChoice`` tuple, byte-equal.
- Refusal-preferring: each injector returns ``()`` when it cannot build
  a primitive that passes the existing ``_initial_admissible``
  structural check (the wrong=0 safety net the candidate-graph already
  enforces).
- No LLM / embeddings / learned classifiers; the injection is rules-only
  same discipline as Phase A/C/D detection.
- Per-category boundary: v1 implements only ``discrete_count_statement``.
  Every other category routes to the empty-tuple fallback (skip-only,
  identical to the round-2 Phase D wiring) and lands in follow-up
  D.2.x PRs after the framework's empirical lift is operator-reviewed.

Five-layer wrong=0 safety net (the Phase D.2 brief's load-bearing
section) is preserved across this module:

  1. Matcher narrowness — ``recognizer_match._try_extract_discrete_count_anchor``
     refuses on any ambiguity.
  2. Extraction correctness — anchor fields ground in the literal
     statement surface.
  3. Injection correctness — the per-category injector returns a
     ``CandidateInitial`` that passes ``_initial_admissible``; failure
     to ground yields ``()``.
  4. Replay gate — propose-time ``run_admissibility_replay_gate``
     auto-rejects any extraction change that lifts the GSM8K wrong
     count.
  5. Multi-branch decision rule — when an injected candidate disagrees
     with another branch's answer, the candidate-graph refuses.
"""

from __future__ import annotations

from typing import Mapping

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_parser import CandidateInitial
from generate.math_problem_graph import InitialPossession, MathGraphError, Quantity
from generate.recognizer_match import RecognizerMatch


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def inject_from_match(
    match: RecognizerMatch,
    sentence: str,
) -> tuple[CandidateInitial, ...]:
    """Dispatch a recognizer match to its per-category injector.

    Returns an empty tuple when the category has no v1 injector or when
    the v1 injector refused.  Skip-only behavior (the round-2 default)
    is the empty-tuple result.
    """
    injector = _INJECTORS.get(match.category)
    if injector is None:
        return ()
    return injector(match, sentence)


# ---------------------------------------------------------------------------
# Per-category injectors
# ---------------------------------------------------------------------------


def inject_discrete_count_statement(
    match: RecognizerMatch,
    sentence: str,
) -> tuple[CandidateInitial, ...]:
    """Build CandidateInitial(s) from ``discrete_count`` parsed anchors.

    v1 narrowness: the matcher emits at most one anchor (further anchors
    refuse extraction).  When the anchor is absent (detection-only
    fallback), the injector returns ``()`` and the candidate-graph
    continues with the round-2 skip-only behavior.
    """
    if not match.parsed_anchors:
        return ()

    out: list[CandidateInitial] = []
    for anchor in match.parsed_anchors:
        cand = _build_initial_from_discrete_count(anchor, sentence)
        if cand is None:
            # Under-admit on any failure to construct.  The other
            # already-built candidates for this sentence remain
            # admissible only if they all pass; partial admission would
            # mean the downstream Cartesian product enumerates a graph
            # missing state — under-admit instead.
            return ()
        out.append(cand)
    return tuple(out)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build_initial_from_discrete_count(
    anchor: Mapping[str, object],
    sentence: str,
) -> CandidateInitial | None:
    """Construct one CandidateInitial from a discrete_count anchor.

    Refuses (returns ``None``) when any field cannot be coerced or when
    the constructed value would violate ``CandidateInitial`` /
    ``InitialPossession`` invariants.  The resulting CandidateInitial is
    structurally verified upstream by ``_initial_admissible``.

    Anchor schema:
        {
          "kind": "discrete_count",
          "subject_role": <str>,
          "count_token": <str>,         # '20' or 'two'
          "count_kind": <"integer"|"word">,
          "counted_noun": <str>,        # 'paperclips' / 'Pokemon cards'
        }
    """
    subject_role = anchor.get("subject_role")
    count_token = anchor.get("count_token")
    count_kind = anchor.get("count_kind")
    counted_noun = anchor.get("counted_noun")

    if (
        not isinstance(subject_role, str) or not subject_role
        or not isinstance(count_token, str) or not count_token
        or not isinstance(count_kind, str)
        or not isinstance(counted_noun, str) or not counted_noun
    ):
        return None

    # Resolve the count token to a numeric value.  v1 supports integer
    # and single-word cardinals; hyphenated compounds defer to a follow-up
    # PR because their resolution requires the language pack's
    # parse_compound_cardinal helper which is not on this hot path.
    value = _resolve_count_value(count_token, count_kind)
    if value is None:
        return None

    # CandidateInitial requires an anchor verb token recognized in its
    # post-init whitelist (has/have/had/owns/owned/holds/held/contains/
    # contained — matched by the recognizer's narrowness rule).  We pick
    # the literal verb token from the sentence so the round-trip ground
    # check inside _initial_admissible succeeds.  Falls back to 'has' when
    # the verb cannot be located in the surface; that fallback only fires
    # when the recognizer's match diverges from the sentence and is the
    # under-admit path.
    verb_in_sentence = _locate_possession_verb(sentence)
    if verb_in_sentence is None:
        return None

    try:
        quantity = Quantity(value=value, unit=counted_noun)
        initial = InitialPossession(entity=subject_role, quantity=quantity)
    except MathGraphError:
        return None

    try:
        return CandidateInitial(
            initial=initial,
            source_span=sentence,
            matched_anchor=verb_in_sentence,
            matched_value_token=count_token,
            matched_unit_token=counted_noun,
            matched_entity_token=subject_role,
        )
    except ValueError:
        return None


def _resolve_count_value(count_token: str, count_kind: str) -> int | None:
    """Map ``count_token`` to a numeric value.

    Integer tokens parse with ``int``.  Word-form tokens look up
    ``WORD_NUMBERS`` from the language pack; unknown words refuse.
    Hyphenated compounds (``twenty-five``) defer to D.2.x — v1 returns
    ``None`` for them.
    """
    if count_kind == "integer":
        try:
            return int(count_token)
        except ValueError:
            return None
    if count_kind == "word":
        # Local import to keep module import-time cheap and to avoid a
        # circular import via the math_candidate_parser surface.
        from generate.math_roundtrip import WORD_NUMBERS

        token_lc = count_token.lower()
        if token_lc in WORD_NUMBERS:
            return int(WORD_NUMBERS[token_lc])
        # Hyphenated compound: defer to D.2.x.
        return None
    return None


def _locate_possession_verb(sentence: str) -> str | None:
    """Return the first possession-anchor verb (lowercased) found in
    ``sentence`` whitespace-tokenized, or ``None`` when absent.

    The verb is the surface token that ``CandidateInitial.__post_init__``
    validates against its registered anchor whitelist.  Returning the
    LITERAL surface keeps the round-trip ground check in
    ``_initial_admissible`` honest.
    """
    possession_verbs = ("has", "have", "had")
    for raw in sentence.split():
        tok = raw.strip(".,;:!?\"'()[]{}").lower()
        if tok in possession_verbs:
            return tok
    return None


# ---------------------------------------------------------------------------
# Dispatch table — keep deterministic and explicit.
# Adding a category here is the SINGLE place a new D.2.x category
# registers its injector.  No global state, no side effects.
# ---------------------------------------------------------------------------

_INJECTORS: Mapping[ShapeCategory, "type"] = {
    ShapeCategory.DISCRETE_COUNT_STATEMENT: inject_discrete_count_statement,  # type: ignore[dict-item]
    # The five other recognizer categories route to the empty-tuple
    # fallback (skip-only) until their D.2.x injector lands:
    #
    # ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY  — by design (no quantity)
    # ShapeCategory.RATE_WITH_CURRENCY             — D.2.2 follow-up
    # ShapeCategory.TEMPORAL_AGGREGATION           — D.2.3 follow-up
    # ShapeCategory.MULTIPLICATIVE_AGGREGATION     — D.2.4 follow-up
    # ShapeCategory.CURRENCY_AMOUNT                — D.2.5 follow-up
}


__all__ = [
    "inject_from_match",
    "inject_discrete_count_statement",
]
